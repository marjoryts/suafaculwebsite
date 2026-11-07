"""Identificador de requisição (X-Request-ID) para correlacionar cliente e logs.

Aceita o ID enviado pelo cliente (sanitizado) ou gera um novo, e o devolve no
cabeçalho de toda resposta. Aparece também no envelope de erro da API v1.
"""
import re
import uuid

from flask import g, request

_ID_VALIDO = re.compile(r'^[A-Za-z0-9._-]{1,64}$')


def registrar(app):
    @app.before_request
    def _definir_request_id():
        recebido = request.headers.get('X-Request-ID', '')
        g.request_id = recebido if _ID_VALIDO.match(recebido) else uuid.uuid4().hex

    @app.after_request
    def _devolver_request_id(resposta):
        resposta.headers['X-Request-ID'] = g.get('request_id') or uuid.uuid4().hex
        return resposta
