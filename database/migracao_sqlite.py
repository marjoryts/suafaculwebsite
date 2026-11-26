"""Migração dos dados de um banco SQLite antigo (database/suafacul.db) para o
PostgreSQL do Supabase.

Uso (ver docs/migracao-supabase.md):
    flask --app wsgi migrar-sqlite database/suafacul.db --simular   # só relatório
    flask --app wsgi migrar-sqlite database/suafacul.db             # grava

Garantias:
  * O SQLite é aberto em modo SOMENTE LEITURA (mode=ro): o banco antigo nunca
    é alterado nem apagado — ele continua sendo o backup até a validação.
  * Tudo numa única transação no destino: ou migra tudo, ou nada. Antes do
    COMMIT confere, tabela por tabela, que cada id esperado chegou.
  * Os ids são preservados (favoritos e resultados continuam apontando para
    os mesmos registros) e as sequências continuam de onde o SQLite parou
    (inclusive ids já apagados, como o AUTOINCREMENT fazia).
  * Recusa gravar num destino que já tem dados de usuário, a menos que
    `substituir=True` (que apaga o conteúdo das tabelas do app no destino).
  * Dados que violariam as regras do esquema novo são tratados como a regra
    manda e LISTADOS no relatório: vínculo com usuário inexistente em
    resultados de teste vira NULL (ON DELETE SET NULL); favoritos/sessões de
    usuário inexistente são descartados (ON DELETE CASCADE); vínculo com
    faculdade inexistente vira NULL.
"""
import sqlite3
from datetime import datetime

from config.database import conexao_direta
from database.init_db import aplicar_migracoes

# Ordem respeita as chaves estrangeiras.
TABELAS = ['usuarios', 'faculdades', 'cursos', 'vestibulares', 'cursos_catalogo', 'favoritos',
           'teste_vocacional_resultados', 'refresh_tokens', 'automacao_logs']
# Tabelas com dados de pessoas: se já houver algo no destino, não sobrescreve.
TABELAS_DE_USUARIO = ['usuarios', 'favoritos', 'teste_vocacional_resultados', 'refresh_tokens']
OBSOLETAS = ['vestibular_inscricoes']

_COLUNAS_TEMPO = {'created_at', 'updated_at', 'executado_em', 'iniciado_em', 'finalizado_em',
                  'ultima_validacao', 'expira_em', 'usado_em', 'revogado_em'}
_FORMATOS_TEMPO = ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S',
                   '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d')


class MigracaoRecusada(Exception):
    pass


