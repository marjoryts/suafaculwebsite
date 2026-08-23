import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection

class Favorito:
    def adicionar(self, usuario_id, tipo, item_id, nome_item):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM favoritos WHERE usuario_id=? AND tipo=? AND item_id=?", (usuario_id, tipo, item_id))
            if c.fetchone():
                conn.close()
                return {'success': False, 'message': 'Item já está nos favoritos.'}
            c.execute("INSERT INTO favoritos (usuario_id, tipo, item_id, nome_item) VALUES (?,?,?,?)", (usuario_id, tipo, item_id, nome_item))
            id = c.lastrowid
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Favorito adicionado com sucesso!', 'id': id}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def remover(self, usuario_id, tipo, item_id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM favoritos WHERE usuario_id=? AND tipo=? AND item_id=?", (usuario_id, tipo, item_id))
            affected = c.rowcount
            conn.commit()
            conn.close()
            if affected > 0:
                return {'success': True, 'message': 'Favorito removido com sucesso!'}
            return {'success': False, 'message': 'Favorito não encontrado.'}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def listar_por_usuario(self, usuario_id, tipo=None):
        try:
            conn = get_connection()
            c = conn.cursor()
            if tipo:
                c.execute("SELECT * FROM favoritos WHERE usuario_id=? AND tipo=? ORDER BY created_at DESC", (usuario_id, tipo))
            else:
                c.execute("SELECT * FROM favoritos WHERE usuario_id=? ORDER BY created_at DESC", (usuario_id,))
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def verificar_favorito(self, usuario_id, tipo, item_id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM favoritos WHERE usuario_id=? AND tipo=? AND item_id=?", (usuario_id, tipo, item_id))
            exists = c.fetchone() is not None
            conn.close()
            return exists
        except Exception:
            return False

    def listar_ids_favoritos(self, usuario_id, tipo):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT item_id FROM favoritos WHERE usuario_id=? AND tipo=?", (usuario_id, tipo))
            ids = [r['item_id'] for r in c.fetchall()]
            conn.close()
            return ids
        except Exception:
            return []
