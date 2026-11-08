import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection, inserir
from werkzeug.security import generate_password_hash, check_password_hash

_HASH_FALSO = None


def _hash_falso():
    global _HASH_FALSO
    if _HASH_FALSO is None:
        _HASH_FALSO = generate_password_hash('senha-inexistente-para-equalizar-o-tempo')
    return _HASH_FALSO


# Colunas devolvidas pelas buscas (nunca a senha).
_CAMPOS = ("id, nome_usuario, email, tipo, google_id, auth_provider, avatar_url, created_at, "
           "email_verificado, credencial_versao, senha_definida")


def normalizar_email(email):
    """E-mails são únicos sem diferenciar maiúsculas: guardamos e comparamos em minúsculas."""
    return (email or '').strip().lower()


class Usuario:
    # ── Suporte a login com Google (OIDC) ──────────────────────────────
    def buscar_por_email(self, email):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(f"SELECT {_CAMPOS} FROM usuarios WHERE LOWER(email)=? ORDER BY id LIMIT 1",
                      (normalizar_email(email),))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def buscar_por_google_id(self, google_id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(f"SELECT {_CAMPOS} FROM usuarios WHERE google_id=?", (google_id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def _gerar_username_disponivel(self, base):
        base = (base or 'usuario').strip().lower().replace(' ', '.') or 'usuario'
        conn = get_connection()
        c = conn.cursor()
        candidato = base
        sufixo = 0
        while True:
            c.execute("SELECT 1 FROM usuarios WHERE nome_usuario=?", (candidato,))
            if not c.fetchone():
                conn.close()
                return candidato
            sufixo += 1
            candidato = f"{base}{sufixo}"

    def criar_via_google(self, google_id, email, nome, avatar_url=None):
        """Cria uma conta nova associada a um login do Google.
        A senha é preenchida com um hash aleatório inutilizável, já que o
        login desse usuário sempre passará pelo Google."""
        try:
            username = self._gerar_username_disponivel(nome or email.split('@')[0])
            senha_inutilizavel = generate_password_hash(os.urandom(32).hex())
            conn = get_connection()
            c = conn.cursor()
            novo_id = inserir(
                c,
                "INSERT INTO usuarios (nome_usuario, email, senha, tipo, google_id, auth_provider, avatar_url, "
                "email_verificado, email_verificado_em, senha_definida) VALUES (?,?,?,?,?,?,?,1,CURRENT_TIMESTAMP,0)",
                (username, normalizar_email(email), senha_inutilizavel, 'aluno', google_id, 'google', avatar_url)
            )
            conn.commit()
            conn.close()
            return {'success': True, 'user': self.buscar_por_id(novo_id)}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def vincular_google(self, user_id, google_id, avatar_url=None):
        """Associa um google_id a uma conta local já existente (mesmo e-mail
        verificado pelo Google) e retorna o usuário atualizado."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "UPDATE usuarios SET google_id=?, avatar_url=COALESCE(?, avatar_url) WHERE id=?",
                (google_id, avatar_url, user_id)
            )
            conn.commit()
            conn.close()
            return {'success': True, 'user': self.buscar_por_id(user_id)}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def criar(self, username, email, password, tipo='aluno'):
        try:
            if tipo not in ('aluno', 'admin'):
                tipo = 'aluno'
            conn = get_connection()
            c = conn.cursor()
            email = normalizar_email(email)
            c.execute("SELECT id FROM usuarios WHERE nome_usuario=? OR LOWER(email)=?", (username, email))
            if c.fetchone():
                conn.close()
                return {'success': False, 'message': 'Nome de usuário ou e-mail já cadastrado.'}
            hashed = generate_password_hash(password)
            c.execute("INSERT INTO usuarios (nome_usuario, email, senha, tipo) VALUES (?,?,?,?)", (username, email, hashed, tipo))
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Usuário registrado com sucesso!'}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def autenticar(self, username, password):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(f"SELECT {_CAMPOS}, senha FROM usuarios WHERE nome_usuario=? OR LOWER(email)=? ORDER BY id LIMIT 1",
                      (username, normalizar_email(username)))
            row = c.fetchone()
            conn.close()
            if row is None:
                check_password_hash(_hash_falso(), password)  # mesmo tempo de resposta
            elif check_password_hash(row['senha'], password):
                user = dict(row)
                user.pop('senha', None)
                return {'success': True, 'user': user}
                # Mesma mensagem para "usuário inexistente" e "senha errada":
                # evita que o login sirva para descobrir quais contas existem.
            return {'success': False, 'message': 'Usuário ou senha inválidos.'}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def autenticar_por_email(self, email, senha):
        """Valida e-mail + senha. Devolve o usuário (sem a senha) ou None.

        Quando o e-mail não existe, ainda assim verifica uma senha "falsa": o
        tempo de resposta não revela se a conta existe.
        """
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(f"SELECT {_CAMPOS}, senha FROM usuarios WHERE LOWER(email)=? ORDER BY id LIMIT 1",
                      (normalizar_email(email),))
            row = c.fetchone()
            conn.close()
        except Exception:
            return None
        if row is None:
            check_password_hash(_hash_falso(), senha)
            return None
        if not check_password_hash(row['senha'], senha):
            return None
        usuario = dict(row)
        usuario.pop('senha', None)
        return usuario

    def listar(self):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id, nome_usuario, email, tipo FROM usuarios ORDER BY id")
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def buscar_por_id(self, id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(f"SELECT {_CAMPOS} FROM usuarios WHERE id=?", (id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def existe_conflito(self, username, email, ignorar_id=None):
        """Já existe OUTRO usuário com esse nome de usuário ou e-mail?"""
        try:
            conn = get_connection()
            c = conn.cursor()
            sql = "SELECT 1 FROM usuarios WHERE (nome_usuario=? OR LOWER(email)=?)"
            params = [username, normalizar_email(email)]
            if ignorar_id is not None:
                sql += " AND id<>?"
                params.append(ignorar_id)
            c.execute(sql, params)
            existe = c.fetchone() is not None
            conn.close()
            return existe
        except Exception:
            return False

    def is_admin(self, id):
        u = self.buscar_por_id(id)
        return bool(u) and u.get('tipo') == 'admin'

    def atualizar(self, id, username, email, password=None):
        try:
            conn = get_connection()
            c = conn.cursor()
            if password:
                hashed = generate_password_hash(password)
                c.execute("UPDATE usuarios SET nome_usuario=?, email=?, senha=?, senha_definida=1, "
                          "credencial_versao=credencial_versao+1 WHERE id=?", (username, email, hashed, id))
            else:
                c.execute("UPDATE usuarios SET nome_usuario=?, email=? WHERE id=?", (username, email, id))
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Usuário atualizado com sucesso!'}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def definir_tipo(self, id, tipo):
        if tipo not in ('aluno', 'admin'):
            return {'success': False, 'message': "Tipo inválido. Use 'aluno' ou 'admin'."}
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE usuarios SET tipo=? WHERE id=?", (tipo, id))
            conn.commit()
            conn.close()
            return {'success': True, 'message': f'Usuário agora é {tipo}.'}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def deletar(self, id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM usuarios WHERE id=?", (id,))
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Usuário deletado com sucesso!'}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    # ── Verificação de e-mail, senha e sessões ────────────────────────
    def _executar(self, sql, params):
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute(sql, params)
            conn.commit()
            return c.rowcount
        finally:
            conn.close()

    def senha_confere(self, id, senha):
        """A senha informada é a atual da conta? (tempo constante por conta do hash)."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT senha FROM usuarios WHERE id=?", (id,)).fetchone()
        finally:
            conn.close()
        return bool(row) and check_password_hash(row['senha'], senha or '')

    def marcar_email_verificado(self, id):
        self._executar("UPDATE usuarios SET email_verificado=1, email_verificado_em=CURRENT_TIMESTAMP WHERE id=?", (id,))

    def marcar_email_nao_verificado(self, id):
        self._executar("UPDATE usuarios SET email_verificado=0, email_verificado_em=NULL WHERE id=?", (id,))

    def trocar_email(self, id, novo_email):
        """Troca já confirmada (o código foi enviado ao novo endereço): fica verificado."""
        self._executar("UPDATE usuarios SET email=?, email_verificado=1, email_verificado_em=CURRENT_TIMESTAMP, "
                       "updated_at=CURRENT_TIMESTAMP WHERE id=?", (normalizar_email(novo_email), id))

    def definir_senha(self, id, senha):
        """Nova senha + nova versão da credencial (as sessões antigas do site caem)."""
        self._executar("UPDATE usuarios SET senha=?, senha_definida=1, credencial_versao=credencial_versao+1, "
                       "updated_at=CURRENT_TIMESTAMP WHERE id=?", (generate_password_hash(senha), id))

    def invalidar_senha(self, id):
        """Troca a senha por um hash aleatório (ninguém a conhece) e derruba as sessões do site.
        Usado quando o dono do e-mail assume, pelo Google, uma conta que não tinha o e-mail verificado."""
        self._executar("UPDATE usuarios SET senha=?, senha_definida=0, credencial_versao=credencial_versao+1, "
                       "updated_at=CURRENT_TIMESTAMP WHERE id=?", (generate_password_hash(os.urandom(32).hex()), id))

