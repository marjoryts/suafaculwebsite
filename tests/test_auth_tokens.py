"""Etapa 5: autenticação do Mobile por e-mail e senha (access + refresh rotativo)."""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from itsdangerous import URLSafeSerializer

from app.models.refresh_token import RefreshToken
from app.services import token_service
from config.database import get_connection

SENHA = 'segredo1'


class Relogio:
    """Substitui o relógio do token_service para simular a passagem do tempo."""

    def __init__(self, monkeypatch):
        self.deslocamento = timedelta(0)
        monkeypatch.setattr(token_service, '_agora', lambda: datetime.now(timezone.utc) + self.deslocamento)

    def avancar(self, **kwargs):
        self.deslocamento += timedelta(**kwargs)


@pytest.fixture()
def relogio(monkeypatch):
    return Relogio(monkeypatch)


def _registrar(client, nome='ana', email='ana@x.com', senha=SENHA):
    return client.post('/api/v1/auth/registrar', json={'nome_usuario': nome, 'email': email, 'password': senha})


def _login(client, email='ana@x.com', senha=SENHA):
    return client.post('/api/v1/auth/login', json={'email': email, 'password': senha})


def _tokens(resposta):
    assert resposta.status_code in (200, 201), resposta.get_data(as_text=True)
    return resposta.get_json()['data']['tokens']


def _refresh(client, token):
    return client.post('/api/v1/auth/refresh', json={'refresh_token': token})


def _me(client, access):
    return client.get('/api/v1/me', headers={'Authorization': f'Bearer {access}'})


def _erro(resposta, status, code):
    assert resposta.status_code == status, resposta.get_data(as_text=True)
    erro = resposta.get_json()['error']
    assert erro['code'] == code and erro['request_id'] == resposta.headers['X-Request-ID']
    if status == 401:
        assert resposta.headers['WWW-Authenticate'] == 'Bearer'
    return erro


def _linhas_refresh():
    conn = get_connection()
    linhas = [dict(r) for r in conn.execute("SELECT * FROM refresh_tokens ORDER BY id")]
    conn.close()
    return linhas


# ── Cadastro e login ────────────────────────────────────────────────────

def test_registrar_devolve_usuario_e_tokens_com_os_prazos_definidos(client):
    r = _registrar(client)
    assert r.status_code == 201
    dado = r.get_json()['data']
    assert dado['usuario']['email'] == 'ana@x.com' and dado['usuario']['tipo'] == 'aluno'
    assert 'senha' not in dado['usuario']
    t = dado['tokens']
    assert t['token_type'] == 'Bearer' and t['expires_in'] == 15 * 60
    assert t['refresh_expires_in'] == 30 * 24 * 3600
    assert _me(client, t['access_token']).get_json()['data']['nome_usuario'] == 'ana'


def test_refresh_token_e_guardado_apenas_como_hash(client):
    t = _tokens(_registrar(client))
    linhas = _linhas_refresh()
    assert len(linhas) == 1
    assert linhas[0]['token_hash'] == hashlib.sha256(t['refresh_token'].encode()).hexdigest()
    assert t['refresh_token'] not in str(linhas[0]) and t['access_token'] not in str(linhas[0])


def test_registrar_valida_conflito_senha_email_e_tipos(client):
    _registrar(client)
    e = _erro(_registrar(client, 'outra', 'ana@x.com'), 409, 'CONFLICT')
    assert 'cadastrado' in e['message']
    _erro(_registrar(client, 'ana', 'nova@x.com'), 409, 'CONFLICT')
    _erro(_registrar(client, 'bia', 'bia@x.com', '123'), 422, 'VALIDATION_ERROR')
    _erro(_registrar(client, 'bia', 'sem-arroba'), 422, 'VALIDATION_ERROR')
    _erro(client.post('/api/v1/auth/registrar', json={'nome_usuario': 5, 'email': 'a@b.com', 'password': SENHA}),
          422, 'VALIDATION_ERROR')
    _erro(client.post('/api/v1/auth/registrar', json={}), 422, 'VALIDATION_ERROR')
    _erro(client.post('/api/v1/auth/registrar', data='x=1'), 415, 'UNSUPPORTED_MEDIA_TYPE')


