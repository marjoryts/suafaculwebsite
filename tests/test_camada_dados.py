"""Etapa 2: acesso a dados centralizado e SQL portável.

Os dois primeiros testes são guardas de arquitetura: falham se alguém voltar
a espalhar SQL pela aplicação ou usar funções exclusivas do SQLite fora do
ponto único (config/database.py). Ver docs/banco-de-dados.md.
"""
import os
import re
from datetime import date, timedelta

from config.database import get_connection
from conftest import PROJECT_ROOT

APP_DIR = os.path.join(PROJECT_ROOT, 'app')


def _arquivos_py(base):
    for raiz, _, nomes in os.walk(base):
        if '__pycache__' in raiz:
            continue
        for nome in nomes:
            if nome.endswith('.py'):
                yield os.path.join(raiz, nome)


def test_sql_so_existe_nos_models():
    """Rotas e services não abrem conexão nem escrevem SQL: usam models."""
    violacoes = []
    for caminho in _arquivos_py(APP_DIR):
        rel = os.path.relpath(caminho, APP_DIR).replace('\\', '/')
        if rel.startswith('models/'):
            continue
        texto = open(caminho, encoding='utf-8').read()
        if re.search(r'get_connection|sqlite3|\.execute\(|cursor\(\)', texto):
            violacoes.append(rel)
    assert not violacoes, f"Acesso direto ao banco fora de app/models: {violacoes}"


def test_sem_construcoes_exclusivas_do_sqlite_no_codigo_da_aplicacao():
    proibidos = re.compile(r"lastrowid|strftime\('%[a-zA-Z]',|date\('now|datetime\('now|COLLATE NOCASE|"
                           r"INSERT OR (IGNORE|REPLACE)|PRAGMA|AUTOINCREMENT|GLOB ")
    violacoes = []
    for caminho in _arquivos_py(APP_DIR):
        for n, linha in enumerate(open(caminho, encoding='utf-8'), 1):
            if proibidos.search(linha):
                violacoes.append(f"{os.path.relpath(caminho, PROJECT_ROOT)}:{n}: {linha.strip()[:80]}")
    assert not violacoes, violacoes


# ── Comportamentos reescritos de forma portável ─────────────────────────

def _vestibular(app, nome, data_prova):
    return app.Vestibular().criar({
        'nome': nome, 'instituicao': 'Inst', 'tipo_instituicao': 'Pública', 'cidade': 'X', 'regiao': 'Sul',
        'periodo_inscricao': '', 'data_prova': data_prova, 'descricao': '', 'link_edital': ''})['id']


def test_filtro_por_mes_usa_substr_iso(app):
    _vestibular(app, 'Prova de Março', '2030-03-15')
    _vestibular(app, 'Prova de Outubro', '2030-10-02')
    _vestibular(app, 'Prova sem data', None)
    _vestibular(app, 'Prova data BR', '15/03/2030')  # formato não-ISO não casa com filtro de mês
    marco = [v['nome'] for v in app.Vestibular().listar({'meses': [3]})]
    assert 'Prova de Março' in marco
    assert 'Prova de Outubro' not in marco and 'Prova sem data' not in marco and 'Prova data BR' not in marco
    ambos = [v['nome'] for v in app.Vestibular().listar({'meses': [3, 10]})]
    assert {'Prova de Março', 'Prova de Outubro'} <= set(ambos)


def test_proximos_vestibulares_inclui_hoje_e_exclui_ontem(app):
    user = app.Usuario()
    user.criar('aluno1', 'aluno1@x.com', 'segredo1')
    uid = user.buscar_por_email('aluno1@x.com')['id']
    hoje = date.today().isoformat()
    ontem = (date.today() - timedelta(days=1)).isoformat()
    v_hoje = _vestibular(app, 'Prova Hoje', hoje)
    v_ontem = _vestibular(app, 'Prova Ontem', ontem)
    for vid, nome in ((v_hoje, 'Prova Hoje'), (v_ontem, 'Prova Ontem')):
        app.Favorito().adicionar(uid, 'vestibular', vid, nome)
    nomes = [p['nome'] for p in app.Favorito().proximos_vestibulares(uid)]
    assert nomes == ['Prova Hoje']


def test_stats_conta_novos_usuarios_dos_ultimos_30_dias(app, admin_client):
    app.Usuario().criar('antigo', 'antigo@x.com', 'segredo1')
    app.Usuario().criar('recente', 'recente@x.com', 'segredo1')
    conn = get_connection()
    conn.execute("UPDATE usuarios SET created_at='2020-01-01 00:00:00' WHERE nome_usuario IN ('antigo')")
    conn.commit()
    conn.close()
    stats = admin_client.get('/api/admin/stats').get_json()['stats']
    assert stats['total_usuarios'] >= 3
    # 'antigo' fica de fora; admin (bootstrap) e 'recente' entram
    assert stats['novos_usuarios_30d'] == stats['total_usuarios'] - 1


def test_automacao_log_registra_e_lista_em_ordem_recente(app):
    from app.models.automacao_log import AutomacaoLog
    log = AutomacaoLog()
    log.registrar('teste_a', True, resumo={'n': 1})
    log.registrar('teste_b', False, erro='boom')
    ultimos = log.ultimos(5)
    assert [u['tipo'] for u in ultimos][:2] == ['teste_b', 'teste_a']
    assert ultimos[0]['sucesso'] is False and ultimos[1]['resumo'] == {'n': 1}


def test_job_diario_registra_execucao_em_automacao_logs(app):
    from app.models.automacao_log import AutomacaoLog
    app.automacao_service.executar('validacao-vestibulares', origem='manual')
    ultimo = AutomacaoLog().ultimos(1)[0]
    assert ultimo['tipo'] == 'validacao_vestibulares' and ultimo['sucesso'] is True


def test_validacao_aplicar_grava_e_dry_run_nao_grava(app):
    vid = _vestibular(app, 'Prova Futura', (date.today() + timedelta(days=10)).isoformat())
    app.vestibular_service.validar_vestibulares(aplicar=False)
    assert app.Vestibular().buscar_por_id(vid)['status_validacao'] == 'nao_validado'
    resultado = app.vestibular_service.validar_vestibulares(aplicar=True)
    assert resultado['resumo']['aplicado'] is True
    assert app.Vestibular().buscar_por_id(vid)['status_validacao'] == 'ativo'


def test_inserir_devolve_id_gerado(app):
    novo = app.Curso().criar({'nome': 'Curso X', 'instituicao': 'Inst', 'faculdade_id': None,
                              'modalidade': 'presencial', 'descricao': '', 'duracao': '', 'grau': '',
                              'area': '', 'tipo_instituicao': 'Pública'})
    assert novo['success'] and isinstance(novo['id'], int)
    assert app.Curso().buscar_por_id(novo['id'])['nome'] == 'Curso X'
