"""
Seed automático de dados de instituições/cursos numa subida com banco
vazio (deploy novo, ambiente novo) — pra não precisar clicar em
"Importar" no admin toda vez que troca de servidor.

Como funciona: se as tabelas `faculdades`/`cursos` estiverem vazias E os
arquivos abaixo existirem, importa automaticamente na inicialização do
app (reaproveita os mesmos importadores usados pelo upload manual no
admin — mesma lógica, mesma validação, sem duplicar código). Se os
arquivos não existirem, não faz nada (comportamento normal de dev/primeira
instalação sem seed).

Arquivos esperados (não versionados no Git — coloque uma vez por
ambiente, como o .env):
    data/seeds/instituicoes.csv   (CSV oficial de Dados Abertos do MEC)
    data/seeds/cursos.csv         (MICRODADOS_CADASTRO_CURSOS_<ano>.CSV do INEP)

Pra usar em produção: depois de fazer a importação manual uma vez pelo
admin, copie os DOIS arquivos originais que você baixou pra
`data/seeds/` (com esses nomes exatos) e comite/leve essa pasta junto do
deploy. Da próxima vez que o app subir com um banco vazio, ele se
autopopula sozinho.
"""
import os
import logging

logger = logging.getLogger('suafacul.seed')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEEDS_DIR = os.path.join(BASE_DIR, 'data', 'seeds')
CAMINHO_INSTITUICOES = os.path.join(SEEDS_DIR, 'instituicoes.csv')
CAMINHO_CURSOS = os.path.join(SEEDS_DIR, 'cursos.csv')


def _ja_tem_dados_importados(nome_tabela, condicao_sql):
    """Verifica se a tabela já tem alguma linha vinda de uma importação
    real (e-MEC/Censo) — não confundir com 'tabela vazia': o init_db.py
    semeia algumas faculdades/cursos de exemplo por padrão (fonte
    'manual', sem codigo_inep_curso), então a tabela NUNCA fica
    genuinamente vazia. O que importa aqui é se os dados oficiais já
    foram carregados alguma vez (por este seed ou por upload manual no
    admin) — se sim, não sobrescreve."""
    from config.database import get_connection
    conn = get_connection()
    c = conn.cursor()
    c.execute(f"SELECT COUNT(*) as total FROM {nome_tabela} WHERE {condicao_sql}")
    total = c.fetchone()['total']
    conn.close()
    return total > 0


def rodar_seed_automatico_se_necessario():
    """Chamado uma vez, na inicialização do app (depois de init_db()).
    Nunca lança exceção — uma falha aqui não pode impedir o site de
    subir; só registra no log e segue (o admin sempre pode importar
    manualmente depois)."""
    try:
        _seed_instituicoes_se_necessario()
    except Exception:
        logger.exception("[seed] Falha ao rodar seed automático de instituições")

    try:
        _seed_cursos_se_necessario()
    except Exception:
        logger.exception("[seed] Falha ao rodar seed automático de cursos")


def _seed_instituicoes_se_necessario():
    if not os.path.exists(CAMINHO_INSTITUICOES):
        return
    if _ja_tem_dados_importados('faculdades', "fonte IN ('emec', 'emec_csv_upload')"):
        logger.info("[seed] Já existem instituições importadas do e-MEC/MEC — seed automático pulado.")
        return

    from app.services import emec_service
    with open(CAMINHO_INSTITUICOES, 'rb') as f:
        conteudo = f.read()
    resultado = emec_service.importar_instituicoes_de_csv_upload(conteudo)
    logger.info(
        "[seed] Instituições importadas automaticamente de data/seeds/instituicoes.csv: "
        "%d criadas, %d atualizadas, %d falharam.",
        resultado.get('criadas', 0), resultado.get('atualizadas', 0), resultado.get('falhas', 0)
    )


def _seed_cursos_se_necessario():
    if not os.path.exists(CAMINHO_CURSOS):
        return
    if _ja_tem_dados_importados('cursos', "codigo_inep_curso IS NOT NULL"):
        logger.info("[seed] Já existem cursos importados do Censo INEP — seed automático pulado.")
        return

    from app.services import censo_service
    with open(CAMINHO_CURSOS, 'rb') as f:
        resultado = censo_service.importar_cursos_de_csv_upload(f)
    logger.info(
        "[seed] Cursos importados automaticamente de data/seeds/cursos.csv: "
        "%d criados, %d atualizados, %d sem faculdade local.",
        resultado.get('criados', 0), resultado.get('atualizados', 0), resultado.get('sem_faculdade_local', 0)
    )