def test_login_por_email_ignora_maiusculas_e_abre_sessao_por_dispositivo(app, client):
    _registrar(client)
    celular = app.app.test_client()
    a = _tokens(_login(celular, 'ANA@X.COM'))
    b = _tokens(_login(app.app.test_client()))
    assert a['refresh_token'] != b['refresh_token']
    familias = {l['familia_id'] for l in _linhas_refresh()}
    assert len(familias) == 3  # registro + dois logins = três sessões independentes


def test_login_erro_e_identico_para_email_inexistente_e_senha_errada(client):
    _registrar(client)
    a = _erro(_login(client, 'ana@x.com', 'errada123'), 401, 'INVALID_CREDENTIALS')
    b = _erro(_login(client, 'ninguem@x.com', SENHA), 401, 'INVALID_CREDENTIALS')
    assert a['message'] == b['message']
    _erro(_login(client, 'ana', SENHA), 401, 'INVALID_CREDENTIALS')  # só e-mail: nome de usuário não loga
    _erro(client.post('/api/v1/auth/login', json={'email': '', 'password': ''}), 422, 'VALIDATION_ERROR')


def test_conta_criada_pelo_app_tambem_loga_no_site_mesma_identidade(client):
    _registrar(client)
    r = client.post('/api/usuario/login', data={'username': 'ana@x.com', 'password': SENHA})
    assert r.get_json()['success'] is True


def test_cookie_do_site_nao_autentica_a_api(client):
    client.post('/api/usuario/registrar', data={'username': 'web', 'email': 'web@x.com', 'password': SENHA})
    client.post('/api/usuario/login', data={'username': 'web', 'password': SENHA})
    assert client.get('/dashboard').status_code == 200  # logado no site
    _erro(client.get('/api/v1/me'), 401, 'UNAUTHENTICATED')  # mas a API exige Bearer


# ── Access token ────────────────────────────────────────────────────────

def test_access_token_ausente_malformado_ou_adulterado(client):
    t = _tokens(_registrar(client))
    _erro(client.get('/api/v1/me'), 401, 'UNAUTHENTICATED')
    _erro(client.get('/api/v1/me', headers={'Authorization': 'Token abc'}), 401, 'INVALID_TOKEN')
    _erro(client.get('/api/v1/me', headers={'Authorization': 'Bearer '}), 401, 'INVALID_TOKEN')
    _erro(_me(client, t['access_token'][:-3] + 'xyz'), 401, 'INVALID_TOKEN')
    _erro(_me(client, 'lixo'), 401, 'INVALID_TOKEN')
    forjado = URLSafeSerializer('outra-chave', salt='suafacul.access-token.v1').dumps(
        {'uid': 1, 'fam': _linhas_refresh()[0]['familia_id'], 'exp': 9999999999})
    _erro(_me(client, forjado), 401, 'INVALID_TOKEN')  # assinado com outra chave


def test_access_token_expira_em_15_minutos(client, relogio):
    t = _tokens(_registrar(client))
    relogio.avancar(minutes=14, seconds=50)
    assert _me(client, t['access_token']).status_code == 200
    relogio.avancar(seconds=20)
    _erro(_me(client, t['access_token']), 401, 'TOKEN_EXPIRED')


def test_rota_de_autenticacao_opcional_rejeita_token_invalido(client, relogio):
    respostas = {f'q{i}': 'a' for i in range(1, 11)}
    assert client.post('/api/v1/teste-vocacional/resultados', json={'respostas': respostas}).status_code == 201
    _erro(client.post('/api/v1/teste-vocacional/resultados', json={'respostas': respostas},
                      headers={'Authorization': 'Bearer lixo'}), 401, 'INVALID_TOKEN')


# ── Refresh: rotação, reuso, expiração ──────────────────────────────────

