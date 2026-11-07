"""Favoritos do usuário autenticado (curso, faculdade, vestibular)."""
from flask import g, jsonify

from app.api.v1 import bp
from app.api.v1.auth import requer_usuario
from app.api.v1.http import texto_arg
from app.api.v1.serializers import favorito_dto
from app.services import favorito_service


@bp.get('/favoritos')
@requer_usuario
def favoritos_listar():
    """Filtro opcional: ?tipo=curso|faculdade|vestibular."""
    tipo = texto_arg('tipo') or None
    if tipo:
        favorito_service.validar_tipo(tipo)
    itens = favorito_service.listar_com_itens(g.usuario['id'], tipo)
    return jsonify({'data': [favorito_dto(f) for f in itens], 'meta': {'total': len(itens)}})


@bp.put('/favoritos/<tipo>/<int:item_id>')
@requer_usuario
def favoritos_adicionar(tipo, item_id):
    """Idempotente: 201 se criou, 200 se já era favorito. 404 se o item não existe."""
    favorito, criado = favorito_service.favoritar(g.usuario['id'], tipo, item_id)
    return jsonify({'data': favorito_dto(favorito)}), (201 if criado else 200)


@bp.delete('/favoritos/<tipo>/<int:item_id>')
@requer_usuario
def favoritos_remover(tipo, item_id):
    """Idempotente: 204 mesmo que o item não estivesse nos favoritos."""
    favorito_service.desfavoritar(g.usuario['id'], tipo, item_id)
    return '', 204
