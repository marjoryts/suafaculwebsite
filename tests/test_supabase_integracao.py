"""Migração para o Supabase (PostgreSQL): contrato usado pelo app Mobile,
health check e o isolamento da Data API (RLS)."""
import psycopg
import pytest

from config.database import conexao_direta, get_connection


def _registrar(client, nome='lia', email='lia@x.com', senha='segredo1'):
    r = client.post('/api/v1/auth/registrar', json={'nome_usuario': nome, 'email': email, 'password': senha})
    assert r.status_code == 201, r.get_json()
    return r.get_json()['data']


def _auth(sessao):
    return {'Authorization': 'Bearer ' + sessao['tokens']['access_token']}


# ── Login por identificador (usuário ou e-mail), como na tela do app ──

@pytest.mark.parametrize('identificador', ['lia', 'lia@x.com', 'LIA@X.COM'])
def test_login_por_identificador(client, identificador):
    _registrar(client)
    r = client.post('/api/v1/auth/login', json={'identificador': identificador, 'password': 'segredo1'})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['data']['usuario']['nome_usuario'] == 'lia'
    assert r.get_json()['data']['tokens']['refresh_token']


def test_login_por_identificador_nao_revela_se_conta_existe(client):
    _registrar(client)
    erradas = [client.post('/api/v1/auth/login', json={'identificador': i, 'password': 'errada99'})
               for i in ('lia', 'ninguem')]
    assert [r.status_code for r in erradas] == [401, 401]
    assert {r.get_json()['error']['code'] for r in erradas} == {'INVALID_CREDENTIALS'}
    assert erradas[0].get_json()['error']['message'] == erradas[1].get_json()['error']['message']


def test_login_por_email_continua_funcionando(client):
    _registrar(client)
    r = client.post('/api/v1/auth/login', json={'email': 'lia@x.com', 'password': 'segredo1'})
    assert r.status_code == 200


# ── Perfil: telefone e troca de senha com confirmação da senha atual ──

def test_telefone_e_salvo_validado_e_apagado(client):
    h = _auth(_registrar(client))
    r = client.patch('/api/v1/me', json={'telefone': '(11) 98888-7777'}, headers=h)
    assert r.status_code == 200 and r.get_json()['data']['telefone'] == '(11) 98888-7777'
    assert client.get('/api/v1/me', headers=h).get_json()['data']['telefone'] == '(11) 98888-7777'
    assert client.patch('/api/v1/me', json={'telefone': 'abc'}, headers=h).status_code == 422
    r = client.patch('/api/v1/me', json={'telefone': ''}, headers=h)
    assert r.status_code == 200 and r.get_json()['data']['telefone'] is None


def test_troca_de_senha_confere_a_senha_atual_quando_enviada(client):
    h = _auth(_registrar(client))
    r = client.patch('/api/v1/me', headers=h, json={'password': 'nova-senha-1', 'password_confirm': 'nova-senha-1',
                                                    'senha_atual': 'errada'})
    assert r.status_code == 422
    assert client.post('/api/v1/auth/login', json={'identificador': 'lia', 'password': 'segredo1'}).status_code == 200
    r = client.patch('/api/v1/me', headers=h, json={'password': 'nova-senha-1', 'password_confirm': 'nova-senha-1',
                                                    'senha_atual': 'segredo1'})
    assert r.status_code == 200
    assert client.post('/api/v1/auth/login', json={'identificador': 'lia', 'password': 'nova-senha-1'}).status_code == 200


def test_tipo_de_acesso_continua_nao_editavel(client):
    h = _auth(_registrar(client))
    assert client.patch('/api/v1/me', json={'tipo': 'admin'}, headers=h).status_code == 422


# ── Health check ──

def test_health_ok(client):
    r = client.get('/api/health')
    assert r.status_code == 200 and r.get_json() == {'status': 'ok', 'database': 'ok'}
    assert r.headers['Cache-Control'] == 'no-store'


def test_health_sem_banco_responde_503_sem_detalhes(client, monkeypatch):
    import config.database as db
    monkeypatch.setenv('DATABASE_URL', 'postgresql://ninguem:x@127.0.0.1:1/nada?connect_timeout=1')
    monkeypatch.setattr(db.ConnectionPool, '__init__', _pool_que_falha)
    db.fechar_pool()
    r = client.get('/api/health')
    assert r.status_code == 503
    assert r.get_json() == {'status': 'degraded', 'database': 'unavailable'}
    assert '127.0.0.1' not in r.get_data(as_text=True)


