"""API legada de vestibulares (+ disparo manual da automação de validação)."""
from flask import Blueprint, jsonify, request

from app.models.vestibular import Vestibular
from app.security import admin_required
from app.services import admin_service, vestibular_service
from app.services.paginacao import paginar

bp = Blueprint('api_vestibulares', __name__, url_prefix='/api/vestibulares')


@bp.route('/listar', methods=['GET'])
def listar():
    filtros = {}
    for campo in ('tipo_instituicao', 'busca', 'curso'):
        valor = request.args.get(campo, '')
        if valor:
            filtros[campo] = valor
    regioes = [r for r in request.args.getlist('regiao') if r]  # pode marcar várias
    if regioes:
        filtros['regiao'] = regioes
    meses = [int(m) for m in request.args.getlist('mes') if m.isdigit()]
    if meses:
        filtros['meses'] = meses
    if request.args.get('incluir_privados') != 'true':
        filtros['apenas_publicos'] = True
    dados = paginar(Vestibular(), filtros, request.args.get('page'), request.args.get('limit'), 'vestibulares')
    return jsonify({'success': True, **dados})


@bp.route('/buscar', methods=['GET'])
def buscar():
    id = request.args.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    v = Vestibular().buscar_por_id(id)
    if v:
        return jsonify({'success': True, 'vestibular': v})
    return jsonify({'success': False, 'message': 'Vestibular não encontrado.'})


@bp.route('/criar', methods=['POST'])
@admin_required
def criar():
    return jsonify(admin_service.criar_vestibular(request.form))


@bp.route('/validar', methods=['GET', 'POST'])
@admin_required
def validar():
    """Automação: valida as datas dos vestibulares e confere se a instituição
    já está cadastrada em `faculdades`. GET faz só o relatório (dry-run);
    POST com aplicar=true grava status_validacao/cadastrado_ok/faculdade_id."""
    aplicar = request.values.get('aplicar', 'false').lower() == 'true'
    return jsonify(vestibular_service.validar_vestibulares(aplicar=aplicar))
