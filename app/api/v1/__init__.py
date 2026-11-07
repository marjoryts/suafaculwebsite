"""API v1 — contrato oficial do aplicativo Mobile (e de consumidores externos).

Catálogo, busca, teste vocacional, favoritos, perfil, dashboard e o painel
administrativo (/admin/*, só para contas admin — o papel é conferido no banco
a cada requisição). Regras de negócio ficam em app/services; aqui só há HTTP.

Convenções: sucesso {"data": ..., "meta": ...}; erro
{"error": {"code", "message", "request_id", "details"?}} (ver app/errors.py);
contrato completo em /api/v1/openapi.json.
"""
from flask import Blueprint, request
from werkzeug.exceptions import UnsupportedMediaType

bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

_METODOS_COM_CORPO = ('POST', 'PUT', 'PATCH')


@bp.before_request
def _exigir_json_quando_ha_corpo():
    """Requisições com corpo só são aceitas como application/json (contrato
    único e defesa em profundidade: a API não usa cookie, mas um <form> de outro
    site também não consegue enviar esse tipo sem passar por CORS)."""
    tem_corpo = request.content_length or 'chunked' in request.headers.get('Transfer-Encoding', '')
    if request.method in _METODOS_COM_CORPO and tem_corpo and not request.is_json:
        raise UnsupportedMediaType('Envie o corpo como application/json.')


@bp.after_request
def _cabecalhos_padrao(resposta):
    # Endpoints públicos sobrescrevem isto com @cache_publico; o resto nunca é cacheado.
    resposta.headers.setdefault('Cache-Control', 'no-store')
    return resposta


# Registra as rotas (import no fim, depois de `bp` existir).
from app.api.v1 import (admin, autenticacao, catalogo, favoritos, instituicoes, me,  # noqa: E402,F401
                        openapi, teste_vocacional)
