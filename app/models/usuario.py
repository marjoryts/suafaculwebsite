import sys, os, re, secrets
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.database import get_connection
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario:
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
            c.execute("SELECT id, nome_usuario, email, senha, tipo, foto_url FROM usuarios WHERE nome_usuario=? OR email=?", (username, username))
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
            c.execute("SELECT id, nome_usuario, email, tipo, foto_url FROM usuarios WHERE id=?", (id,))
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

    def buscar_por_google_id(self, google_id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id, nome_usuario, email, tipo, foto_url FROM usuarios WHERE google_id=?", (google_id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def buscar_por_email(self, email):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id, nome_usuario, email, tipo, foto_url FROM usuarios WHERE email=?", (email,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def vincular_google(self, id, google_id, foto_url):
        """Vincula uma conta google_id a um usuário já existente (encontrado
        por e-mail verificado). Não sobrescreve a foto atual se o Google não
        mandar uma (foto_url=None)."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE usuarios SET google_id=?, foto_url=COALESCE(?, foto_url) WHERE id=?", (google_id, foto_url, id))
            conn.commit()
            c.execute("SELECT id, nome_usuario, email, tipo, foto_url FROM usuarios WHERE id=?", (id,))
            row = c.fetchone()
            conn.close()
            if not row:
                return {'success': False, 'message': 'Usuário não encontrado.'}
            return {'success': True, 'user': dict(row)}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def criar_via_google(self, google_id, email, nome, foto_url):
        """Cria uma conta nova (tipo 'aluno') a partir de um login Google
        sem conta local prévia. A senha é um hash aleatório e inutilizável —
        essa conta só pode entrar via Google."""
        try:
            conn = get_connection()
            c = conn.cursor()
            username = self._gerar_username_unico(c, nome or email.split('@')[0])
            senha_hash = generate_password_hash(secrets.token_hex(32))
            c.execute(
                "INSERT INTO usuarios (nome_usuario, email, senha, tipo, google_id, foto_url) VALUES (?,?,?,?,?,?)",
                (username, email, senha_hash, 'aluno', google_id, foto_url)
            )
            conn.commit()
            novo_id = c.lastrowid
            conn.close()
            return {'success': True, 'user': {'id': novo_id, 'nome_usuario': username, 'email': email, 'tipo': 'aluno', 'foto_url': foto_url}}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def _gerar_username_unico(self, cursor, base):
        base = re.sub(r'[^a-zA-Z0-9_.]', '', base.strip().replace(' ', '_')) or 'usuario'
        base = base[:40] or 'usuario'
        candidato = base
        sufixo = 1
        while True:
            cursor.execute("SELECT id FROM usuarios WHERE nome_usuario=?", (candidato,))
            if not cursor.fetchone():
                return candidato
            sufixo += 1
            candidato = f"{base}{sufixo}"
