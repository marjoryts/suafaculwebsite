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
            # Aceita uma região (str) ou várias (lista) — o painel de filtros
            # permite marcar mais de uma.
            regioes = filtros['regiao']
            if isinstance(regioes, str):
                regioes = [regioes]
            regioes = [r for r in regioes if r]
            if regioes:
                sql += f" AND regiao IN ({','.join('?' * len(regioes))})"
                params.extend(regioes)
        if filtros.get('busca'):
            like = f"%{filtros['busca']}%"
            sql += (" AND (nome LIKE ? OR instituicao LIKE ? OR cidade LIKE ?"
                    " OR descricao LIKE ? OR cursos_oferecidos LIKE ?)")
            params.extend([like] * 5)
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
            # Vestibulares da faculdade que oferece o curso OU que citam o
            # curso na lista de cursos oferecidos do processo seletivo.
            sql += (" AND (faculdade_id IN (SELECT faculdade_id FROM cursos WHERE faculdade_id IS NOT NULL AND nome=?)"
                    " OR cursos_oferecidos LIKE ?)")
            params.extend([filtros['curso'], f"%{filtros['curso']}%"])
        return sql, params

    def listar(self, filtros={}):
        try:
            conn = get_connection()
            c = conn.cursor()
            where, params = self._build_where(filtros)
            # Próximas provas primeiro (da mais próxima para a mais distante),
            # depois as que já passaram e, por último, as sem data definida.
            sql = ("SELECT * FROM vestibulares" + where +
                   " ORDER BY (data_prova IS NULL OR date(data_prova) IS NULL),"
                   " (date(data_prova) < date('now')), data_prova ASC, nome ASC")
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
            c.execute("SELECT id FROM vestibulares WHERE lower(nome)=lower(?)", (dados['nome'].strip(),))
            if c.fetchone():
                conn.close()
                return {'success': False, 'message': 'Já existe um vestibular cadastrado com esse nome.'}
            c.execute(
                "INSERT INTO vestibulares (nome, instituicao, tipo_instituicao, cidade, regiao, periodo_inscricao, data_prova, descricao, link_edital, taxa_inscricao, cursos_oferecidos, requisitos) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (dados['nome'].strip(), dados.get('instituicao',''), dados['tipo_instituicao'], dados['cidade'],
                 dados['regiao'], dados['periodo_inscricao'], dados['data_prova'] or None, dados['descricao'], dados['link_edital'],
                 dados.get('taxa_inscricao') or None, dados.get('cursos_oferecidos') or None, dados.get('requisitos') or None)
            )
            id = c.lastrowid
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Vestibular criado com sucesso!', 'id': id}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}
