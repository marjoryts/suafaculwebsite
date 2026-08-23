import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection

class Curso:
    def _build_where(self, filtros):
        sql = " WHERE 1=1"
        params = []
        if filtros.get('area'):
            sql += " AND area=?"
            params.append(filtros['area'])
        if filtros.get('modalidade'):
            mods = filtros['modalidade'] if isinstance(filtros['modalidade'], list) else [filtros['modalidade']]
            if mods:
                sql += f" AND modalidade IN ({','.join('?'*len(mods))})"
                params.extend(mods)
        if filtros.get('tipo_instituicao'):
            tipos = filtros['tipo_instituicao'] if isinstance(filtros['tipo_instituicao'], list) else [filtros['tipo_instituicao']]
            if tipos:
                sql += f" AND tipo_instituicao IN ({','.join('?'*len(tipos))})"
                params.extend(tipos)
        if filtros.get('busca'):
            like = f"%{filtros['busca']}%"
            sql += " AND (nome LIKE ? OR instituicao LIKE ? OR descricao LIKE ? OR area LIKE ?)"
            params.extend([like, like, like, like])
        return sql, params

    def listar(self, filtros={}):
        try:
            conn = get_connection()
            c = conn.cursor()
            where, params = self._build_where(filtros)
            sql = "SELECT * FROM cursos" + where + " ORDER BY nome ASC"
            if 'limit' in filtros and 'offset' in filtros:
                sql += " LIMIT ? OFFSET ?"
                params.extend([filtros['limit'], filtros['offset']])
            c.execute(sql, params)
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def contar(self, filtros={}):
        try:
            conn = get_connection()
            c = conn.cursor()
            where, params = self._build_where(filtros)
            sql = "SELECT COUNT(*) as total FROM cursos" + where
            c.execute(sql, params)
            total = c.fetchone()['total']
            conn.close()
            return total
        except Exception:
            return 0

    def buscar_por_id(self, id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM cursos WHERE id=?", (id,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def criar(self, dados):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "INSERT INTO cursos (nome, instituicao, faculdade_id, modalidade, descricao, duracao, grau, area, tipo_instituicao) VALUES (?,?,?,?,?,?,?,?,?)",
                (dados['nome'], dados['instituicao'], dados.get('faculdade_id'), dados['modalidade'], dados['descricao'],
                 dados['duracao'], dados['grau'], dados['area'], dados['tipo_instituicao'])
            )
            id = c.lastrowid
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Curso criado com sucesso!', 'id': id}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}
