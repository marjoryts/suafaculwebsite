"""Cadastro, login (e-mail + senha ou Google), renovação e logout do app Mobile.

Cada rota só valida o formato do corpo e delega: usuario_service / google_service
(identidade) e token_service (sessão/tokens) — a sessão é a mesma nos dois logins.
"""
from flask import jsonify, request

from app.api.v1 import bp
from app.api.v1.http import campo_texto, corpo_json
from app.api.v1.serializers import usuario_dto
from app.models.usuario import Usuario
from app.services import google_service, token_service, usuario_service


def _dispositivo():
    return request.headers.get('User-Agent', '')[:200] or None


def _sessao(usuario_id):
    return {'usuario': usuario_dto(Usuario().buscar_por_id(usuario_id)),
            'tokens': token_service.iniciar_sessao(usuario_id, _dispositivo())}


@bp.post('/auth/registrar')
def auth_registrar():
    """Cria a conta (aluno) e já abre uma sessão."""
    dados = corpo_json()
    email = campo_texto(dados, 'email')
    resultado = usuario_service.registrar(campo_texto(dados, 'nome_usuario'), email,
                                          campo_texto(dados, 'password'))
    if not resultado.get('success'):
        raise RuntimeError(resultado.get('message', 'Falha ao criar conta.'))  # infra: vira 500 genérico
    usuario = Usuario().buscar_por_email(email.strip())
    return jsonify({'data': _sessao(usuario['id'])}), 201


@bp.post('/auth/login')
def auth_login():
    dados = corpo_json()
    usuario = usuario_service.autenticar_por_email(campo_texto(dados, 'email'), campo_texto(dados, 'password'))
    return jsonify({'data': _sessao(usuario['id'])})


@bp.post('/auth/google')
def auth_google():
    """Corpo: {"id_token": "<ID token do Google Sign-In>"}. O servidor valida
    assinatura, emissor, audiência e validade; depois aplica a mesma regra de
    conta do site (vincula por e-mail verificado ou cria) e abre uma sessão."""
    claims = google_service.validar_id_token(campo_texto(corpo_json(), 'id_token'))
    usuario = google_service.entrar_com_claims(claims)
    return jsonify({'data': _sessao(usuario['id'])})


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