def _pool_que_falha(self, *a, **k):
    raise psycopg.OperationalError('sem conexão')


# ── RLS: Data API do Supabase (anon/authenticated) não lê nem escreve nada ──

def _papel_existe(conn, papel):
    return conn.execute("SELECT 1 FROM pg_roles WHERE rolname=?", (papel,)).fetchone() is not None


@pytest.mark.parametrize('papel', ['anon', 'authenticated'])
@pytest.mark.parametrize('tabela', ['usuarios', 'favoritos', 'refresh_tokens', 'teste_vocacional_resultados',
                                    'faculdades', 'cursos', 'vestibulares'])
def test_data_api_fechada_para_papeis_do_postgrest(app, novo_banco, papel, tabela):
    conn = conexao_direta(novo_banco())
    try:
        if not _papel_existe(conn, papel):
            pytest.skip(f'papel {papel} não existe neste servidor (só no Supabase)')
        conn.execute(f'SET ROLE {papel}')
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(f'SELECT * FROM public.{tabela} LIMIT 1')
        conn.rollback()
        conn.execute(f'SET ROLE {papel}')
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(f'DELETE FROM public.{tabela}')
    finally:
        conn.rollback()
        conn.close()


def test_todas_as_tabelas_tem_rls_e_politica_so_para_o_backend(app):
    conn = get_connection()
    try:
        sem_rls = [r[0] for r in conn.execute(
            "SELECT relname FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind='r' "
            "AND NOT relrowsecurity").fetchall()]
        papeis = {r[0] for r in conn.execute(
            "SELECT DISTINCT unnest(roles)::text FROM pg_policies WHERE schemaname='public'").fetchall()}
    finally:
        conn.close()
    assert sem_rls == []
    assert papeis == {'suafacul_backend'}


# ── Catálogo de formações e filtro exato (home e detalhe de curso do app) ──

def test_catalogo_de_formacoes_aponta_para_cursos_reais(client):
    r = client.get('/api/v1/cursos/catalogo')
    assert r.status_code == 200
    itens = r.get_json()['data']
    assert len(itens) == r.get_json()['meta']['total'] > 0
    for item in itens[:10]:
        if item['curso_id'] is None:
            continue
        curso = client.get(f"/api/v1/cursos/{item['curso_id']}").get_json()['data']
        from config.database import normalizar
        assert normalizar(curso['nome']) == normalizar(item['nome'])
        assert item['total_instituicoes'] >= 1


def test_faculdades_por_curso_exato(client):
    exato = client.get('/api/v1/faculdades?curso=Medicina&exato=true&limit=100').get_json()
    contem = client.get('/api/v1/faculdades?curso=Medicina&limit=100').get_json()
    assert 0 < exato['meta']['total'] <= contem['meta']['total']
    ids_exato = {f['id'] for f in exato['data']}
    for fid in list(ids_exato)[:5]:
        nomes = [c['nome'] for c in client.get(f'/api/v1/faculdades/{fid}').get_json()['data']['cursos']]
        assert 'Medicina' in nomes


# ── Busca sem diferenciar acentos (cursos e vestibulares, como já era em faculdades) ──

@pytest.mark.parametrize('termo', ['administracao', 'ADMINISTRAÇÃO', 'Administração'])
def test_busca_de_cursos_ignora_acentos(client, termo):
    nomes = {c['nome'] for c in client.get(f'/api/v1/cursos?busca={termo}&limit=100').get_json()['data']}
    assert 'Administração' in nomes


def test_busca_de_vestibulares_ignora_acentos(client):
    com = client.get('/api/v1/vestibulares?busca=São Paulo&incluir_privados=true&limit=100').get_json()['meta']['total']
    sem = client.get('/api/v1/vestibulares?busca=sao paulo&incluir_privados=true&limit=100').get_json()['meta']['total']
    assert com == sem > 0


def test_busca_escapa_curingas(client):
    assert client.get('/api/v1/cursos?busca=%25%25&limit=5').get_json()['meta']['total'] == 0
