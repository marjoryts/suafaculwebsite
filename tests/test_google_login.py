"""Login com Google no app (POST /api/v1/auth/google) e a regra de conta
compartilhada com o site. Os tokens são assinados com uma chave RSA gerada no
teste; as "chaves do Google" são a parte pública dela (sem rede)."""
import time

import pytest
from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey

CLIENT_WEB = 'web-123.apps.googleusercontent.com'
CLIENT_ANDROID = 'android-456.apps.googleusercontent.com'

CHAVE = RSAKey.generate_key(2048, parameters={'kid': 'google-1'})
OUTRA_CHAVE = RSAKey.generate_key(2048, parameters={'kid': 'google-1'})  # mesmo kid, chave diferente


@pytest.fixture(autouse=True)
def google_configurado(app, monkeypatch):
    from app.services import google_service
    monkeypatch.setenv('GOOGLE_CLIENT_ID', CLIENT_WEB)
    monkeypatch.setenv('GOOGLE_ANDROID_CLIENT_ID', CLIENT_ANDROID)
    monkeypatch.setattr(google_service, '_chaves_do_google',
                        lambda: KeySet.import_key_set({'keys': [CHAVE.as_dict(private=False)]}))


def _token(chave=CHAVE, **mudancas):
    agora = int(time.time())
    claims = {'iss': 'https://accounts.google.com', 'aud': CLIENT_WEB, 'sub': 'g-111',
              'email': 'nova@gmail.com', 'email_verified': True, 'name': 'Nova Pessoa',
              'iat': agora, 'exp': agora + 3600}
    claims.update(mudancas)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode({'alg': 'RS256', 'kid': 'google-1'}, claims, chave)


def _entrar(client, token):
    return client.post('/api/v1/auth/google', json={'id_token': token})


def test_primeiro_login_cria_conta_aluno_e_abre_sessao(client):
    r = _entrar(client, _token())
    assert r.status_code == 200, r.get_json()
    dados = r.get_json()['data']
    assert dados['usuario']['email'] == 'nova@gmail.com' and dados['usuario']['tipo'] == 'aluno'
    assert dados['usuario']['auth_provider'] == 'google'
    assert dados['tokens']['token_type'] == 'Bearer'
    # mesma sessão do login por senha: o access token funciona no /me
    me = client.get('/api/v1/me', headers={'Authorization': 'Bearer ' + dados['tokens']['access_token']})
    assert me.get_json()['data']['email'] == 'nova@gmail.com'


def test_segundo_login_reusa_a_conta_e_aceita_client_android(client):
    id1 = _entrar(client, _token()).get_json()['data']['usuario']['id']
    id2 = _entrar(client, _token(aud=CLIENT_ANDROID)).get_json()['data']['usuario']['id']
    assert id1 == id2


def test_vincula_conta_local_existente_so_com_email_verificado(client):
    client.post('/api/v1/auth/registrar', json={'nome_usuario': 'ana', 'email': 'ana@gmail.com', 'password': 'segredo1'})
    r = _entrar(client, _token(sub='g-ana', email='ana@gmail.com', email_verified=False))
    assert r.status_code == 403 and r.get_json()['error']['code'] == 'EMAIL_NOT_VERIFIED'
    r = _entrar(client, _token(sub='g-ana', email='ana@gmail.com'))
    assert r.status_code == 200 and r.get_json()['data']['usuario']['nome_usuario'] == 'ana'  # a mesma conta


@pytest.mark.parametrize('token,motivo', [
    (lambda: _token(aud='outro-app.apps.googleusercontent.com'), 'audiência de outro app'),
    (lambda: _token(iss='https://evil.example.com'), 'emissor falso'),
    (lambda: _token(exp=int(time.time()) - 3600), 'expirado'),
    (lambda: _token(chave=OUTRA_CHAVE), 'assinado por outra chave'),
    (lambda: _token(email=None), 'sem e-mail'),
    (lambda: 'nao.e.um-token', 'malformado'),
    (lambda: '', 'vazio'),
])
def test_tokens_invalidos_sao_recusados(client, token, motivo):
    r = _entrar(client, token())
    assert r.status_code == 401, motivo
    assert r.get_json()['error']['code'] == 'INVALID_GOOGLE_TOKEN', motivo


def test_dados_do_cliente_nao_validados_nao_sao_aceitos(client):
    """Mandar claims "soltas" (sem assinatura do Google) não autentica."""
    r = client.post('/api/v1/auth/google', json={'id_token': '', 'email': 'admin@suafacul.local', 'sub': 'x'})
    assert r.status_code == 401


def test_sem_client_ids_configurados_responde_503(client, monkeypatch):
    monkeypatch.delenv('GOOGLE_CLIENT_ID')
    monkeypatch.delenv('GOOGLE_ANDROID_CLIENT_ID')
    r = _entrar(client, _token())
    assert r.status_code == 503 and r.get_json()['error']['code'] == 'GOOGLE_NOT_CONFIGURED'


def test_regra_de_conta_e_a_mesma_do_site(app):
    """O callback Web chama google_service.entrar_com_claims — a mesma função da API."""
    from app.services import google_service
    claims = {'sub': 'g-web', 'email': 'Web@Gmail.com', 'email_verified': True, 'name': 'Web'}
    u1 = google_service.entrar_com_claims(claims)
    u2 = google_service.entrar_com_claims(claims)
    assert u1['id'] == u2['id'] and u1['email'] == 'web@gmail.com'
