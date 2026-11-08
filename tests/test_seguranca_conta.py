"""Etapa de segurança: verificação de e-mail, recuperação de senha, limites de
tentativas, sessões e vinculação segura com Google. Os e-mails vão para a caixa
de saída em memória (EMAIL_MODO=memoria, ver conftest)."""
import logging
import re
import sqlite3
import time
from datetime import timedelta

import pytest
from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey

from app.services import codigo_service, email_service, limite_service

SENHA = 'segredo12'


def _ultimo_codigo(para=None):
    msgs = [m for m in email_service.caixa_de_saida if para is None or m['To'] == para]
    assert msgs, 'nenhum e-mail enviado'
    texto = msgs[-1].get_body(('plain',)).get_content()
    return re.search(r'Código: (\d{5})', texto).group(1)


def _registrar(client, nome='ana', email='ana@x.com', senha=SENHA):
    return client.post('/api/v1/auth/registrar', json={'nome_usuario': nome, 'email': email, 'password': senha})


def _erro(resposta, status, code):
    assert resposta.status_code == status, resposta.get_data(as_text=True)
    assert resposta.get_json()['error']['code'] == code
    return resposta.get_json()['error']


def _deslocar_relogio(monkeypatch, minutos):
    real = codigo_service._agora
    for modulo in (codigo_service, limite_service):
        monkeypatch.setattr(modulo, '_agora', lambda real=real: real() + timedelta(minutes=minutos))


# ── Cadastro e verificação ──────────────────────────────────────────────

def test_cadastro_cria_conta_nao_verificada_e_envia_codigo(client):
    r = _registrar(client)
    assert r.status_code == 201
    dados = r.get_json()['data']
    assert dados['usuario']['email_verificado'] is False and dados['verificacao_enviada'] is True
    msg = email_service.caixa_de_saida[-1]
    assert msg['To'] == 'ana@x.com' and 'Confirme seu e-mail' in msg['Subject']
    html = msg.get_body(('html',)).get_content()
    assert 'SuaFacul' in html and '#5a189a' in html  # identidade visual
    assert re.fullmatch(r'\d{5}', _ultimo_codigo())


def test_codigo_nunca_e_guardado_em_texto(app, client):
    _registrar(client)
    codigo = _ultimo_codigo()
    from config.database import get_connection
    conn = get_connection()
    linhas = [dict(r) for r in conn.execute('SELECT * FROM codigos_email')]
    conn.close()
    assert linhas and all(codigo not in str(v) for linha in linhas for v in linha.values())


def test_cadastro_email_duplicado_sem_diferenciar_maiusculas(client):
    _registrar(client)
    _erro(_registrar(client, nome='outra', email='  ANA@X.com '), 409, 'CONFLICT')


def test_cadastro_exige_email_valido_e_senha_forte(client):
    _erro(_registrar(client, email='sem-arroba'), 422, 'VALIDATION_ERROR')
    _erro(_registrar(client, senha='curta1'), 422, 'VALIDATION_ERROR')
    _erro(_registrar(client, senha='somenteletras'), 422, 'VALIDATION_ERROR')


