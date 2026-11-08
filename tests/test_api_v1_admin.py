"""Painel administrativo pela API v1 (app): permissões conferidas no servidor e
as mesmas operações/regras do painel Web (/api/*)."""
import pytest


def _bearer(client, login, senha):
    r = client.post('/api/v1/auth/login', json={'email': login, 'password': senha})
    assert r.status_code == 200, r.get_data(as_text=True)
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + r.get_json()['data']['tokens']['access_token']
    return client


@pytest.fixture()
def admin(app):
    # O conftest cria o admin com SUAFACUL_ADMIN_PASSWORD=admin123 (só nos testes).
    from app.models.usuario import Usuario
    email = [u for u in Usuario().listar() if u['tipo'] == 'admin'][0]['email']
    return _bearer(app.app.test_client(), email, 'admin123')


@pytest.fixture()
def aluno(app):
    c = app.app.test_client()
    c.post('/api/v1/auth/registrar', json={'nome_usuario': 'aluno1', 'email': 'aluno1@x.com', 'password': 'segredo1'})
    return _bearer(c, 'aluno1@x.com', 'segredo1')


ROTAS_ADMIN = [
    ('get', '/api/v1/admin/estatisticas', None),
    ('get', '/api/v1/admin/usuarios', None),
    ('post', '/api/v1/admin/usuarios', {'nome_usuario': 'x', 'email': 'x@x.com', 'password': 'segredo1'}),
    ('patch', '/api/v1/admin/usuarios/1', {'nome_usuario': 'x', 'email': 'x@x.com'}),
    ('delete', '/api/v1/admin/usuarios/1', None),
    ('post', '/api/v1/admin/faculdades', {'nome': 'X'}),
    ('patch', '/api/v1/admin/faculdades/1', {'nome': 'X'}),
    ('delete', '/api/v1/admin/faculdades/1', None),
    ('post', '/api/v1/admin/faculdades/importacoes', {'codigos': ['1']}),
    ('post', '/api/v1/admin/cursos', {'nome': 'X', 'instituicao': 'Y'}),
    ('post', '/api/v1/admin/vestibulares', {'nome': 'X', 'instituicao': 'Y'}),
    ('post', '/api/v1/admin/vestibulares/validacao', {'aplicar': True}),
]


@pytest.mark.parametrize('metodo,url,corpo', ROTAS_ADMIN)
def test_sem_token_401_e_aluno_403_em_toda_rota_admin(client, aluno, metodo, url, corpo):
    """Usuário comum não acessa dados nem operações admin por chamada direta à API."""
    assert getattr(client, metodo)(url, json=corpo).status_code == 401
    r = getattr(aluno, metodo)(url, json=corpo)
    assert r.status_code == 403 and r.get_json()['error']['code'] == 'FORBIDDEN'


def test_rebaixar_admin_tira_o_acesso_na_hora(app, admin):
    """O papel vem do banco a cada requisição, não do token."""
    from app.models.usuario import Usuario
    assert admin.get('/api/v1/admin/estatisticas').status_code == 200
    eu = [u for u in Usuario().listar() if u['tipo'] == 'admin'][0]
    Usuario().definir_tipo(eu['id'], 'aluno')
    assert admin.get('/api/v1/admin/estatisticas').status_code == 403


def test_estatisticas_iguais_as_do_painel_web(admin, admin_client):
    app_stats = admin.get('/api/v1/admin/estatisticas').get_json()['data']['stats']
    web_stats = admin_client.get('/api/admin/stats').get_json()['stats']
    assert app_stats == web_stats and app_stats['total_usuarios'] >= 1


def test_crud_de_usuarios_com_as_regras_do_painel(admin):
    r = admin.post('/api/v1/admin/usuarios', json={'nome_usuario': 'bia', 'email': 'bia@x.com', 'password': 'segredo1', 'tipo': 'admin'})
    assert r.status_code == 201 and r.get_json()['data']['tipo'] == 'admin'
    novo = r.get_json()['data']
    assert 'senha' not in novo
    assert admin.post('/api/v1/admin/usuarios', json={'nome_usuario': 'bia', 'email': 'bia@x.com', 'password': 'segredo1'}).status_code == 409
    assert admin.post('/api/v1/admin/usuarios', json={'nome_usuario': 'c', 'email': 'ruim', 'password': 'segredo1'}).status_code == 422

    r = admin.patch(f"/api/v1/admin/usuarios/{novo['id']}", json={'nome_usuario': 'bia2', 'email': 'bia@x.com', 'tipo': 'aluno'})
    assert r.status_code == 200 and r.get_json()['data'] == {'id': novo['id'], 'nome_usuario': 'bia2', 'email': 'bia@x.com', 'tipo': 'aluno'}
    lista = admin.get('/api/v1/admin/usuarios').get_json()
    assert any(u['nome_usuario'] == 'bia2' for u in lista['data']) and all('senha' not in u for u in lista['data'])

    assert admin.delete(f"/api/v1/admin/usuarios/{novo['id']}").status_code == 204
    assert admin.delete(f"/api/v1/admin/usuarios/{novo['id']}").status_code == 404


