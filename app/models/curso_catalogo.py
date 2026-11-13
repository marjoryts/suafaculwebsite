import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection, normalizar


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
                "SELECT normalizar(nome) AS n, COUNT(DISTINCT COALESCE(CAST(faculdade_id AS TEXT), instituicao)) AS total "
                "FROM cursos WHERE normalizar(nome) IN (" + ','.join('?' * len(nomes)) + ") GROUP BY normalizar(nome)",
                list(nomes)
            )
            totais = {r['n']: r['total'] for r in c.fetchall()}
            for item in itens:
                item['total_instituicoes'] = totais.get(normalizar(item['nome']), 0)
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
