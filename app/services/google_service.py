"""Login com Google: validação do ID token (OpenID Connect) e a regra de conta,
compartilhadas pelo site (callback do Authlib, app/routes/auth_google.py) e pelo
app (POST /api/v1/auth/google).

O cliente nunca é confiável: o app envia só o `id_token` emitido pelo Google e
o servidor confere assinatura (chaves públicas do Google), emissor, audiência
(os client IDs do projeto) e validade antes de usar qualquer dado dele.

Variáveis de ambiente (audiências aceitas):
    GOOGLE_CLIENT_ID           cliente Web (site; também é a audiência do token
                               pedido pelo app com o Google Sign-In nativo)
    GOOGLE_ANDROID_CLIENT_ID   opcional (vírgulas para vários)
    GOOGLE_IOS_CLIENT_ID       opcional
"""
import os
import time

import requests
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet

from app.models.usuario import Usuario
from app.services.erros import ErroDeNegocio, NaoAutenticadoError, PermissaoNegadaError

JWKS_URL = 'https://www.googleapis.com/oauth2/v3/certs'
EMISSORES = ('accounts.google.com', 'https://accounts.google.com')
TOLERANCIA_RELOGIO = 60  # segundos de diferença aceitos entre os relógios
CACHE_CHAVES_SEGUNDOS = 3600

_cache = {'chaves': None, 'ate': 0.0}


class GoogleNaoConfiguradoError(ErroDeNegocio):
    status = 503
    code = 'GOOGLE_NOT_CONFIGURED'


def audiencias_permitidas():
    ids = []
    for var in ('GOOGLE_CLIENT_ID', 'GOOGLE_ANDROID_CLIENT_ID', 'GOOGLE_IOS_CLIENT_ID'):
        ids += [i.strip() for i in os.environ.get(var, '').split(',') if i.strip()]
    return ids


def _chaves_do_google():
    """Chaves públicas do Google (JWKS), em cache por uma hora."""
    agora = time.time()
    if _cache['chaves'] is None or agora >= _cache['ate']:
        resposta = requests.get(JWKS_URL, timeout=10)
        resposta.raise_for_status()
        _cache['chaves'] = KeySet.import_key_set(resposta.json())
        _cache['ate'] = agora + CACHE_CHAVES_SEGUNDOS
    return _cache['chaves']


def _invalido(msg='Token do Google inválido.'):
    return NaoAutenticadoError(msg, code='INVALID_GOOGLE_TOKEN')


def validar_id_token(id_token):
    """Claims do ID token, só se ele for do Google, para este projeto e válido."""
    audiencias = audiencias_permitidas()
    if not audiencias:
        raise GoogleNaoConfiguradoError('Login com Google não está configurado no servidor.')
    if not isinstance(id_token, str) or id_token.count('.') != 2:
        raise _invalido()
    try:
        token = jwt.decode(id_token, _chaves_do_google(), algorithms=['RS256'])
    except JoseError:
        raise _invalido()  # assinatura inválida, chave desconhecida, token malformado
    claims = token.claims
    aud = claims.get('aud')
    aud = aud if isinstance(aud, list) else [aud]
    agora = time.time()
    if claims.get('iss') not in EMISSORES:
        raise _invalido()
    if not any(a in audiencias for a in aud):
        raise _invalido('Token do Google emitido para outro aplicativo.')
    if not isinstance(claims.get('exp'), (int, float)) or claims['exp'] < agora - TOLERANCIA_RELOGIO:
        raise NaoAutenticadoError('Token do Google expirado. Entre novamente.', code='INVALID_GOOGLE_TOKEN')
    if isinstance(claims.get('iat'), (int, float)) and claims['iat'] > agora + TOLERANCIA_RELOGIO:
        raise _invalido()
    if not claims.get('sub') or not claims.get('email'):
        raise _invalido('O Google não informou um e-mail utilizável.')
    return claims


def entrar_com_claims(claims):
    """Conta para os dados (já validados) do Google — a mesma regra no site e no app:

    1) já existe conta com esse google_id -> essa conta;
    2) existe conta local com o e-mail -> vincula, SÓ se o Google confirmar que o
       e-mail é verificado (impede sequestrar uma conta com e-mail não confirmado);
    3) senão -> cria uma conta 'aluno'.
    """
    google_id = claims.get('sub')
    email = (claims.get('email') or '').strip().lower()
    if not google_id or not email:
        raise _invalido('O Google não informou um e-mail utilizável.')
    nome = claims.get('name') or email.split('@')[0]
    avatar_url = claims.get('picture')
    usuarios = Usuario()

    usuario = usuarios.buscar_por_google_id(google_id)
    if usuario:
        return usuario

    existente = usuarios.buscar_por_email(email)
    if existente:
        if claims.get('email_verified') is not True:
            raise PermissaoNegadaError('Seu e-mail ainda não foi verificado pelo Google.', code='EMAIL_NOT_VERIFIED')
        resultado = usuarios.vincular_google(existente['id'], google_id, avatar_url)
    else:
        resultado = usuarios.criar_via_google(google_id, email, nome, avatar_url)
    if not resultado.get('success'):
        raise RuntimeError(resultado.get('message') or 'Falha ao entrar com Google.')  # infra: 500
    return resultado['user']
