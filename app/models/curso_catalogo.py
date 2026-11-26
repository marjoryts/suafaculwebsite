import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection, normalizar, sql_norm


class CursoCatalogo:
    """Formações do catálogo da página inicial (tabela cursos_catalogo),
    com quantas instituições oferecem cada uma (contadas na tabela cursos,
    comparando o nome sem acento/caixa)."""

    def listar(self, area=None):
        conn = get_connection()
        try:
            c = conn.cursor()
            sql = ("SELECT id, nome, area, grau, duracao, descricao, imagem_url FROM cursos_catalogo")
            params = []
            if area:
                sql += " WHERE area = ?"
                params.append(area)
            c.execute(sql, params)
            # Ordem alfabética sem diferenciar acentos ("Análise" antes de "Arquitetura")
            itens = sorted((dict(r) for r in c.fetchall()), key=lambda i: normalizar(i['nome']))
            if not itens:
                return []

            nomes = {normalizar(i['nome']) for i in itens}
            c.execute(
                f"SELECT {sql_norm('nome')} AS n, COUNT(DISTINCT COALESCE(CAST(faculdade_id AS TEXT), instituicao)) AS total, "
                "MIN(id) AS curso_id "
                f"FROM cursos WHERE {sql_norm('nome')} IN (" + ','.join('?' * len(nomes)) + f") GROUP BY {sql_norm('nome')}",
                list(nomes)
            )
            totais = {r['n']: (r['total'], r['curso_id']) for r in c.fetchall()}
            for item in itens:
                total, curso_id = totais.get(normalizar(item['nome']), (0, None))
                item['total_instituicoes'] = total
                # Uma oferta real desse curso (tabela cursos): o app usa para
                # abrir o detalhe e para favoritar, como os cards do site.
                item['curso_id'] = curso_id
            return itens
        finally:
            conn.close()

    def areas(self):
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT DISTINCT area FROM cursos_catalogo WHERE area IS NOT NULL AND area <> ''")
            return sorted((r['area'] for r in c.fetchall()), key=normalizar)
        finally:
            conn.close()
