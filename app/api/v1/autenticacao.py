"""Cadastro, login (e-mail + senha ou Google), renovação e logout do app Mobile.

Cada rota só valida o formato do corpo e delega: usuario_service / google_service
(identidade) e token_service (sessão/tokens) — a sessão é a mesma nos dois logins.
"""
from flask import jsonify, request

from app.api.v1 import bp
from app.api.v1.http import campo_texto, corpo_json
from app.api.v1.serializers import usuario_dto
from app.rede import ip_cliente
from app.models.usuario import Usuario
from app.services import conta_service, google_service, limite_service, token_service, usuario_service


def _dispositivo():
    return request.headers.get('User-Agent', '')[:200] or None


def _sessao(usuario_id):
    return {'usuario': usuario_dto(Usuario().buscar_por_id(usuario_id)),
            'tokens': token_service.iniciar_sessao(usuario_id, _dispositivo())}


@bp.post('/auth/registrar')
def auth_registrar():
    """Cria a conta (aluno, e-mail ainda não verificado), envia o código de
    verificação e já abre uma sessão. `verificacao_enviada` diz se o e-mail saiu."""
    dados = corpo_json()
    email = campo_texto(dados, 'email')
    resultado = usuario_service.registrar(campo_texto(dados, 'nome_usuario'), email,
                                          campo_texto(dados, 'password'), ip=ip_cliente())
    if not resultado.get('success'):
        raise RuntimeError(resultado.get('message', 'Falha ao criar conta.'))  # infra: vira 500 genérico
    usuario = Usuario().buscar_por_email(email)
    return jsonify({'data': {**_sessao(usuario['id']),
                             'verificacao_enviada': bool(resultado.get('verificacao_enviada'))}}), 201


@bp.post('/auth/login')
def auth_login():
    dados = corpo_json()
    usuario = usuario_service.autenticar_por_email(campo_texto(dados, 'email'), campo_texto(dados, 'password'),
                                                   ip=ip_cliente())
    return jsonify({'data': _sessao(usuario['id'])})


@bp.post('/auth/google')
def auth_google():
    """Corpo: {"id_token": "<ID token do Google Sign-In>"}. O servidor valida
    assinatura, emissor, audiência e validade; depois aplica a mesma regra de
    conta do site (vincula por e-mail verificado ou cria) e abre uma sessão."""
    limite_service.consumir('google_ip', ip_cliente())
    claims = google_service.validar_id_token(campo_texto(corpo_json(), 'id_token'))
    usuario = google_service.entrar_com_claims(claims)
    return jsonify({'data': _sessao(usuario['id'])})


# ── Verificação de e-mail e recuperação de senha (públicas, sem sessão) ──
# Os pedidos respondem sempre a mesma coisa (não revelam se o e-mail existe).

@bp.post('/auth/verificacao/enviar')
def auth_verificacao_enviar():
    """Corpo: {"email"}. (Re)envia o código de verificação, se a conta existir e não
    estiver verificada. Resposta genérica (202)."""
    conta_service.solicitar_verificacao(campo_texto(corpo_json(), 'email'), ip=ip_cliente())
    return jsonify({'data': {'mensagem': conta_service.MENSAGEM_ENVIO_GENERICA}}), 202


@bp.post('/auth/verificacao/confirmar')
def auth_verificacao_confirmar():
    """Corpo: {"email", "codigo"}. Confirma o e-mail. Erros: INVALID_CODE, CODE_EXPIRED
    (422) e TOO_MANY_ATTEMPTS (429)."""
    dados = corpo_json()
    usuario = conta_service.confirmar_verificacao(campo_texto(dados, 'email'), campo_texto(dados, 'codigo'),
                                                  ip=ip_cliente())
    return jsonify({'data': {'usuario': usuario_dto(usuario)}})


@bp.post('/auth/recuperacao/solicitar')
def auth_recuperacao_solicitar():
    """Corpo: {"email"}. Envia o código de recuperação, se a conta existir. Resposta genérica (202)."""
    conta_service.solicitar_recuperacao(campo_texto(corpo_json(), 'email'), ip=ip_cliente())
    return jsonify({'data': {'mensagem': conta_service.MENSAGEM_ENVIO_GENERICA}}), 202


@bp.post('/auth/recuperacao/validar')
def auth_recuperacao_validar():
    """Corpo: {"email", "codigo"}. Confere o código sem consumi-lo (libera a tela da nova senha)."""
    dados = corpo_json()
    conta_service.validar_recuperacao(campo_texto(dados, 'email'), campo_texto(dados, 'codigo'), ip=ip_cliente())
    return jsonify({'data': {'valido': True}})


@bp.post('/auth/recuperacao/redefinir')
def auth_recuperacao_redefinir():
    """Corpo: {"email", "codigo", "password", "password_confirm"}. Nova senha; o código
    é consumido e TODAS as sessões da conta são encerradas (app e site)."""
    dados = corpo_json()
    conta_service.redefinir_senha(campo_texto(dados, 'email'), campo_texto(dados, 'codigo'),
                                  campo_texto(dados, 'password'), campo_texto(dados, 'password_confirm'),
                                  ip=ip_cliente())
    return jsonify({'data': {'mensagem': 'Senha redefinida. Entre com a nova senha.'}})


@bp.post('/auth/refresh')
def auth_refresh():
    """Troca o refresh token (uso único) por um novo par de tokens."""
    tokens = token_service.renovar(campo_texto(corpo_json(), 'refresh_token'), _dispositivo())
    return jsonify({'data': {'tokens': tokens}})


@bp.post('/auth/logout')
def auth_logout():
    """Encerra a sessão do refresh token informado (idempotente)."""
    token_service.encerrar_sessao(campo_texto(corpo_json(), 'refresh_token'))
    return '', 204