def test_refresh_rotaciona_e_invalida_o_token_usado(client):
    t1 = _tokens(_registrar(client))
    t2 = _tokens(_refresh(client, t1['refresh_token']))
    t3 = _tokens(_refresh(client, t2['refresh_token']))
    assert len({t1['refresh_token'], t2['refresh_token'], t3['refresh_token']}) == 3
    assert _me(client, t3['access_token']).status_code == 200
    assert len({l['familia_id'] for l in _linhas_refresh()}) == 1  # mesma sessão, três elos
    assert [bool(l['usado_em']) for l in _linhas_refresh()] == [True, True, False]


def test_reuso_de_refresh_token_revoga_a_familia_inteira(app, client):
    t1 = _tokens(_registrar(client))
    outro_aparelho = _tokens(_login(app.app.test_client()))  # sessão independente do mesmo usuário
    t2 = _tokens(_refresh(client, t1['refresh_token']))

    _erro(_refresh(client, t1['refresh_token']), 401, 'REFRESH_TOKEN_REUSED')  # token antigo reapresentado
    _erro(_refresh(client, t2['refresh_token']), 401, 'INVALID_REFRESH_TOKEN')  # o "legítimo" também caiu
    _erro(_me(client, t2['access_token']), 401, 'INVALID_TOKEN')                # e o access da família
    assert all(l['motivo_revogacao'] == 'reuso_de_refresh_token' for l in _linhas_refresh()
               if l['familia_id'] == _linhas_refresh()[0]['familia_id'])
    # outra sessão do mesmo usuário continua intacta
    assert _me(client, outro_aparelho['access_token']).status_code == 200
    assert _refresh(client, outro_aparelho['refresh_token']).status_code == 200


def test_rotacao_concorrente_so_uma_requisicao_vence(client):
    t = _tokens(_registrar(client))
    linha = _linhas_refresh()[0]
    novo = {'familia_id': linha['familia_id'], 'usuario_id': linha['usuario_id'], 'token_hash': 'h1',
            'expira_em': '2099-01-01 00:00:00'}
    repo = RefreshToken()
    assert repo.rotacionar(linha['id'], novo, '2026-01-01 00:00:00') is True
    assert repo.rotacionar(linha['id'], {**novo, 'token_hash': 'h2'}, '2026-01-01 00:00:01') is False
    assert [l['token_hash'] for l in _linhas_refresh()][-1] == 'h1'  # o perdedor não gravou nada


def test_perder_a_corrida_no_refresh_e_tratado_como_reuso(client, monkeypatch):
    t = _tokens(_registrar(client))
    monkeypatch.setattr(RefreshToken, 'rotacionar', lambda self, *a, **k: False)
    _erro(_refresh(client, t['refresh_token']), 401, 'REFRESH_TOKEN_REUSED')
    assert all(l['revogado_em'] for l in _linhas_refresh())


def test_refresh_token_expira_em_30_dias(client, relogio):
    t = _tokens(_registrar(client))
    relogio.avancar(days=29, hours=23)
    t2 = _tokens(_refresh(client, t['refresh_token']))  # ainda válido; agora vale mais 30 dias
    relogio.avancar(days=30, minutes=1)
    _erro(_refresh(client, t2['refresh_token']), 401, 'REFRESH_TOKEN_EXPIRED')


def test_refresh_com_token_invalido_ou_campo_errado(client):
    _erro(_refresh(client, 'nao-existe'), 401, 'INVALID_REFRESH_TOKEN')
    _erro(client.post('/api/v1/auth/refresh', json={}), 401, 'INVALID_REFRESH_TOKEN')
    _erro(client.post('/api/v1/auth/refresh', json={'refresh_token': 123}), 422, 'VALIDATION_ERROR')
    _erro(client.post('/api/v1/auth/refresh', json=[1]), 422, 'VALIDATION_ERROR')


def test_access_token_nao_serve_como_refresh(client):
    t = _tokens(_registrar(client))
    _erro(_refresh(client, t['access_token']), 401, 'INVALID_REFRESH_TOKEN')


