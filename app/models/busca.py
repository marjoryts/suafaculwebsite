"""Consultas da busca dinâmica (autocomplete): só SQL. A composição e o
ranking de apresentação ficam em services/busca_service.py.
"""
from config.database import get_connection, sql_norm


def _rank_sql(coluna):
    # Mesma ordem de busca_service._rank(), calculada no banco para ordenar + LIMIT lá.
    n = sql_norm(coluna)
    return (f"CASE WHEN {n} LIKE :prefixo ESCAPE '\\' THEN 0 "
            f"WHEN {n} LIKE :palavra ESCAPE '\\' "
            f"  OR {n} LIKE :palavra_hifen ESCAPE '\\' THEN 1 ELSE 2 END")


class BuscaRepository:
    def _executar(self, sql, params):
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute(sql, params)
            return [dict(r) for r in c.fetchall()]
        finally:
            conn.close()

    def cursos(self, params_like):
        rank = _rank_sql('nome')
        n = sql_norm('nome')
        return self._executar(f"""
            SELECT MIN(nome) AS nome,
                   COUNT(DISTINCT COALESCE(CAST(faculdade_id AS TEXT), instituicao)) AS total,
                   MIN(area) AS area,
                   MIN({rank}) AS rank
            FROM cursos
            WHERE {n} LIKE :contem ESCAPE '\\'
            GROUP BY {n}
            ORDER BY rank, nome
            LIMIT :limite
        """, params_like)

    def faculdades(self, params_like):
        rank_nome = _rank_sql('nome')
        ns, nn = sql_norm('sigla'), sql_norm('nome')
        return self._executar(f"""
            SELECT id, nome, sigla, cidade, uf, tipo_instituicao,
                   CASE WHEN {ns} LIKE :prefixo ESCAPE '\\' THEN 0
                        ELSE {rank_nome} END AS rank
            FROM faculdades
            WHERE {nn} LIKE :contem ESCAPE '\\'
               OR {ns} LIKE :contem ESCAPE '\\'
            ORDER BY rank, nome
            LIMIT :limite
        """, params_like)

    def cidades(self, params_like):
        rank = _rank_sql('cidade')
        n = sql_norm('cidade')
        return self._executar(f"""
            SELECT MIN(cidade) AS cidade, uf, COUNT(*) AS total, MIN({rank}) AS rank
            FROM faculdades
            WHERE cidade IS NOT NULL AND TRIM(cidade) <> ''
              AND {n} LIKE :contem ESCAPE '\\'
            GROUP BY {n}, uf
            ORDER BY rank, total DESC, cidade
            LIMIT :limite
        """, params_like)

    def contagem_por_uf(self):
        return self._executar(
            "SELECT UPPER(TRIM(uf)) AS uf, COUNT(*) AS total FROM faculdades "
            "WHERE uf IS NOT NULL AND TRIM(uf) <> '' GROUP BY UPPER(TRIM(uf))", {})
