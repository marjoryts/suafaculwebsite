"""Helpers HTTP compartilhados pelas rotas da API v1 (sem regra de negócio)."""
from functools import wraps

from flask import jsonify, make_response, request

from app.services.erros import ValidacaoError
from app.services.paginacao import inteiro, paginar

LIMITE_PADRAO = 20
LIMITE_MAXIMO = 100

# Conteúdo público (mesmo para todos): CDN pode guardar por alguns minutos.
CACHE_PUBLICO = 'public, max-age=60, s-maxage=300'


def cache_publico(view):
    """Marca respostas 200 de endpoints PÚBLICOS como cacheáveis pela CDN.
    (Endpoints autenticados ficam com `no-store` — ver api/v1/__init__.py.)"""
    @wraps(view)
    def envolvido(*args, **kwargs):
        resposta = make_response(view(*args, **kwargs))
        if resposta.status_code == 200:
            resposta.headers['Cache-Control'] = CACHE_PUBLICO
        return resposta
    return envolvido


def corpo_json():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        raise ValidacaoError('O corpo da requisição deve ser um objeto JSON.')
    return dados


def campo_texto(dados, campo):
    """Campo de texto do corpo JSON: ausente/None vira ''; outro tipo é erro 422
    (evita que um número ou lista vire erro 500 mais adiante)."""
    valor = dados.get(campo)
    if valor is None:
        return ''
    if not isinstance(valor, str):
        raise ValidacaoError(f'O campo "{campo}" deve ser texto.', details={'campo': campo})
    return valor


def texto_arg(nome):
    return request.args.get(nome, '').strip()


def lista_arg(nome):
    """Parâmetro repetido (?modalidade=a&modalidade=b) sem valores vazios."""
    return [v for v in request.args.getlist(nome) if v]


def responder_pagina(repositorio, filtros, chave, dto):
    """Pagina via service e devolve o formato {data: [...], meta: {...}}."""
    resultado = paginar(
        repositorio, filtros,
        page=request.args.get('page'),
        limit=inteiro(request.args.get('limit'), LIMITE_PADRAO),
        chave=chave, limite_maximo=LIMITE_MAXIMO,
    )
    return jsonify({
        'data': [dto(i) for i in resultado[chave]],
        'meta': {k: resultado[k] for k in ('total', 'page', 'limit', 'total_pages')},
    })
