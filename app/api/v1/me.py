"""Perfil e dashboard do usuário autenticado."""
from flask import g, jsonify

from app.api.v1 import bp
from app.api.v1.auth import requer_usuario
from app.api.v1.http import campo_texto, corpo_json
from app.api.v1.serializers import dashboard_dto, usuario_dto
from app.models.usuario import Usuario
from app.services import dashboard_service, usuario_service
from app.services.erros import ValidacaoError

# Somente estes campos podem ser alterados pelo próprio usuário. O tipo de
# acesso (aluno/admin) NUNCA é editável por aqui.
CAMPOS_EDITAVEIS = {'nome_usuario', 'email', 'password', 'password_confirm'}


@bp.get('/me')
@requer_usuario
def me():
    return jsonify({'data': usuario_dto(g.usuario)})


@bp.patch('/me')
@requer_usuario
def me_atualizar():
    """Corpo (todos opcionais): nome_usuario, email, password + password_confirm."""
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
    )
    if not resultado.get('success'):
        # Falha de infraestrutura (não de validação): vira 500 genérico, sem vazar detalhe.
        raise RuntimeError(resultado.get('message', 'Falha ao atualizar perfil.'))

    atualizado = Usuario().buscar_por_id(atual['id'])
    return jsonify({'data': usuario_dto(atualizado)})


@bp.get('/me/dashboard')
@requer_usuario
def me_dashboard():
    return jsonify({'data': dashboard_dto(dashboard_service.resumo(g.usuario['id']))})
