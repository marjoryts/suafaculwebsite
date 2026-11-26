"""Verificação de saúde: o app responde E alcança o banco (Supabase).

Usado pelo app Mobile para diagnosticar conexão ("o servidor está no ar?") e
por monitoramento. Não revela detalhes de infraestrutura na resposta.
"""
from flask import Blueprint, current_app, jsonify

from app.models.saude import Saude

bp = Blueprint('health', __name__)


@bp.get('/api/health')
def health():
    try:
        Saude().verificar_banco()
        corpo, status = {'status': 'ok', 'database': 'ok'}, 200
    except Exception:
        current_app.logger.exception('[health] Banco de dados indisponível')
        corpo, status = {'status': 'degraded', 'database': 'unavailable'}, 503
    resposta = jsonify(corpo)
    resposta.status_code = status
    resposta.headers['Cache-Control'] = 'no-store'
    return resposta
