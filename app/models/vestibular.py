import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection, hoje_iso, inserir, like_ci

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
            # Ignora acentos/maiúsculas (like_ci) e procura também na descrição e
            # na lista de cursos oferecidos pelo processo seletivo.
            campos = ('nome', 'instituicao', 'cidade', 'descricao', 'cursos_oferecidos')
            sql += " AND (" + " OR ".join(like_ci(campo) for campo in campos) + ")"
            params.extend([like] * len(campos))
        if filtros.get('meses'):
            # data_prova é texto ISO 'AAAA-MM-DD': o mês são os caracteres 6-7
            # (SUBSTR é padrão SQL; evita strftime, exclusivo do SQLite).
            meses = [f"{int(m):02d}" for m in filtros['meses']]
            sql += (" AND data_prova LIKE '____-__-%'"
                    f" AND SUBSTR(data_prova, 6, 2) IN ({','.join('?' * len(meses))})")
            params.extend(meses)
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
            # "Hoje" vem do Python (hoje_iso): a função de data atual do SQLite não é portável.
            sql = ("SELECT * FROM vestibulares" + where +
                   " ORDER BY (data_prova IS NULL OR date(data_prova) IS NULL),"
                   " (date(data_prova) < ?), data_prova ASC, nome ASC")
            params.append(hoje_iso())
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

    def proximos(self, limite=8):
        """Vestibulares com prova de hoje em diante, da mais próxima para a
        mais distante (usado no carrossel da página inicial)."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "SELECT * FROM vestibulares WHERE date(data_prova) >= ? "
                "ORDER BY date(data_prova) ASC, nome ASC LIMIT ?", (hoje_iso(), limite)
            )
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

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
            id = inserir(
                c,
                "INSERT INTO vestibulares (nome, instituicao, tipo_instituicao, cidade, regiao, periodo_inscricao, data_prova, descricao, link_edital, taxa_inscricao, cursos_oferecidos, requisitos) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (dados['nome'].strip(), dados.get('instituicao',''), dados['tipo_instituicao'], dados['cidade'],
                 dados['regiao'], dados['periodo_inscricao'], dados['data_prova'] or None, dados['descricao'], dados['link_edital'],
                 dados.get('taxa_inscricao') or None, dados.get('cursos_oferecidos') or None, dados.get('requisitos') or None)
            )
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Vestibular criado com sucesso!', 'id': id}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def listar_para_validacao(self):
        """Campos usados pela automação de validação (todos os vestibulares)."""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT id, nome, instituicao, data_prova, faculdade_id FROM vestibulares")
            return [dict(r) for r in c.fetchall()]
        finally:
            conn.close()

    def aplicar_validacoes(self, itens):
        """Grava o resultado da validação numa única transação (tudo ou nada).

        itens: [{'vestibular_id', 'status_validacao', 'cadastrado_ok', 'faculdade_id'}]
        faculdade_id None preserva o vínculo já existente.
        """
        conn = get_connection()
        try:
            c = conn.cursor()
            for i in itens:
                c.execute(
                    """UPDATE vestibulares
                       SET status_validacao=?, cadastrado_ok=?, faculdade_id=COALESCE(?, faculdade_id),
                           ultima_validacao=CURRENT_TIMESTAMP
                       WHERE id=?""",
                    (i['status_validacao'], 1 if i['cadastrado_ok'] else 0, i['faculdade_id'], i['vestibular_id'])
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def nome_por_id(self, id):
        """Nome do registro (ou None se não existir) — consulta leve, sem relacionamentos."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT nome FROM vestibulares WHERE id=?", (id,))
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
            c.execute("SELECT id, nome, instituicao, cidade, data_prova, periodo_inscricao, status_validacao FROM vestibulares WHERE id IN (" + ','.join('?' * len(ids)) + ")", ids)
            return {r['id']: dict(r) for r in c.fetchall()}
        finally:
            conn.close()
