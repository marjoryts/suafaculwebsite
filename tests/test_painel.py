"""Dashboard do usuário e painel administrativo: dados reais nos cards,
perfil próprio, e separação de permissões entre aluno e administrador."""
import json


def _registrar_e_logar(client, username='aluna', email='aluna@exemplo.com', senha='segredo123'):
    client.post('/api/usuario/registrar', data={'username': username, 'email': email, 'password': senha})
    r = client.post('/api/usuario/login', data={'username': username, 'password': senha})
    assert r.get_json()['success'] is True
    return r.get_json()['user']


def _criar_vestibular(app, **kwargs):
    dados = {'nome': 'Vestibular Teste', 'instituicao': 'UTST', 'tipo_instituicao': 'Pública',
             'cidade': 'Campinas', 'regiao': 'Sudeste', 'periodo_inscricao': '01/01 a 31/01',
             'data_prova': '2099-11-20', 'descricao': '', 'link_edital': 'https://exemplo.com/edital'}
    dados.update(kwargs)
    return app.Vestibular().criar(dados)['id']


# ── Dashboard do usuário ──

def test_dashboard_exige_login(client):
    r = client.get('/dashboard')
    assert r.status_code == 302
    assert '/login' in r.headers['Location']


def test_dashboard_mostra_dados_reais_do_usuario(app, client):
    _registrar_e_logar(client)
    vid = _criar_vestibular(app, nome='Vestibular Futuro Teste', data_prova='2099-11-20')
    client.post('/api/favoritos/adicionar', data={'tipo': 'vestibular', 'item_id': vid, 'nome_item': 'Vestibular Futuro Teste'})
    client.post('/api/teste_vocacional/salvar', data={
        'perfil_principal': 'criativo',
        'perfis_json': json.dumps({'scores': {'criativo': 6, 'tecnico': 2, 'humano': 2}}),
    })
    html = client.get('/dashboard').data.decode()
    assert 'Vestibular Futuro Teste' in html          # próximas provas + salvos recentemente
    assert '20/11/2099' in html
    assert 'Perfil Criativo / Comunicativo' in html   # último teste vocacional
    assert '60%' in html                              # 6 de 10 pontos
    assert 'data-contador="vestibular">1<' in html


def test_dashboard_de_aluno_nao_mostra_link_admin(client):
    _registrar_e_logar(client)
    html = client.get('/dashboard').data.decode()
    assert 'href="/admin"' not in html
    assert 'Painel administrativo' not in html


def test_dashboard_de_admin_mostra_link_admin(admin_client):
    html = admin_client.get('/dashboard').data.decode()
    assert 'href="/admin"' in html


def test_prova_passada_nao_aparece_em_proximas(app, client):
    user = _registrar_e_logar(client)
    vid = _criar_vestibular(app, nome='Vestibular Antigo Teste', data_prova='2001-01-10')
    app.Favorito().adicionar(user['id'], 'vestibular', vid, 'Vestibular Antigo Teste')
    assert app.Favorito().proximos_vestibulares(user['id']) == []


# ── Perfil próprio ──

def test_usuario_atualiza_o_proprio_perfil(client):
    _registrar_e_logar(client)
    r = client.post('/api/usuario/perfil', data={'username': 'aluna2', 'email': 'nova@exemplo.com',
                                                  'password': 'novasenha', 'password_confirm': 'novasenha'})
    assert r.get_json()['success'] is True
    client.get('/logout')
    login = client.post('/api/usuario/login', data={'username': 'aluna2', 'password': 'novasenha'}).get_json()
    assert login['success'] is True
    assert login['user']['email'] == 'nova@exemplo.com'


def test_perfil_valida_confirmacao_de_senha(client):
    _registrar_e_logar(client)
    r = client.post('/api/usuario/perfil', data={'username': 'aluna', 'email': 'aluna@exemplo.com',
                                                  'password': 'abcdef', 'password_confirm': 'outra'})
    assert r.get_json()['success'] is False