def test_conta_nao_verificada_pode_entrar_e_confirma_com_codigo(client):
    _registrar(client)
    codigo = _ultimo_codigo()
    login = client.post('/api/v1/auth/login', json={'email': 'ana@x.com', 'password': SENHA})
    assert login.status_code == 200 and login.get_json()['data']['usuario']['email_verificado'] is False
    _erro(client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': '00000' if codigo != '00000' else '11111'}),
          422, 'INVALID_CODE')
    r = client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': codigo})
    assert r.status_code == 200 and r.get_json()['data']['usuario']['email_verificado'] is True
    # uso único: o mesmo código não vale de novo
    _erro(client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': codigo}), 422, 'INVALID_CODE')


def test_codigo_expirado(client, monkeypatch):
    _registrar(client)
    codigo = _ultimo_codigo()
    _deslocar_relogio(monkeypatch, codigo_service.VALIDADE_MINUTOS['verificacao'] + 1)
    _erro(client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': codigo}), 422, 'CODE_EXPIRED')


def test_cinco_erros_invalidam_o_codigo(client):
    _registrar(client)
    codigo = _ultimo_codigo()
    errado = '99999' if codigo != '99999' else '88888'
    for _ in range(codigo_service.MAX_TENTATIVAS - 1):
        _erro(client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': errado}), 422, 'INVALID_CODE')
    _erro(client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': errado}), 429, 'TOO_MANY_ATTEMPTS')
    _erro(client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': codigo}), 422, 'INVALID_CODE')


def test_reenvio_respeita_intervalo_e_invalida_o_codigo_anterior(client, monkeypatch):
    _registrar(client)
    primeiro = _ultimo_codigo()
    enviados = len(email_service.caixa_de_saida)
    # pedir de novo logo em seguida: resposta genérica, mas nenhum e-mail novo
    r = client.post('/api/v1/auth/verificacao/enviar', json={'email': 'ana@x.com'})
    nao_existe = client.post('/api/v1/auth/verificacao/enviar', json={'email': 'ninguem@x.com'})
    assert r.status_code == nao_existe.status_code == 202  # não revela a conta pelo 429
    assert r.get_json() == nao_existe.get_json()
    assert len(email_service.caixa_de_saida) == enviados
    _deslocar_relogio(monkeypatch, 2)
    assert client.post('/api/v1/auth/verificacao/enviar', json={'email': 'ana@x.com'}).status_code == 202
    segundo = _ultimo_codigo()
    if primeiro != segundo:
        _erro(client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': primeiro}), 422, 'INVALID_CODE')
    assert client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': segundo}).status_code == 200


def test_pedidos_de_codigo_nao_revelam_se_o_email_existe(client):
    _registrar(client)
    existe = client.post('/api/v1/auth/recuperacao/solicitar', json={'email': 'ana@x.com'})
    nao_existe = client.post('/api/v1/auth/recuperacao/solicitar', json={'email': 'ninguem@x.com'})
    assert existe.status_code == nao_existe.status_code == 202
    assert existe.get_json() == nao_existe.get_json()
    assert all(m['To'] != 'ninguem@x.com' for m in email_service.caixa_de_saida)
    # confirmar código de conta inexistente: o mesmo erro de um código errado
    _erro(client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ninguem@x.com', 'codigo': '12345'}), 422, 'INVALID_CODE')


# ── Login ───────────────────────────────────────────────────────────────

def test_login_bloqueia_apos_muitas_senhas_erradas_e_libera_depois(client, monkeypatch):
    _registrar(client)
    for _ in range(limite_service.LIMITES['login_conta'][0]):
        _erro(client.post('/api/v1/auth/login', json={'email': 'ana@x.com', 'password': 'errada123'}), 401, 'INVALID_CREDENTIALS')
    r = client.post('/api/v1/auth/login', json={'email': 'ana@x.com', 'password': SENHA})  # até a certa espera
    _erro(r, 429, 'RATE_LIMITED')
    assert int(r.headers['Retry-After']) > 0
    _deslocar_relogio(monkeypatch, limite_service.LIMITES['login_conta'][1] + 1)
    assert client.post('/api/v1/auth/login', json={'email': 'ana@x.com', 'password': SENHA}).status_code == 200


def test_bloqueio_igual_para_conta_inexistente(client):
    for _ in range(limite_service.LIMITES['login_conta'][0]):
        client.post('/api/v1/auth/login', json={'email': 'fantasma@x.com', 'password': 'qualquer1'})
    _erro(client.post('/api/v1/auth/login', json={'email': 'fantasma@x.com', 'password': 'qualquer1'}), 429, 'RATE_LIMITED')


def test_login_do_site_tambem_e_limitado(client):
    client.post('/api/usuario/registrar', data={'username': 'bia', 'email': 'bia@x.com', 'password': SENHA})
    for _ in range(limite_service.LIMITES['login_conta'][0]):
        assert client.post('/api/usuario/login', data={'username': 'bia@x.com', 'password': 'errada123'}).get_json()['success'] is False
    r = client.post('/api/usuario/login', data={'username': 'bia@x.com', 'password': SENHA})
    assert r.status_code == 429 and r.get_json()['success'] is False


# ── Recuperação de senha ────────────────────────────────────────────────

def _recuperar(client, email='ana@x.com'):
    assert client.post('/api/v1/auth/recuperacao/solicitar', json={'email': email}).status_code == 202
    return _ultimo_codigo(email)


def test_recuperacao_completa_encerra_todas_as_sessoes(app, client):
    tokens = _registrar(client).get_json()['data']['tokens']
    web = app.app.test_client()
    assert web.post('/api/usuario/login', data={'username': 'ana', 'password': SENHA}).get_json()['success']
    assert web.get('/dashboard').status_code == 200

    codigo = _recuperar(client)
    assert client.post('/api/v1/auth/recuperacao/validar', json={'email': 'ana@x.com', 'codigo': codigo}).status_code == 200
    _erro(client.post('/api/v1/auth/recuperacao/redefinir', json={'email': 'ana@x.com', 'codigo': codigo,
                                                                 'password': 'novaSenha9', 'password_confirm': 'outra'}),
          422, 'VALIDATION_ERROR')
    r = client.post('/api/v1/auth/recuperacao/redefinir', json={'email': 'ana@x.com', 'codigo': codigo,
                                                               'password': 'novaSenha9', 'password_confirm': 'novaSenha9'})
    assert r.status_code == 200

    # app: access e refresh antigos não valem mais; site: a sessão aberta caiu
    _erro(client.get('/api/v1/me', headers={'Authorization': 'Bearer ' + tokens['access_token']}), 401, 'INVALID_TOKEN')
    _erro(client.post('/api/v1/auth/refresh', json={'refresh_token': tokens['refresh_token']}), 401, 'INVALID_REFRESH_TOKEN')
    assert web.get('/dashboard').status_code == 302
    # código de uso único; senha antiga não entra; nova entra; e-mail ficou verificado
    _erro(client.post('/api/v1/auth/recuperacao/redefinir', json={'email': 'ana@x.com', 'codigo': codigo,
                                                                 'password': 'outraSenha9', 'password_confirm': 'outraSenha9'}),
          422, 'INVALID_CODE')
    _erro(client.post('/api/v1/auth/login', json={'email': 'ana@x.com', 'password': SENHA}), 401, 'INVALID_CREDENTIALS')
    login = client.post('/api/v1/auth/login', json={'email': 'ana@x.com', 'password': 'novaSenha9'})
    assert login.status_code == 200 and login.get_json()['data']['usuario']['email_verificado'] is True


def test_recuperacao_com_codigo_expirado(client, monkeypatch):
    _registrar(client)
    codigo = _recuperar(client)
    _deslocar_relogio(monkeypatch, codigo_service.VALIDADE_MINUTOS['recuperacao'] + 1)
    _erro(client.post('/api/v1/auth/recuperacao/redefinir', json={'email': 'ana@x.com', 'codigo': codigo,
                                                                 'password': 'novaSenha9', 'password_confirm': 'novaSenha9'}),
          422, 'CODE_EXPIRED')


def test_pedidos_de_recuperacao_sao_limitados(client, monkeypatch):
    _registrar(client)
    maximo = limite_service.LIMITES['recuperacao_conta'][0]
    for i in range(maximo):
        _deslocar_relogio(monkeypatch, 2 * (i + 1))  # passa o intervalo mínimo entre envios
        assert client.post('/api/v1/auth/recuperacao/solicitar', json={'email': 'ana@x.com'}).status_code == 202
    _erro(client.post('/api/v1/auth/recuperacao/solicitar', json={'email': 'ana@x.com'}), 429, 'RATE_LIMITED')


def test_nenhum_codigo_ou_senha_nos_logs(client, caplog):
    caplog.set_level(logging.DEBUG)
    _registrar(client)
    codigo = _recuperar(client)
    client.post('/api/v1/auth/recuperacao/redefinir', json={'email': 'ana@x.com', 'codigo': codigo,
                                                           'password': 'novaSenha9', 'password_confirm': 'novaSenha9'})
    texto = caplog.text
    assert codigo not in texto and SENHA not in texto and 'novaSenha9' not in texto


# ── Troca de senha e de e-mail logado ───────────────────────────────────

def test_trocar_email_exige_senha_atual_e_confirmacao_no_novo_endereco(client):
    tokens = _registrar(client).get_json()['data']['tokens']
    h = {'Authorization': 'Bearer ' + tokens['access_token']}
    _registrar(client, nome='bia', email='bia@x.com')
    _erro(client.post('/api/v1/me/email', json={'email': 'nova@x.com', 'password_atual': 'errada123'}, headers=h),
          422, 'INVALID_CURRENT_PASSWORD')
    _erro(client.post('/api/v1/me/email', json={'email': 'BIA@x.com', 'password_atual': SENHA}, headers=h), 409, 'CONFLICT')
    assert client.post('/api/v1/me/email', json={'email': 'nova@x.com', 'password_atual': SENHA}, headers=h).status_code == 202
    assert client.get('/api/v1/me', headers=h).get_json()['data']['email'] == 'ana@x.com'  # ainda não mudou
    r = client.post('/api/v1/me/email/confirmar', json={'codigo': _ultimo_codigo('nova@x.com')}, headers=h)
    assert r.status_code == 200 and r.get_json()['data']['email'] == 'nova@x.com'
    assert r.get_json()['data']['email_verificado'] is True


def test_web_troca_propria_senha_e_continua_logado_mas_outras_sessoes_caem(app, client):
    client.post('/api/usuario/registrar', data={'username': 'caio', 'email': 'caio@x.com', 'password': SENHA})
    outro = app.app.test_client()
    for c in (client, outro):
        assert c.post('/api/usuario/login', data={'username': 'caio', 'password': SENHA}).get_json()['success']
    r = client.post('/api/usuario/perfil', data={'username': 'caio', 'email': 'caio@x.com', 'password_atual': SENHA,
                                                 'password': 'novaSenha9', 'password_confirm': 'novaSenha9'})
    assert r.get_json()['success'] is True
    assert client.get('/dashboard').status_code == 200   # quem trocou continua
    assert outro.get('/dashboard').status_code == 302    # o outro navegador foi deslogado


# ── Google: vinculação segura ───────────────────────────────────────────

CHAVE = RSAKey.generate_key(2048, parameters={'kid': 'g1'})


@pytest.fixture()
def google(monkeypatch):
    from app.services import google_service
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'web.apps.googleusercontent.com')
    monkeypatch.setattr(google_service, '_chaves_do_google',
                        lambda: KeySet.import_key_set({'keys': [CHAVE.as_dict(private=False)]}))

    def token(email='ana@x.com', sub='g-ana', verificado=True):
        agora = int(time.time())
        return jwt.encode({'alg': 'RS256', 'kid': 'g1'}, {
            'iss': 'https://accounts.google.com', 'aud': 'web.apps.googleusercontent.com', 'sub': sub,
            'email': email, 'email_verified': verificado, 'iat': agora, 'exp': agora + 600}, CHAVE)
    return token


def test_google_assume_conta_local_nao_verificada_e_invalida_a_senha_antiga(client, google):
    """Alguém cadastrou o e-mail de outra pessoa sem verificar; a dona entra com Google:
    a conta passa a ser dela e a senha de quem cadastrou deixa de funcionar."""
    tokens_intruso = _registrar(client).get_json()['data']['tokens']
    r = client.post('/api/v1/auth/google', json={'id_token': google()})
    assert r.status_code == 200
    usuario = r.get_json()['data']['usuario']
    assert usuario['email_verificado'] is True and usuario['senha_definida'] is False
    _erro(client.post('/api/v1/auth/login', json={'email': 'ana@x.com', 'password': SENHA}), 401, 'INVALID_CREDENTIALS')
    _erro(client.post('/api/v1/auth/refresh', json={'refresh_token': tokens_intruso['refresh_token']}), 401, 'INVALID_REFRESH_TOKEN')


def test_google_vincula_conta_verificada_sem_mexer_na_senha(client, google):
    _registrar(client)
    client.post('/api/v1/auth/verificacao/confirmar', json={'email': 'ana@x.com', 'codigo': _ultimo_codigo()})
    id_local = client.post('/api/v1/auth/login', json={'email': 'ana@x.com', 'password': SENHA}).get_json()['data']['usuario']['id']
    r = client.post('/api/v1/auth/google', json={'id_token': google()})
    assert r.get_json()['data']['usuario']['id'] == id_local  # a mesma conta, sem duplicar
    assert client.post('/api/v1/auth/login', json={'email': 'ana@x.com', 'password': SENHA}).status_code == 200
    # conta já vinculada: entra direto pelo google_id
    assert client.post('/api/v1/auth/google', json={'id_token': google()}).get_json()['data']['usuario']['id'] == id_local


def test_google_sem_email_verificado_nao_cria_nem_vincula(app, client, google):
    _erro(client.post('/api/v1/auth/google', json={'id_token': google(email='novo@x.com', sub='g-novo', verificado=False)}),
          403, 'EMAIL_NOT_VERIFIED')
    assert app.Usuario().buscar_por_email('novo@x.com') is None


def test_conta_criada_pelo_google_define_primeira_senha_sem_a_atual(client, google):
    tokens = client.post('/api/v1/auth/google', json={'id_token': google(email='g@x.com', sub='g-1')}).get_json()['data']['tokens']
    h = {'Authorization': 'Bearer ' + tokens['access_token']}
    r = client.patch('/api/v1/me', json={'password': 'primeira9', 'password_confirm': 'primeira9'}, headers=h)
    assert r.status_code == 200 and r.get_json()['data']['senha_definida'] is True
    # a partir daí, a senha atual passa a ser exigida
    _erro(client.patch('/api/v1/me', json={'password': 'segunda99', 'password_confirm': 'segunda99'}, headers=h),
          422, 'INVALID_CURRENT_PASSWORD')


# ── Contas antigas ──────────────────────────────────────────────────────

def test_migracao_preserva_contas_antigas(app, tmp_path, monkeypatch):
    """Banco no formato anterior (sem as colunas novas): ninguém é apagado; locais ficam
    não verificadas (e continuam entrando), Google fica verificada."""
    from werkzeug.security import generate_password_hash
    db = tmp_path / 'antigo.db'
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_usuario TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE, senha TEXT NOT NULL, tipo TEXT NOT NULL DEFAULT 'aluno',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            google_id TEXT, auth_provider TEXT NOT NULL DEFAULT 'local', avatar_url TEXT);
    """)
    conn.execute("INSERT INTO usuarios (nome_usuario, email, senha) VALUES ('velho', 'velho@x.com', ?)",
                 (generate_password_hash('curta1'),))
    conn.execute("INSERT INTO usuarios (nome_usuario, email, senha, google_id, auth_provider) VALUES "
                 "('gente', 'gente@gmail.com', 'x', 'g-9', 'google')")
    conn.commit()
    conn.close()
    monkeypatch.setenv('SUAFACUL_DB_PATH', str(db))
    import importlib

    import database.init_db as init_db
    importlib.reload(init_db).init_db()
    conn = sqlite3.connect(db)
    linhas = dict(conn.execute("SELECT nome_usuario, email_verificado || '/' || senha_definida FROM usuarios "
                               "WHERE nome_usuario IN ('velho', 'gente')").fetchall())
    conn.close()
    assert linhas == {'velho': '0/1', 'gente': '1/0'}
    # senha antiga (fora da política nova) continua entrando
    from app.services import usuario_service
    assert usuario_service.autenticar_por_email('velho@x.com', 'curta1')['nome_usuario'] == 'velho'


def test_paginas_de_conta_do_site(client):
    for caminho in ('/verificar-email', '/recuperar-senha'):
        r = client.get(caminho)
        assert r.status_code == 200 and b'conta.js' in r.data
    assert b'href="/recuperar-senha"' in client.get('/login').data
