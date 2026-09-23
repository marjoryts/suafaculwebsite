import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario:
    # ── Suporte a login com Google (OIDC) ──────────────────────────────
    def buscar_por_email(self, email):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "SELECT id, nome_usuario, email, tipo, google_id, auth_provider, avatar_url "
                "FROM usuarios WHERE email=?", (email,)
            )
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def buscar_por_google_id(self, google_id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "SELECT id, nome_usuario, email, tipo, google_id, auth_provider, avatar_url "
                "FROM usuarios WHERE google_id=?", (google_id,)
            )
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
            c.execute(
                "INSERT INTO usuarios (nome_usuario, email, senha, tipo, google_id, auth_provider, avatar_url) "
                "VALUES (?,?,?,?,?,?,?)",
                (username, email, senha_inutilizavel, 'aluno', google_id, 'google', avatar_url)
            )
            conn.commit()
            novo_id = c.lastrowid
            conn.close()
            return {'success': True, 'user': {'id': novo_id, 'nome_usuario': username, 'email': email, 'tipo': 'aluno', 'avatar_url': avatar_url}}
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
            c.execute("SELECT id, nome_usuario, email, tipo, avatar_url FROM usuarios WHERE id=?", (user_id,))
            row = c.fetchone()
            conn.close()
            return {'success': True, 'user': dict(row) if row else None}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def criar(self, username, email, password, tipo='aluno'):
        try:
            if tipo not in ('aluno', 'admin'):
                tipo = 'aluno'
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM usuarios WHERE nome_usuario=? OR email=?", (username, email))
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
            c.execute("SELECT id, nome_usuario, email, senha, tipo, avatar_url FROM usuarios WHERE nome_usuario=? OR email=?", (username, username))
            row = c.fetchone()
            conn.close()
            if row:
                if check_password_hash(row['senha'], password):
                    user = dict(row)
                    user.pop('senha', None)
                    return {'success': True, 'user': user}
                else:
                    return {'success': False, 'message': 'Senha incorreta.'}
            else:
                return {'success': False, 'message': 'Usuário não encontrado.'}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

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
            c.execute("SELECT id, nome_usuario, email, tipo, avatar_url, auth_provider, created_at "
                      "FROM usuarios WHERE id=?", (id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def is_admin(self, id):
        u = self.buscar_por_id(id)
        return bool(u) and u.get('tipo') == 'admin'

    def atualizar(self, id, username, email, password=None):
        try:
            conn = get_connection()
            c = conn.cursor()
            if password:
                hashed = generate_password_hash(password)
                c.execute("UPDATE usuarios SET nome_usuario=?, email=?, senha=? WHERE id=?", (username, email, hashed, id))
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