def test_perfil_rejeita_nome_ja_usado(client):
    client.post('/api/usuario/registrar', data={'username': 'ocupado', 'email': 'ocupado@exemplo.com', 'password': 'x12345'})
    _registrar_e_logar(client)
    r = client.post('/api/usuario/perfil', data={'username': 'ocupado', 'email': 'aluna@exemplo.com'})
    body = r.get_json()
    assert body['success'] is False
    assert 'em uso' in body['message']


def test_perfil_exige_login(client):
    r = client.post('/api/usuario/perfil', data={'username': 'x', 'email': 'x@x.com'})
    assert r.status_code == 401


def test_perfil_nao_permite_virar_admin(app, client):
    user = _registrar_e_logar(client)
    client.post('/api/usuario/perfil', data={'username': 'aluna', 'email': 'aluna@exemplo.com', 'tipo': 'admin'})
    assert app.Usuario().buscar_por_id(user['id'])['tipo'] == 'aluno'


# ── Permissões ──

def test_aluno_nao_acessa_admin(client):
    _registrar_e_logar(client)
    r = client.get('/admin')
    assert r.status_code == 302
    assert r.headers['Location'].endswith('/dashboard')
    for rota in ('/api/admin/stats', '/api/usuario/listar'):
        assert client.get(rota).status_code == 403, rota
    assert client.post('/api/cursos/criar', data={'nome': 'X', 'instituicao': 'Y'}).status_code == 403
    assert client.post('/api/vestibulares/criar', data={'nome': 'X', 'instituicao': 'Y'}).status_code == 403


def test_anonimo_nao_cria_curso_nem_vestibular(client):
    assert client.post('/api/cursos/criar', data={'nome': 'X', 'instituicao': 'Y'}).status_code == 401
    assert client.post('/api/vestibulares/criar', data={'nome': 'X', 'instituicao': 'Y'}).status_code == 401


def test_buscar_usuario_so_proprio_ou_admin(client):
    outro = client.post('/api/usuario/registrar', data={'username': 'outro', 'email': 'outro@exemplo.com', 'password': 'x12345'})
    assert outro.get_json()['success']
    assert client.get('/api/usuario/buscar?id=1').status_code == 401     # anônimo
    user = _registrar_e_logar(client)
    assert client.get(f"/api/usuario/buscar?id={user['id']}").get_json()['success'] is True
    assert client.get('/api/usuario/buscar?id=1').status_code == 403     # conta de outra pessoa


def test_admin_cria_curso_e_vestibular(admin_client):
    r = admin_client.post('/api/cursos/criar', data={'nome': 'Curso Admin Teste', 'instituicao': 'Inst Teste',
                                                     'modalidade': 'ead', 'tipo_instituicao': 'Privada'})
    assert r.get_json()['success'] is True
    r = admin_client.post('/api/vestibulares/criar', data={'nome': 'Vest Admin Teste', 'instituicao': 'IT',
                                                           'tipo_instituicao': 'Pública', 'cidade': '', 'regiao': '',
                                                           'periodo_inscricao': '', 'data_prova': '', 'descricao': '',
                                                           'link_edital': ''})
    assert r.get_json()['success'] is True


def test_admin_stats_tem_dados_do_painel(admin_client):
    body = admin_client.get('/api/admin/stats').get_json()
    assert body['success'] is True
    for chave in ('total_usuarios', 'total_admins', 'total_alunos', 'novos_usuarios_30d', 'total_cursos',
                  'total_faculdades', 'total_vestibulares', 'vestibulares_ativos', 'vestibulares_encerrados',
                  'total_favoritos', 'total_testes_vocacionais', 'faculdades_com_cursos'):
        assert isinstance(body['stats'][chave], int), chave
    assert isinstance(body['automacoes'], list)


def test_admin_painel_tem_todas_as_secoes(admin_client):
    html = admin_client.get('/admin').data.decode()
    for secao in ('visao-geral', 'usuarios', 'faculdades', 'cursos', 'vestibulares', 'sistema'):
        assert f'id="{secao}"' in html, secao
