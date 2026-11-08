"""Autenticação das rotas da API v1: somente `Authorization: Bearer <access_token>`.

O cookie de sessão do site NÃO autentica a API (elimina o CSRF por cookie). A
sessão do token é conferida no banco a cada requisição: logout, reuso de
refresh token, troca de senha e exclusão de conta valem imediatamente.
"""
from functools import wraps

from flask import g, request

from app.models.usuario import Usuario
from app.services import token_service
from app.services.erros import NaoAutenticadoError, PermissaoNegadaError


def _token_bearer():
    """Access token do cabeçalho Authorization, ou None se não veio nenhum."""
    cabecalho = request.headers.get('Authorization', '').strip()
    if not cabecalho:
        return None
    esquema, _, token = cabecalho.partition(' ')
    if esquema.lower() != 'bearer' or not token.strip():
        raise NaoAutenticadoError('Use o cabeçalho "Authorization: Bearer <access_token>".',
                                  code='INVALID_TOKEN')
    return token.strip()


def usuario_atual(obrigatorio=True):
    """Usuário autenticado (dict do banco).

    Sem cabeçalho: None (ou 401 se `obrigatorio`). Com cabeçalho inválido,
    expirado ou de sessão revogada: sempre 401 — o cliente precisa saber que
    deve renovar o token, mesmo em rotas onde a autenticação é opcional.
    """
    token = _token_bearer()
    if token is None:
        if obrigatorio:
            raise NaoAutenticadoError('Autenticação necessária.')
        return None
    dados = token_service.validar_access_token(token)
    usuario = Usuario().buscar_por_id(dados['uid'])
    if usuario is None:
        raise NaoAutenticadoError('Access token inválido.', code='INVALID_TOKEN')
    g.familia_id = dados['fam']
    return usuario


def requer_usuario(view):
    @wraps(view)
    def envolvido(*args, **kwargs):
        g.usuario = usuario_atual()
        return view(*args, **kwargs)
    return envolvido


def requer_admin(view):
    """Bearer válido E conta de administrador. O papel vem do banco a cada
    requisição (usuario_atual), nunca do token: rebaixar um admin vale na hora."""
    @wraps(view)
    def envolvido(*args, **kwargs):
        g.usuario = usuario_atual()
        if g.usuario.get('tipo') != 'admin':
            raise PermissaoNegadaError('Acesso restrito a administradores.')
        return view(*args, **kwargs)
    return envolvido
