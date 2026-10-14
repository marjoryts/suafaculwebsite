"""Testes do catálogo ampliado de vestibulares (database/vestibulares_dados.py):
seed sem duplicatas, migração de bancos antigos, novos campos e
integração com busca, filtros e cadastro do admin."""
import re
import sqlite3
from datetime import date

from database.vestibulares_dados import VESTIBULARES, SEED_VERSAO

REGIOES_VALIDAS = {'Nacional', 'Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul'}


def _listar(client, **params):
    params.setdefault('incluir_privados', 'true')
    params.setdefault('limit', 100)
    r = client.get('/api/vestibulares/listar', query_string=params)
    assert r.status_code == 200
    return r.get_json()


# ── Integridade do catálogo ──

def test_catalogo_sem_nomes_duplicados():
    nomes = [v['nome'].lower() for v in VESTIBULARES]
    assert len(nomes) == len(set(nomes))
    todos = nomes + [n.lower() for v in VESTIBULARES for n in v.get('nomes_anteriores', [])]
    assert len(todos) == len(set(todos)), 'um nome antigo não pode coincidir com outro registro'


def test_catalogo_campos_obrigatorios_e_formatos():
    for v in VESTIBULARES:
        for campo in ('nome', 'instituicao', 'tipo_instituicao', 'cidade', 'regiao',
                      'periodo_inscricao', 'data_prova', 'descricao', 'link_edital',
                      'taxa_inscricao', 'cursos_oferecidos', 'requisitos', 'fonte'):
            assert v.get(campo), f"{v['nome']}: campo '{campo}' vazio"
        assert v['tipo_instituicao'] in ('Pública', 'Privada'), v['nome']
        assert v['regiao'] in REGIOES_VALIDAS, v['nome']
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', v['data_prova']), v['nome']
        date.fromisoformat(v['data_prova'])
        assert v['link_edital'].startswith('https://'), v['nome']


def test_catalogo_cobre_todas_as_regioes_e_publicas_e_privadas():
    assert {v['regiao'] for v in VESTIBULARES} == REGIOES_VALIDAS
    assert {v['tipo_instituicao'] for v in VESTIBULARES} == {'Pública', 'Privada'}
    assert len(VESTIBULARES) >= 40


# ── Seed em banco novo ──

def test_banco_novo_recebe_catalogo_completo(client):
    body = _listar(client)
    assert body['total'] == len(VESTIBULARES)
    nomes = {v['nome'] for v in body['vestibulares']}
    for esperado in ('Vestibular ITA 2027', 'Vestibular IME 2027', 'Vestibular de Verão PUC-SP 2027',
                     'Vestibular Estadual UERJ 2027 - Exame Discursivo', 'Vestibular UFSM 2027'):
        assert esperado in nomes


def test_novos_campos_vem_na_api(client):
    body = _listar(client, busca='ITA 2027')
    ita = next(v for v in body['vestibulares'] if v['nome'] == 'Vestibular ITA 2027')
    assert ita['taxa_inscricao'].startswith('R$ 195')
    assert 'Aeroespacial' in ita['cursos_oferecidos']
    assert 'brasileiro nato' in ita['requisitos']
    assert ita['fonte']


