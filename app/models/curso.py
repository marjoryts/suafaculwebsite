import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection, inserir, like_ci

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
            sql += (f" AND ({like_ci('nome')} OR {like_ci('instituicao')}"
                    f" OR {like_ci('descricao')} OR {like_ci('area')})")
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
            id = inserir(
                c,
                "INSERT INTO cursos (nome, instituicao, faculdade_id, modalidade, descricao, duracao, grau, area, tipo_instituicao) VALUES (?,?,?,?,?,?,?,?,?)",
                (dados['nome'], dados['instituicao'], dados.get('faculdade_id'), dados['modalidade'], dados['descricao'],
                 dados['duracao'], dados['grau'], dados['area'], dados['tipo_instituicao'])
            )
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Curso criado com sucesso!', 'id': id}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def upsert_por_codigo_inep_lote(self, lista_dados):
        """Insere/atualiza em massa uma lista de cursos vindos do Censo
        INEP, identificados por `codigo_inep_curso` (evita duplicar em
        reimportações do mesmo dataset ou de anos diferentes). Tudo numa
        única transação — ou importa tudo, ou nada (evita ficar com o
        banco pela metade se algo falhar no meio de 40 mil linhas)."""
        conn = get_connection()
        c = conn.cursor()
        criados, atualizados = 0, 0
        try:
            for dados in lista_dados:
                c.execute("SELECT id FROM cursos WHERE codigo_inep_curso=?", (dados['codigo_inep_curso'],))
                existente = c.fetchone()
                if existente:
                    c.execute(
                        """UPDATE cursos SET nome=?, instituicao=?, faculdade_id=?, modalidade=?,
                           grau=?, area=?, tipo_instituicao=?, updated_at=CURRENT_TIMESTAMP
                           WHERE codigo_inep_curso=?""",
                        (dados['nome'], dados['instituicao'], dados['faculdade_id'], dados['modalidade'],
                         dados['grau'], dados['area'], dados['tipo_instituicao'], dados['codigo_inep_curso'])
                    )
                    atualizados += 1
                else:
                    c.execute(
                        """INSERT INTO cursos (nome, instituicao, faculdade_id, modalidade, descricao,
                           duracao, grau, area, tipo_instituicao, codigo_inep_curso)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (dados['nome'], dados['instituicao'], dados['faculdade_id'], dados['modalidade'],
                         dados.get('descricao'), dados.get('duracao'), dados['grau'], dados['area'],
                         dados['tipo_instituicao'], dados['codigo_inep_curso'])
                    )
                    criados += 1
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return {'criados': criados, 'atualizados': atualizados}

    def sugestoes_por_nome(self, termo, limite=8):
        """Nomes de curso distintos que começam com `termo` (case-insensitive)
        — usado pelo autocomplete do campo de busca de curso. Prefixo (não
        'contém') para casar com o padrão de UX pedido: digitar 'Engenharia'
        sugere 'Engenharia de Software', 'Engenharia Civil' etc., não
        qualquer curso que tenha 'engenharia' em outra parte do nome."""
        termo = (termo or '').strip()
        if not termo:
            return []
        try:
            conn = get_connection()
            c = conn.cursor()
            termo_escapado = termo.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            c.execute(
                "SELECT DISTINCT nome FROM cursos WHERE LOWER(nome) LIKE ? ESCAPE '\\' "
                "ORDER BY nome ASC LIMIT ?",
                (termo_escapado.lower() + '%', limite)
            )
            nomes = [r['nome'] for r in c.fetchall()]
            conn.close()
            return nomes
        except Exception:
            return []

    def listar_por_faculdade(self, faculdade_id):
        """Cursos de uma instituição (campos públicos), em ordem alfabética."""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT nome, modalidade, grau, area FROM cursos WHERE faculdade_id=? ORDER BY nome ASC",
                      (faculdade_id,))
            return [dict(r) for r in c.fetchall()]
        finally:
            conn.close()

    def contar_importados_inep(self):
        """Cursos que vieram do Censo INEP (têm codigo_inep_curso)."""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) AS total FROM cursos WHERE codigo_inep_curso IS NOT NULL")
            return c.fetchone()['total']
        finally:
            conn.close()

    def nome_por_id(self, id):
        """Nome do registro (ou None se não existir) — consulta leve, sem relacionamentos."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT nome FROM cursos WHERE id=?", (id,))
            row = c.fetchone()
            conn.close()
            return row['nome'] if row else None
        except Exception:
            return None

    def resumos_por_ids(self, ids):
        """{id: resumo} em UMA consulta (usado para enriquecer a lista de favoritos)."""
        ids = list({int(i) for i in ids})
        if not ids:
            return {}
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT id, nome, instituicao, area, modalidade, grau, duracao FROM cursos WHERE id IN (" + ','.join('?' * len(ids)) + ")", ids)
            return {r['id']: dict(r) for r in c.fetchall()}
        finally:
            conn.close()

    def agrupados_por_nome_e_area(self):
        """[{nome, area, total, id, descricao, grau}] — um item por (nome, área),
        com quantas instituições oferecem, o menor id e a maior descrição.
        Usado pela compatibilidade do teste vocacional."""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute(
                "SELECT nome, area, COUNT(*) AS total, MIN(id) AS id, "
                "MAX(COALESCE(descricao, '')) AS descricao, MAX(COALESCE(grau, '')) AS grau "
                "FROM cursos GROUP BY nome, area"
            )
            return [dict(r) for r in c.fetchall()]
        finally:
            conn.close()
