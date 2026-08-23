import sys, os
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
            c.execute("SELECT id, nome_usuario, email, senha, tipo FROM usuarios WHERE nome_usuario=? OR email=?", (username, username))
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
            c.execute("SELECT id, nome_usuario, email, tipo FROM usuarios WHERE id=?", (id,))
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
