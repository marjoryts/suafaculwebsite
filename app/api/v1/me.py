"""Perfil e dashboard do usuário autenticado."""
from flask import g, jsonify

from app.api.v1 import bp
from app.api.v1.auth import requer_usuario
from app.api.v1.http import campo_texto, corpo_json
from app.api.v1.serializers import dashboard_dto, usuario_dto
from app.models.usuario import Usuario
from app.rede import ip_cliente
from app.services import conta_service, dashboard_service, usuario_service
from app.services.erros import ValidacaoError

# Somente estes campos podem ser alterados pelo próprio usuário. O tipo de
# acesso (aluno/admin) NUNCA é editável por aqui.
CAMPOS_EDITAVEIS = {'nome_usuario', 'email', 'password', 'password_confirm', 'password_atual'}


@bp.get('/me')
@requer_usuario
def me():
    return jsonify({'data': usuario_dto(g.usuario)})


@bp.patch('/me')
@requer_usuario
def me_atualizar():
    """Corpo (todos opcionais): nome_usuario; password + password_confirm + password_atual
    (a senha atual é obrigatória, exceto em contas sem senha própria). O e-mail não muda
    aqui: use POST /me/email (confirmação por código no novo endereço)."""
    dados = corpo_json()
    extras = sorted(set(dados) - CAMPOS_EDITAVEIS)
    if extras:
        raise ValidacaoError('Campos não permitidos.', details={'campos': extras})
    if not dados:
        raise ValidacaoError('Informe ao menos um campo para atualizar.')

    atual = g.usuario
    resultado = usuario_service.atualizar_perfil(
        atual['id'],
        campo_texto(dados, 'nome_usuario') if 'nome_usuario' in dados else atual['nome_usuario'],
        campo_texto(dados, 'email') if 'email' in dados else atual['email'],
        campo_texto(dados, 'password'),
        campo_texto(dados, 'password_confirm'),
        manter_sessao_api=g.familia_id,  # trocar a senha encerra as OUTRAS sessões do app
        senha_atual=campo_texto(dados, 'password_atual'),
    )
    if not resultado.get('success'):
        # Falha de infraestrutura (não de validação): vira 500 genérico, sem vazar detalhe.
        raise RuntimeError(resultado.get('message', 'Falha ao atualizar perfil.'))

    atualizado = Usuario().buscar_por_id(atual['id'])
    return jsonify({'data': usuario_dto(atualizado)})


@bp.post('/me/email')
@requer_usuario
def me_trocar_email():
    """Corpo: {"email", "password_atual"}. Envia um código ao NOVO endereço; o e-mail
    só muda após POST /me/email/confirmar."""
    dados = corpo_json()
    conta_service.solicitar_troca_email(g.usuario['id'], campo_texto(dados, 'email'), campo_texto(dados, 'password_atual'))
    return jsonify({'data': {'mensagem': 'Enviamos um código para o novo e-mail.'}}), 202


@bp.post('/me/email/confirmar')
@requer_usuario
def me_confirmar_email():
    """Corpo: {"codigo"}. Confirma a troca de e-mail (o novo já fica verificado)."""
    usuario = conta_service.confirmar_troca_email(g.usuario['id'], campo_texto(corpo_json(), 'codigo'),
                                                  ip=ip_cliente())
    return jsonify({'data': usuario_dto(usuario)})


@bp.get('/me/dashboard')
@requer_usuario
def me_dashboard():
    return jsonify({'data': dashboard_dto(dashboard_service.resumo(g.usuario['id']))})
