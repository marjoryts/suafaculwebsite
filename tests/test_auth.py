"""Testes de autenticação: login local, registro, login com Google
(fluxo de redirecionamento e tratamento de erros do callback)."""
import pytest


class DummyOAuthError(Exception):
    pass


def test_registro_normal(client):
    r = client.post('/api/usuario/registrar', data={
        'username': 'joaosilva', 'email': 'joao@example.com', 'password': 'senha123'
    })
    body = r.get_json()
    assert body['success'] is True


def test_registro_email_duplicado(client):
    client.post('/api/usuario/registrar', data={
        'username': 'user1', 'email': 'dup@example.com', 'password': 'senha123'
    })
    r = client.post('/api/usuario/registrar', data={
        'username': 'user2', 'email': 'dup@example.com', 'password': 'outrasenha'
    })
    body = r.get_json()
    assert body['success'] is False
    assert 'cadastrado' in body['message'].lower()


def test_login_normal_sucesso(client):
    client.post('/api/usuario/registrar', data={
        'username': 'maria', 'email': 'maria@example.com', 'password': 'senha123'
    })
    r = client.post('/api/usuario/login', data={'username': 'maria', 'password': 'senha123'})
    body = r.get_json()
    assert body['success'] is True
    with client.session_transaction() as sess:
        assert sess['user_id'] == body['user']['id']


def test_login_senha_incorreta(client):
    client.post('/api/usuario/registrar', data={
        'username': 'pedro', 'email': 'pedro@example.com', 'password': 'senhacerta'
    })
    r = client.post('/api/usuario/login', data={'username': 'pedro', 'password': 'errada'})
    body = r.get_json()
    assert body['success'] is False


def test_login_admin_padrao(client):
    r = client.post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    body = r.get_json()
    assert body['success'] is True
    assert body['user']['tipo'] == 'admin'


# ── Login com Google ────────────────────────────────────────────────────

def test_google_auth_desabilitado_sem_credenciais(client):
    r = client.get('/auth/google', follow_redirects=False)
    assert r.status_code == 302
    assert 'oauth_error=nao_configurado' in r.headers['Location']


def test_google_auth_redirect_valido_com_credenciais(app, client, monkeypatch):
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'fake-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'fake-secret')
    app.oauth_service.init_app(app.app)  # reprocessa com as credenciais setadas agora
    r = client.get('/auth/google', follow_redirects=False)
    assert r.status_code == 302
    location = r.headers['Location']
    assert location.startswith('https://accounts.google.com/o/oauth2/v2/auth')
    assert 'client_id=fake-client-id' in location
    assert 'state=' in location and 'nonce=' in location


def test_google_callback_cancelado_pelo_usuario(app, client, monkeypatch):
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'fake-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'fake-secret')
    app.oauth_service.init_app(app.app)
    r = client.get('/auth/google/callback?error=access_denied', follow_redirects=False)
    assert r.status_code == 302
    assert 'oauth_error=cancelado' in r.headers['Location']


def test_google_callback_falha_comunicacao(app, client, monkeypatch):
    """Simula falha ao trocar o código por token (rede indisponível, por
    exemplo) — o usuário deve ser redirecionado com uma mensagem amigável,
    nunca ver um erro 500 cru."""
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'fake-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'fake-secret')
    app.oauth_service.init_app(app.app)

    class FakeGoogleClient:
        def authorize_access_token(self):
            raise RuntimeError("network unreachable")

    monkeypatch.setattr(app.oauth_service, 'google_client', lambda: FakeGoogleClient())
    r = client.get('/auth/google/callback?code=abc&state=xyz', follow_redirects=False)
    assert r.status_code == 302
    assert 'oauth_error=comunicacao' in r.headers['Location']


def test_google_login_usuario_novo_cria_conta(app, client, monkeypatch):
    """Usuário nunca visto antes faz login pelo Google -> conta nova
    criada e sessão iniciada, sem exigir senha."""
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'fake-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'fake-secret')
    app.oauth_service.init_app(app.app)

    class FakeGoogleClient:
        def authorize_access_token(self):
            return {
                'userinfo': {
                    'sub': 'google-uid-123',
                    'email': 'novo@example.com',
                    'email_verified': True,
                    'name': 'Novo Usuario',
                    'picture': 'https://example.com/avatar.png',
                }
            }

    monkeypatch.setattr(app.oauth_service, 'google_client', lambda: FakeGoogleClient())
    r = client.get('/auth/google/callback?code=abc&state=xyz', follow_redirects=False)
    assert r.status_code == 302
    assert r.headers['Location'].endswith('/dashboard')

    usuario = app.Usuario().buscar_por_email('novo@example.com')
    assert usuario is not None
    assert usuario['google_id'] == 'google-uid-123'
    assert usuario['auth_provider'] == 'google'


def test_google_login_usuario_existente_vincula_conta(app, client, monkeypatch):
    """E-mail já cadastrado localmente + login Google com e-mail
    verificado -> vincula à conta existente em vez de duplicar."""
    client.post('/api/usuario/registrar', data={
        'username': 'anacarolina', 'email': 'ana@example.com', 'password': 'senha123'
    })

    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'fake-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'fake-secret')
    app.oauth_service.init_app(app.app)

    class FakeGoogleClient:
        def authorize_access_token(self):
            return {'userinfo': {'sub': 'google-uid-999', 'email': 'ana@example.com', 'email_verified': True, 'name': 'Ana'}}

    monkeypatch.setattr(app.oauth_service, 'google_client', lambda: FakeGoogleClient())
    r = client.get('/auth/google/callback?code=abc&state=xyz', follow_redirects=False)
    assert r.headers['Location'].endswith('/dashboard')

    usuarios = app.Usuario().listar()
    contas_com_esse_email = [u for u in usuarios if u['email'] == 'ana@example.com']
    assert len(contas_com_esse_email) == 1  # não duplicou a conta