def test_init_db_e_idempotente(app):
    from database.init_db import init_db
    init_db()
    init_db()
    from config.database import get_connection
    conn = get_connection()
    dup = conn.execute(
        "SELECT lower(nome), COUNT(*) FROM vestibulares GROUP BY lower(nome) HAVING COUNT(*) > 1"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM vestibulares").fetchone()[0]
    conn.close()
    assert dup == []
    assert total == len(VESTIBULARES)


# ── Migração de bancos já existentes ──

def test_registro_antigo_e_atualizado_sem_trocar_id(app):
    from config.database import get_connection
    from database.init_db import sincronizar_vestibulares

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM vestibulares WHERE nome='Vestibular UFRGS 2027'")
    vest_id = c.fetchone()[0]
    # Simula o registro como ele estava no seed antigo
    c.execute("UPDATE vestibulares SET nome='Vestibular UFRGS 2026', data_prova='2026-11-29', "
              "taxa_inscricao=NULL, seed_versao=0 WHERE id=?", (vest_id,))
    c.execute("INSERT INTO favoritos (usuario_id, tipo, item_id, nome_item) VALUES (1, 'vestibular', ?, 'UFRGS')", (vest_id,))
    conn.commit()

    resultado = sincronizar_vestibulares(conn)
    assert resultado['atualizados'] >= 1
    assert resultado['inseridos'] == 0

    row = c.execute("SELECT nome, data_prova, taxa_inscricao, seed_versao FROM vestibulares WHERE id=?", (vest_id,)).fetchone()
    assert tuple(row) == ('Vestibular UFRGS 2027', '2026-11-28', 'R$ 180,00', SEED_VERSAO)
    assert c.execute("SELECT COUNT(*) FROM favoritos WHERE item_id=?", (vest_id,)).fetchone()[0] == 1
    conn.close()


def test_registro_na_versao_atual_nao_e_sobrescrito(app):
    """Edições feitas depois do seed (ex.: pelo admin direto no banco) não
    podem ser revertidas a cada inicialização."""
    from config.database import get_connection
    from database.init_db import sincronizar_vestibulares

    conn = get_connection()
    conn.execute("UPDATE vestibulares SET taxa_inscricao='R$ 999,00' WHERE nome='Fuvest 2027'")
    conn.commit()
    sincronizar_vestibulares(conn)
    taxa = conn.execute("SELECT taxa_inscricao FROM vestibulares WHERE nome='Fuvest 2027'").fetchone()[0]
    conn.close()
    assert taxa == 'R$ 999,00'


# ── Busca e filtros ──

def test_filtro_varias_regioes(client):
    body = _listar(client, regiao=['Norte', 'Nordeste'])
    regioes = {v['regiao'] for v in body['vestibulares']}
    assert regioes == {'Norte', 'Nordeste'}
    esperado = sum(1 for v in VESTIBULARES if v['regiao'] in ('Norte', 'Nordeste'))
    assert body['total'] == esperado


def test_filtro_mes_dezembro(client):
    body = _listar(client, mes=12)
    assert body['total'] > 0
    assert all(v['data_prova'][5:7] == '12' for v in body['vestibulares'])


def test_filtro_privadas(client):
    body = _listar(client, tipo_instituicao='Privada')
    assert body['total'] == sum(1 for v in VESTIBULARES if v['tipo_instituicao'] == 'Privada')
    assert all(v['tipo_instituicao'] == 'Privada' for v in body['vestibulares'])


def test_padrao_sem_incluir_privados_mostra_so_publicas(client):
    r = client.get('/api/vestibulares/listar?limit=100')
    body = r.get_json()
    assert body['total'] == sum(1 for v in VESTIBULARES if v['tipo_instituicao'] == 'Pública')


def test_busca_encontra_por_curso_oferecido(client):
    body = _listar(client, busca='Aeroespacial')
    assert [v['nome'] for v in body['vestibulares']] == ['Vestibular ITA 2027']


def test_filtro_curso_usa_cursos_oferecidos(client):
    body = _listar(client, curso='Medicina')
    nomes = {v['nome'] for v in body['vestibulares']}
    assert 'Vestibular Famerp 2027' in nomes
    assert 'Vestibular ITA 2027' not in nomes


def test_proximas_provas_vem_antes_das_ja_realizadas(client):
    vests = _listar(client)['vestibulares']
    hoje = date.today().isoformat()
    passou = [v['data_prova'] < hoje for v in vests if v['data_prova']]
    # depois do primeiro vestibular já realizado, não pode aparecer um futuro
    if True in passou:
        assert all(passou[passou.index(True):])
    futuras = [v['data_prova'] for v in vests if v['data_prova'] and v['data_prova'] >= hoje]
    assert futuras == sorted(futuras)


# ── Cadastro pelo admin ──

def test_admin_cadastra_com_novos_campos(admin_client):
    r = admin_client.post('/api/vestibulares/criar', data={
        'nome': 'Vestibular Teste Catálogo', 'instituicao': 'TESTE - Instituição de Teste',
        'tipo_instituicao': 'Privada', 'cidade': 'Mogi das Cruzes', 'regiao': 'Sudeste',
        'periodo_inscricao': '01/11 a 30/11/2026', 'data_prova': '2026-12-20',
        'descricao': 'desc', 'link_edital': 'https://example.com',
        'taxa_inscricao': 'R$ 50,00', 'cursos_oferecidos': 'Direito', 'requisitos': 'Ensino médio',
    })
    assert r.get_json()['success'] is True
    body = _listar(admin_client, busca='Teste Catálogo')
    v = body['vestibulares'][0]
    assert (v['taxa_inscricao'], v['cursos_oferecidos'], v['requisitos']) == ('R$ 50,00', 'Direito', 'Ensino médio')


def test_admin_nao_duplica_vestibular(admin_client):
    r = admin_client.post('/api/vestibulares/criar', data={
        'nome': 'fuvest 2027', 'instituicao': 'USP', 'tipo_instituicao': 'Pública',
        'cidade': 'São Paulo', 'regiao': 'Sudeste', 'periodo_inscricao': '',
        'data_prova': '', 'descricao': '', 'link_edital': '',
    })
    body = r.get_json()
    assert body['success'] is False
    assert 'Já existe' in body['message']


def test_pagina_vestibulares_tem_todos_os_meses(client):
    html = client.get('/vestibulares').get_data(as_text=True)
    for numero in range(1, 13):
        assert f'value="{numero}"' in html


# ── Página inicial ──

def test_home_mostra_proximos_vestibulares_do_banco(app, client):
    proximos = app.Vestibular().proximos(limite=8)
    assert proximos, 'o catálogo deve ter provas futuras'
    hoje = date.today().isoformat()
    assert all(v['data_prova'] >= hoje for v in proximos)
    assert [v['data_prova'] for v in proximos] == sorted(v['data_prova'] for v in proximos)

    html = client.get('/').get_data(as_text=True)
    for v in proximos:
        assert v['nome'] in html
    assert 'href="/vestibulares"' in html
