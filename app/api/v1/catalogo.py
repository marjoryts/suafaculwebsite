"""Catálogo público: cursos, faculdades, vestibulares e busca dinâmica."""
from flask import jsonify, request

from app.api.v1 import bp
from app.api.v1.http import cache_publico, lista_arg, responder_pagina, texto_arg
from app.api.v1.serializers import (curso_dto, faculdade_detalhe_dto, faculdade_dto, vestibular_dto)
from app.models.curso import Curso
from app.models.faculdade import Faculdade
from app.models.vestibular import Vestibular
from app.services import busca_service
from app.services.erros import NaoEncontradoError
from app.services.paginacao import inteiro


def _filtros(**campos):
    """Monta o dict de filtros com os campos de texto presentes na query."""
    filtros = {}
    for nome, transformar in campos.items():
        valor = texto_arg(nome)
        if valor:
            filtros[nome] = transformar(valor)
    return filtros


# ── Cursos ──────────────────────────────────────────────────────────────

@bp.get('/cursos')
@cache_publico
def cursos_listar():
    filtros = _filtros(area=str, busca=str)
    if filtros.get('area') == 'Todas as áreas':
        del filtros['area']
    for campo in ('modalidade', 'tipo_instituicao'):
        valores = lista_arg(campo)
        if valores:
            filtros[campo] = valores
    return responder_pagina(Curso(), filtros, 'cursos', curso_dto)


@bp.get('/cursos/<int:curso_id>')
@cache_publico
def curso_detalhe(curso_id):
    curso = Curso().buscar_por_id(curso_id)
    if not curso:
        raise NaoEncontradoError('Curso não encontrado.')
    return jsonify({'data': curso_dto(curso)})


# ── Faculdades ──────────────────────────────────────────────────────────

@bp.get('/faculdades')
@cache_publico
def faculdades_listar():
    filtros = _filtros(tipo_instituicao=str, uf=str.upper, cidade=str, curso=str, busca=str)
    modalidade = lista_arg('modalidade')
    if modalidade:
        filtros['modalidade'] = modalidade
    return responder_pagina(Faculdade(), filtros, 'faculdades', faculdade_dto)


@bp.get('/faculdades/<int:faculdade_id>')
@cache_publico
def faculdade_detalhe(faculdade_id):
    faculdade = Faculdade().buscar_por_id(faculdade_id)
    if not faculdade:
        raise NaoEncontradoError('Faculdade não encontrada.')
    return jsonify({'data': faculdade_detalhe_dto(faculdade)})


# ── Vestibulares ────────────────────────────────────────────────────────

@bp.get('/vestibulares')
@cache_publico
def vestibulares_listar():
    filtros = _filtros(tipo_instituicao=str, busca=str, curso=str)
    regioes = lista_arg('regiao')  # repetível: ?regiao=Sudeste&regiao=Sul
    if regioes:
        filtros['regiao'] = regioes
    meses = sorted({int(m) for m in lista_arg('mes') if m.isdigit() and 1 <= int(m) <= 12})
    if meses:
        filtros['meses'] = meses
    # Por padrão só instituições públicas (regra do site); ?incluir_privados=true inclui as demais.
    if request.args.get('incluir_privados') != 'true':
        filtros['apenas_publicos'] = True
    return responder_pagina(Vestibular(), filtros, 'vestibulares', vestibular_dto)


@bp.get('/vestibulares/<int:vestibular_id>')
@cache_publico
def vestibular_detalhe(vestibular_id):
    vestibular = Vestibular().buscar_por_id(vestibular_id)
    if not vestibular:
        raise NaoEncontradoError('Vestibular não encontrado.')
    return jsonify({'data': vestibular_dto(vestibular)})


# ── Busca dinâmica (autocomplete) ───────────────────────────────────────

@bp.get('/busca/sugestoes')
@cache_publico
def busca_sugestoes():
    """Sugestões agrupadas por tipo (local, faculdade, curso) para o termo digitado."""
    termo = texto_arg('q')
    tipos = [t.strip() for t in request.args.get('tipos', '').split(',') if t.strip()] or list(busca_service.TIPOS)
    limite = inteiro(request.args.get('limite'), busca_service.LIMITE_PADRAO)
    resultados = busca_service.sugestoes(termo, tipos=tipos, limite=limite)
    return jsonify({'data': resultados,
                    'meta': {'termo': termo, 'total': sum(len(v) for v in resultados.values())}})