def _abrir_sqlite(caminho):
    conn = sqlite3.connect(f'file:{caminho}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _tabelas_sqlite(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _colunas_sqlite(conn, tabela):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({tabela})")]


def _colunas_pg(pg, tabela):
    c = pg.execute("SELECT column_name FROM information_schema.columns "
                   "WHERE table_schema='public' AND table_name=? ORDER BY ordinal_position", (tabela,))
    return [r[0] for r in c.fetchall()]


def _tempo(valor):
    """Texto de data do SQLite -> texto ISO aceito pelo TIMESTAMPTZ (UTC), ou None."""
    if valor in (None, ''):
        return None
    texto = str(valor).strip()
    for formato in _FORMATOS_TEMPO:
        try:
            return datetime.strptime(texto, formato).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    return None


def _ler(conn_sqlite, tabela):
    return [dict(r) for r in conn_sqlite.execute(f"SELECT * FROM {tabela} ORDER BY id")]


def _sequencia_sqlite(conn_sqlite, tabela):
    if 'sqlite_sequence' not in _tabelas_sqlite(conn_sqlite):
        return 0
    r = conn_sqlite.execute("SELECT seq FROM sqlite_sequence WHERE name=?", (tabela,)).fetchone()
    return int(r[0]) if r and r[0] else 0


def _transformar(tabela, linha, contexto, avisos):
    """Ajusta uma linha às regras do esquema PostgreSQL. None = descartar."""
    for coluna in list(linha):
        if coluna in _COLUNAS_TEMPO:
            original = linha[coluna]
            linha[coluna] = _tempo(original)
            if original not in (None, '') and linha[coluna] is None:
                avisos.append(f"{tabela} id={linha.get('id')}: {coluna}={original!r} não é uma data; gravado vazio.")
    # NOT NULL com default no destino: sem valor, deixa o banco preencher.
    for coluna in ('created_at', 'updated_at', 'executado_em'):
        if coluna in linha and linha[coluna] is None:
            del linha[coluna]

    usuarios = contexto['usuarios']
    if tabela == 'usuarios':
        linha['tipo'] = linha.get('tipo') if linha.get('tipo') in ('aluno', 'admin') else 'aluno'
        linha['auth_provider'] = linha.get('auth_provider') or 'local'
    elif tabela in ('cursos', 'vestibulares'):
        if linha.get('faculdade_id') is not None and linha['faculdade_id'] not in contexto['faculdades']:
            avisos.append(f"{tabela} id={linha['id']}: faculdade_id={linha['faculdade_id']} inexistente → NULL.")
            linha['faculdade_id'] = None
        if tabela == 'vestibulares' and 'cadastrado_ok' in linha:
            linha['cadastrado_ok'] = 1 if linha['cadastrado_ok'] else 0
    elif tabela == 'teste_vocacional_resultados':
        if linha.get('usuario_id') is not None and linha['usuario_id'] not in usuarios:
            avisos.append(f"teste_vocacional_resultados id={linha['id']}: usuario_id={linha['usuario_id']} "
                          "inexistente → NULL (ON DELETE SET NULL).")
            linha['usuario_id'] = None
    elif tabela in ('favoritos', 'refresh_tokens'):
        if linha.get('usuario_id') not in usuarios:
            avisos.append(f"{tabela} id={linha['id']}: usuario_id={linha.get('usuario_id')} inexistente → "
                          "descartado (ON DELETE CASCADE).")
            return None
    elif tabela == 'automacao_logs':
        linha['sucesso'] = 1 if linha.get('sucesso', 1) else 0
        if not linha.get('status'):
            linha['status'] = 'sucesso' if linha['sucesso'] else 'falha'
    return linha


def migrar(caminho_sqlite, url_destino, simular=False, substituir=False, aplicar_esquema=True, saida=print):
    """Copia os dados do SQLite para o PostgreSQL. Devolve o relatório (dict)."""
    origem = _abrir_sqlite(caminho_sqlite)
    pg = conexao_direta(url_destino)
    relatorio = {'tabelas': {}, 'avisos': [], 'simulacao': simular, 'ignoradas': []}
    try:
        verificacao = origem.execute("PRAGMA integrity_check").fetchone()[0]
        if verificacao != 'ok':
            raise MigracaoRecusada(f"O SQLite de origem está corrompido (integrity_check: {verificacao}).")

        pg.execute("SET LOCAL TIME ZONE 'UTC'")
        if aplicar_esquema:
            aplicar_migracoes(pg)
        tabelas_origem = _tabelas_sqlite(origem)

        ocupadas = [t for t in TABELAS_DE_USUARIO
                    if pg.execute(f"SELECT EXISTS (SELECT 1 FROM public.{t})").fetchone()[0]]
        if ocupadas and not substituir:
            raise MigracaoRecusada(
                "O destino já tem dados em " + ', '.join(ocupadas) + ". Nada foi gravado. Use um banco "
                "vazio ou a opção de substituir (apaga o conteúdo das tabelas do app no destino).")
        if substituir or any(pg.execute(f"SELECT EXISTS (SELECT 1 FROM public.{t})").fetchone()[0]
                             for t in TABELAS):
            # Catálogo semeado por um init-db anterior também é substituído pelo do SQLite,
            # para que os ids (referenciados pelos favoritos) sejam exatamente os antigos.
            pg.execute("TRUNCATE " + ', '.join(f'public.{t}' for t in TABELAS) + " RESTART IDENTITY")

        contexto = {'usuarios': set(), 'faculdades': set()}
        for tabela in TABELAS:
            if tabela not in tabelas_origem:
                relatorio['tabelas'][tabela] = {'origem': 0, 'migradas': 0, 'descartadas': 0}
                continue
            colunas_destino = set(_colunas_pg(pg, tabela))
            colunas_origem = _colunas_sqlite(origem, tabela)
            fora = [c for c in colunas_origem if c not in colunas_destino]
            if fora:
                relatorio['avisos'].append(f"{tabela}: colunas sem equivalente no esquema novo ignoradas: {fora}")
            linhas = _ler(origem, tabela)
            novas = []
            for linha in linhas:
                linha = {k: v for k, v in linha.items() if k in colunas_destino}
                linha = _transformar(tabela, linha, contexto, relatorio['avisos'])
                if linha is not None:
                    novas.append(linha)
            _inserir_lote(pg, tabela, novas)
            if tabela in ('usuarios', 'faculdades'):
                contexto[tabela] = {l['id'] for l in novas}
            _ajustar_sequencia(pg, tabela, max([l['id'] for l in novas] + [_sequencia_sqlite(origem, tabela)]))
            _conferir(pg, tabela, {l['id'] for l in novas})
            relatorio['tabelas'][tabela] = {'origem': len(linhas), 'migradas': len(novas),
                                            'descartadas': len(linhas) - len(novas)}

        for tabela in OBSOLETAS:
            if tabela in tabelas_origem:
                total = origem.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
                if total:
                    relatorio['avisos'].append(
                        f"{tabela} (tabela obsoleta, sem uso no app) tem {total} linha(s) — NÃO migrada; "
                        "os dados continuam no SQLite. Exporte-os se forem necessários.")
                relatorio['ignoradas'].append(tabela)

        if simular:
            pg.rollback()
        else:
            pg.commit()
    except Exception:
        pg.rollback()
        raise
    finally:
        pg.close()
        origem.close()

    for tabela, n in relatorio['tabelas'].items():
        saida(f"  {tabela:<30} origem={n['origem']:<6} migradas={n['migradas']:<6} descartadas={n['descartadas']}")
    for aviso in relatorio['avisos']:
        saida(f"  AVISO: {aviso}")
    saida("Simulação: nada foi gravado no destino." if simular else
          "Migração concluída. O SQLite de origem não foi alterado (mantenha-o como backup).")
    return relatorio


def _inserir_lote(pg, tabela, linhas):
    if not linhas:
        return
    por_colunas = {}
    for linha in linhas:  # linhas com o mesmo conjunto de colunas vão no mesmo lote
        por_colunas.setdefault(tuple(linha), []).append(linha)
    for colunas, grupo in por_colunas.items():
        sql = (f"INSERT INTO public.{tabela} ({', '.join(colunas)}) OVERRIDING SYSTEM VALUE "
               f"VALUES ({', '.join('?' * len(colunas))})")
        pg.cursor().executemany(sql, [tuple(l[c] for c in colunas) for l in grupo])


def _ajustar_sequencia(pg, tabela, ultimo_id):
    """Próximo id = último usado no SQLite + 1 (inclusive ids já apagados)."""
    if ultimo_id:
        pg.execute(f"SELECT setval(pg_get_serial_sequence('public.{tabela}', 'id'), ?, true)", (ultimo_id,))
    else:
        pg.execute(f"SELECT setval(pg_get_serial_sequence('public.{tabela}', 'id'), 1, false)")


def _conferir(pg, tabela, ids_esperados):
    ids = {r[0] for r in pg.execute(f"SELECT id FROM public.{tabela}").fetchall()}
    if ids != ids_esperados:
        faltando = sorted(ids_esperados - ids)[:10]
        sobrando = sorted(ids - ids_esperados)[:10]
        raise MigracaoRecusada(f"Conferência falhou em {tabela}: faltando {faltando}, sobrando {sobrando}.")
