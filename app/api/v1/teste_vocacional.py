"""Teste vocacional: perguntas (públicas), envio de respostas, histórico e cursos recomendados."""
from flask import g, jsonify, request

from app.api.v1 import bp
from app.api.v1.auth import requer_usuario, usuario_atual
from app.api.v1.http import cache_publico, corpo_json
from app.services import teste_vocacional_service
from app.services.erros import ValidacaoError
from app.services.paginacao import inteiro


@bp.get('/teste-vocacional/perguntas')
@cache_publico
def teste_perguntas():
    return jsonify({'data': teste_vocacional_service.questionario()})


@bp.post('/teste-vocacional/resultados')
def teste_enviar_respostas():
    """Corpo: {"respostas": {"q1": "a", ..., "q10": "c"}}. A pontuação é feita no
    servidor. Se houver usuário autenticado o resultado é salvo no histórico dele."""
    respostas = corpo_json().get('respostas')
    if not isinstance(respostas, dict):
        raise ValidacaoError('Informe "respostas" como um objeto {"q1": "a", ...}.')
    usuario = usuario_atual(obrigatorio=False)
    resultado = teste_vocacional_service.submeter(
        {str(k): v for k, v in respostas.items()}, usuario_id=usuario['id'] if usuario else None)
    return jsonify({'data': resultado}), 201


@bp.get('/teste-vocacional/resultados')
@requer_usuario
def teste_historico():
    limite = min(inteiro(request.args.get('limit'), 10), 50)
    itens = teste_vocacional_service.historico(g.usuario['id'], limite=limite)
    return jsonify({'data': itens, 'meta': {'total': len(itens)}})


@bp.get('/teste-vocacional/recomendacoes')
@requer_usuario
def teste_recomendacoes():
    """Cursos ordenados por compatibilidade (%) com um resultado da própria conta
    (?id=; padrão: o mais recente). Mesma regra da página de resultado do site."""
    limite = max(1, min(inteiro(request.args.get('limite'), 50), 200))
    resultado_id = inteiro(request.args.get('id'), None)
    dados = teste_vocacional_service.recomendacoes(g.usuario['id'], resultado_id=resultado_id, limite=limite)
    return jsonify({'data': dados})
