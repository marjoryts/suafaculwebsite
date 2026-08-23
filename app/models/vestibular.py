import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection

class Vestibular:
    def _build_where(self, filtros):
        sql = " WHERE 1=1"
        params = []
        if filtros.get('tipo_instituicao'):
            sql += " AND tipo_instituicao=?"
            params.append(filtros['tipo_instituicao'])
        if filtros.get('regiao'):
            sql += " AND regiao=?"
            params.append(filtros['regiao'])
        if filtros.get('busca'):
            like = f"%{filtros['busca']}%"
            sql += " AND (nome LIKE ? OR instituicao LIKE ? OR cidade LIKE ?)"
            params.extend([like, like, like])
        if filtros.get('meses'):
            meses = filtros['meses']
            clauses = []
            for m in meses:
                # SQLite: strftime('%m', data_prova)
                clauses.append("CAST(strftime('%m', data_prova) AS INTEGER)=?")
                params.append(int(m))
            if clauses:
                sql += f" AND ({' OR '.join(clauses)})"
        if filtros.get('apenas_publicos'):
            sql += " AND tipo_instituicao='Pública'"
        if filtros.get('curso'):
            sql += " AND faculdade_id IN (SELECT faculdade_id FROM cursos WHERE faculdade_id IS NOT NULL AND nome=?)"
            params.append(filtros['curso'])
        return sql, params

    def listar(self, filtros={}):
        try:
            conn = get_connection()
            c = conn.cursor()
            where, params = self._build_where(filtros)
            sql = "SELECT * FROM vestibulares" + where + " ORDER BY data_prova ASC"
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
            sql = "SELECT COUNT(*) as total FROM vestibulares" + where
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
            c.execute("SELECT * FROM vestibulares WHERE id=?", (id,))
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
                "INSERT INTO vestibulares (nome, instituicao, tipo_instituicao, cidade, regiao, periodo_inscricao, data_prova, descricao, link_edital) VALUES (?,?,?,?,?,?,?,?,?)",
                (dados['nome'], dados.get('instituicao',''), dados['tipo_instituicao'], dados['cidade'],
                 dados['regiao'], dados['periodo_inscricao'], dados['data_prova'], dados['descricao'], dados['link_edital'])
            )
            id = c.lastrowid
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Vestibular criado com sucesso!', 'id': id}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}
