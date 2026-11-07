"""Endpoints chamados pelo Vercel Cron (GET, produção). Só HTTP: a execução,
a trava e o registro estão em services/automacao_service.py.

Segurança: a Vercel envia `Authorization: Bearer <CRON_SECRET>` quando a
variável CRON_SECRET existe no projeto. Sem CRON_SECRET (ou com menos de 16
caracteres) TODOS os endpoints ficam desligados (falha fechada).
"""
import hmac
import os

from flask import Blueprint, jsonify, request

from app.errors import envelope
from app.services import automacao_service
from app.services.erros import NaoEncontradoError

bp = Blueprint('cron', __name__, url_prefix='/api/cron')

TAMANHO_MINIMO_SEGREDO = 16


def _resposta_sem_cache(resposta):
    resposta.headers['Cache-Control'] = 'no-store'
    return resposta


def _autenticar():
    """None se autorizado; senão a resposta de erro pronta."""
    segredo = os.environ.get('CRON_SECRET', '').strip()
    if len(segredo) < TAMANHO_MINIMO_SEGREDO:
        return _resposta_sem_cache(envelope(503, 'CRON_DISABLED', 'Cron não configurado.'))
    recebido = request.headers.get('Authorization', '')
    if not hmac.compare_digest(recebido.encode('utf-8'), f'Bearer {segredo}'.encode('utf-8')):
        return _resposta_sem_cache(envelope(401, 'UNAUTHENTICATED', 'Não autorizado.'))
    return None


@bp.get('/<nome>')
def executar(nome):
    negado = _autenticar()
    if negado:
        return negado
    try:
        resultado = automacao_service.executar(nome, origem='cron')
    except NaoEncontradoError as e:
        return _resposta_sem_cache(envelope(404, e.code, e.message, e.details))
    # 200 para sucesso e "ignorada" (duplicata/concorrência); 500 só se o job falhou
    # (a Vercel não repete, mas registra a falha). O detalhe do erro fica no banco, não na resposta.
    status_http = 500 if resultado['status'] == 'falha' else 200
    resposta = jsonify(resultado)
    resposta.status_code = status_http
    return _resposta_sem_cache(resposta)