# ── Logout e revogação ──────────────────────────────────────────────────

def test_logout_revoga_sessao_imediatamente_e_e_idempotente(app, client):
    t = _tokens(_registrar(client))
    outro = _tokens(_login(app.app.test_client()))
    r = client.post('/api/v1/auth/logout', json={'refresh_token': t['refresh_token']})
    assert r.status_code == 204 and r.get_data() == b''
    _erro(_me(client, t['access_token']), 401, 'INVALID_TOKEN')       # access cortado na hora
    _erro(_refresh(client, t['refresh_token']), 401, 'INVALID_REFRESH_TOKEN')
    assert client.post('/api/v1/auth/logout', json={'refresh_token': t['refresh_token']}).status_code == 204
    assert client.post('/api/v1/auth/logout', json={'refresh_token': 'desconhecido'}).status_code == 204
    assert _me(client, outro['access_token']).status_code == 200      # outro aparelho segue logado


def test_trocar_senha_na_api_encerra_as_outras_sessoes_e_mantem_a_atual(app, client):
    a = _tokens(_registrar(client))
    b = _tokens(_login(app.app.test_client()))
    r = client.patch('/api/v1/me', json={'password': 'novasenha1', 'password_confirm': 'novasenha1',
                                         'password_atual': SENHA},
                     headers={'Authorization': f"Bearer {a['access_token']}"})
    assert r.status_code == 200
    assert _me(client, a['access_token']).status_code == 200            # sessão de quem trocou continua
    _erro(_me(client, b['access_token']), 401, 'INVALID_TOKEN')          # as outras caem
    _erro(_refresh(client, b['refresh_token']), 401, 'INVALID_REFRESH_TOKEN')
    _erro(_login(client, senha=SENHA), 401, 'INVALID_CREDENTIALS')
    assert _login(client, senha='novasenha1').status_code == 200


def test_trocar_senha_pelo_site_ou_admin_encerra_sessoes_do_app(app, client, admin_client):
    t = _tokens(_registrar(client))
    web = app.app.test_client()
    web.post('/api/usuario/login', data={'username': 'ana', 'password': SENHA})
    web.post('/api/usuario/perfil', data={'username': 'ana', 'email': 'ana@x.com', 'password_atual': SENHA,
                                          'password': 'viaweb123', 'password_confirm': 'viaweb123'})
    _erro(_me(client, t['access_token']), 401, 'INVALID_TOKEN')

    t2 = _tokens(_login(client, senha='viaweb123'))
    uid = app.Usuario().buscar_por_email('ana@x.com')['id']
    admin_client.post('/api/usuario/atualizar', data={'id': uid, 'username': 'ana', 'email': 'ana@x.com',
                                                      'password': 'admin-reset1'})
    _erro(_me(client, t2['access_token']), 401, 'INVALID_TOKEN')


def test_excluir_a_conta_remove_as_sessoes(app, client):
    t = _tokens(_registrar(client))
    conn = get_connection()
    conn.execute("DELETE FROM usuarios WHERE email='ana@x.com'")
    conn.commit()
    conn.close()
    assert _linhas_refresh() == []  # ON DELETE CASCADE
    _erro(_refresh(client, t['refresh_token']), 401, 'INVALID_REFRESH_TOKEN')
    _erro(_me(client, t['access_token']), 401, 'INVALID_TOKEN')


# ── Preparação para o login Google (sem implementá-lo) ──────────────────

def test_iniciar_sessao_independe_do_metodo_de_login(app, client):
    """Um futuro login Google validado no backend só precisa chamar iniciar_sessao()."""
    uid = app.Usuario().criar_via_google('g-123', 'goog@x.com', 'Goog', None)['user']['id']
    with app.app.app_context():
        t = token_service.iniciar_sessao(uid, 'Pixel 9')
    assert _me(client, t['access_token']).get_json()['data']['email'] == 'goog@x.com'
    assert _linhas_refresh()[0]['dispositivo'] == 'Pixel 9'
