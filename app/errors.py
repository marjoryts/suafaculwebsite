"""Tratamento central de erros.

  /api/v1/*   envelope estruturado: {"error": {"code", "message", "request_id", "details"?}}
  /api/* legado  HTTP 200 + {"success": false, "message": ...} (contrato do frontend Web)
  páginas     página 404 do site; demais erros seguem o padrão do Flask

Nunca expõe stack trace, SQL ou detalhes internos em respostas 5xx.
"""
from flask import g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from app.services.erros import ErroDeNegocio

CODIGOS_HTTP = {
    400: 'BAD_REQUEST', 401: 'UNAUTHENTICATED', 403: 'FORBIDDEN', 404: 'RESOURCE_NOT_FOUND',
    405: 'METHOD_NOT_ALLOWED', 413: 'PAYLOAD_TOO_LARGE', 415: 'UNSUPPORTED_MEDIA_TYPE',
    422: 'VALIDATION_ERROR', 429: 'RATE_LIMITED',
}


def eh_api_v1():
    return request.path == '/api/v1' or request.path.startswith('/api/v1/')


def envelope(status, code, message, details=None):
    erro = {'code': code, 'message': message, 'request_id': g.get('request_id')}
    if details:
        erro['details'] = details
    resposta = jsonify({'error': erro})
    resposta.status_code = status
    if status == 401:
        resposta.headers['WWW-Authenticate'] = 'Bearer'
    return resposta


def registrar_tratadores(app):
    @app.errorhandler(ErroDeNegocio)
    def _erro_de_negocio(e):
        retry_after = getattr(e, 'retry_after', None)
        if eh_api_v1():
            resposta = envelope(e.status, e.code, e.message, e.details)
        else:
            # Web legado: HTTP 200 + success:false (contrato do frontend); excesso de
            # tentativas devolve 429, que o JS trata como erro com a mesma mensagem.
            resposta = jsonify({'success': False, 'message': e.message})
            if retry_after:
                resposta.status_code = 429
        if retry_after:
            resposta.headers['Retry-After'] = str(retry_after)
        return resposta

    @app.errorhandler(HTTPException)
    def _erro_http(e):
        if eh_api_v1():
            status = e.code or 500
            if status >= 500:
                return envelope(status, 'INTERNAL_ERROR', 'Erro interno do servidor.')
            resposta = envelope(status, CODIGOS_HTTP.get(status, 'HTTP_ERROR'), e.description)
            if status == 405 and getattr(e, 'valid_methods', None):
                resposta.headers['Allow'] = ', '.join(e.valid_methods)
            return resposta
        if e.code == 404:
            return render_template('404.html'), 404
        return e
