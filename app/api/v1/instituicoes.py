"""API pública de instituições por código e-MEC (consumo externo; sem id interno).

Somente leitura, sem autenticação — catálogo de dados públicos do MEC.
"""
from flask import jsonify

from app.api.v1 import bp
from app.api.v1.http import cache_publico, responder_pagina, texto_arg
from app.api.v1.serializers import instituicao_dto
from app.models.curso import Curso
from app.models.faculdade import Faculdade
from app.services.erros import NaoEncontradoError


def _instituicao_ou_404(codigo_emec):
    instituicao = Faculdade().buscar_por_codigo_emec(codigo_emec)
    if not instituicao:
        raise NaoEncontradoError('Instituição não encontrada para este código e-MEC.')
    return instituicao


@bp.get('/instituicoes')
@cache_publico
def instituicoes_listar():
    """Filtros (opcionais): uf, cidade, tipo_instituicao ('Pública'|'Privada'), busca."""
    filtros = {}
    for campo in ('uf', 'cidade', 'tipo_instituicao', 'busca'):
        valor = texto_arg(campo)
        if valor:
            filtros[campo] = valor.upper() if campo == 'uf' else valor
    return responder_pagina(Faculdade(), filtros, 'instituicoes', instituicao_dto)


@bp.get('/instituicoes/<codigo_emec>')
@cache_publico
def instituicao_detalhe(codigo_emec):
    return jsonify({'data': instituicao_dto(_instituicao_ou_404(codigo_emec))})


@bp.get('/instituicoes/<codigo_emec>/cursos')
@cache_publico
def instituicao_cursos(codigo_emec):
    """Cursos de graduação de uma instituição (importados do Censo INEP)."""
    instituicao = _instituicao_ou_404(codigo_emec)
    cursos = Curso().listar_por_faculdade(instituicao['id'])
    return jsonify({'data': cursos,
                    'meta': {'total': len(cursos), 'instituicao': instituicao['nome']}})