def test_admin_nao_remove_o_proprio_acesso_nem_se_exclui(app, admin):
    from app.models.usuario import Usuario
    eu = [u for u in Usuario().listar() if u['tipo'] == 'admin'][0]
    r = admin.patch(f"/api/v1/admin/usuarios/{eu['id']}", json={'nome_usuario': eu['nome_usuario'], 'email': eu['email'], 'tipo': 'aluno'})
    assert r.status_code == 403
    assert admin.delete(f"/api/v1/admin/usuarios/{eu['id']}").status_code == 403


def test_faculdades_cursos_e_vestibulares(admin):
    r = admin.post('/api/v1/admin/faculdades', json={'nome': 'Faculdade Teste', 'sigla': 'FT', 'uf': 'SP', 'cidade': 'Santos'})
    assert r.status_code == 201
    fac = r.get_json()['data']
    assert fac['sigla'] == 'FT'
    assert admin.post('/api/v1/admin/faculdades', json={'nome': ''}).status_code == 422
    r = admin.patch(f"/api/v1/admin/faculdades/{fac['id']}", json={'cidade': 'Campinas'})
    assert r.get_json()['data']['cidade'] == 'Campinas' and r.get_json()['data']['sigla'] == 'FT'  # só o enviado muda

    r = admin.post('/api/v1/admin/cursos', json={'nome': 'Curso Teste', 'instituicao': 'Faculdade Teste',
                                                  'faculdade_id': fac['id'], 'area': 'Tecnologia', 'modalidade': 'ead'})
    assert r.status_code == 201 and r.get_json()['data']['faculdade_id'] == fac['id']
    assert admin.post('/api/v1/admin/cursos', json={'nome': 'Sem instituição'}).status_code == 422

    r = admin.post('/api/v1/admin/vestibulares', json={'nome': 'Vestibular Teste', 'instituicao': 'FT', 'taxa_inscricao': 'R$ 50'})
    assert r.status_code == 201 and r.get_json()['data']['taxa_inscricao'] == 'R$ 50'
    assert admin.post('/api/v1/admin/vestibulares', json={'nome': 'vestibular teste', 'instituicao': 'FT'}).status_code == 409

    previa = admin.post('/api/v1/admin/vestibulares/validacao', json={'aplicar': False})
    assert previa.status_code == 200

    assert admin.delete(f"/api/v1/admin/faculdades/{fac['id']}").status_code == 204
    assert admin.delete(f"/api/v1/admin/faculdades/{fac['id']}").status_code == 404


def test_importacao_valida_a_entrada_sem_chamar_o_emec(admin, monkeypatch):
    from app.services import emec_service
    chamadas = []
    monkeypatch.setattr(emec_service, 'importar_todas_faculdades_por_uf', lambda uf: chamadas.append(uf) or {'success': True, 'uf': uf})
    assert admin.post('/api/v1/admin/faculdades/importacoes', json={'uf': 'XX'}).status_code == 422
    assert admin.post('/api/v1/admin/faculdades/importacoes', json={}).status_code == 422
    r = admin.post('/api/v1/admin/faculdades/importacoes', json={'uf': 'sp'})
    assert r.status_code == 200 and chamadas == ['SP']


def test_painel_web_continua_igual(admin_client):
    """As rotas antigas do painel Web agora usam o mesmo admin_service: mesmo formato de resposta."""
    r = admin_client.post('/api/cursos/criar', data={'nome': '', 'instituicao': ''}).get_json()
    assert r == {'success': False, 'message': 'Nome e instituição são obrigatórios.'}
    r = admin_client.post('/api/faculdades/criar', data={'nome': 'Web Teste'}).get_json()
    assert r['success'] is True and r['id']
    r = admin_client.post('/api/faculdades/deletar', data={'id': r['id']}).get_json()
    assert r['success'] is True
