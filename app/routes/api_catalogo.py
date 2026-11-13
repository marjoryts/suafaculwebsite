"""API legada do catálogo: cursos, faculdades e busca dinâmica."""
from flask import Blueprint, jsonify, request

from app.models.curso import Curso
from app.models.curso_catalogo import CursoCatalogo
from app.models.faculdade import Faculdade
from app.security import admin_required
from app.services import admin_service
from app.services import busca_service
from app.services.paginacao import paginar

bp = Blueprint('api_catalogo', __name__, url_prefix='/api')


# ── Cursos ──────────────────────────────────────────────────────────────

@bp.route('/cursos/listar', methods=['GET'])
def cursos_listar():
    filtros = {}
    area = request.args.get('area', '')
    if area and area != 'Todas as áreas':
        filtros['area'] = area
    modalidade = [m for m in request.args.getlist('modalidade') if m]
    if modalidade:
        filtros['modalidade'] = modalidade
    tipo_inst = [t for t in request.args.getlist('tipo_instituicao') if t]
    if tipo_inst:
        filtros['tipo_instituicao'] = tipo_inst
    busca = request.args.get('busca', '')
    if busca:
        filtros['busca'] = busca
    dados = paginar(Curso(), filtros, request.args.get('page'), request.args.get('limit'), 'cursos')
    return jsonify({'success': True, **dados})


@bp.route('/cursos/catalogo', methods=['GET'])
def cursos_catalogo():
    """Formações da seção "Cursos" da página inicial: nome, área, grau,
    duração, descrição, imagem do card e quantas instituições oferecem.
    Parâmetro opcional: area."""
    area = request.args.get('area', '').strip()
    if area == 'Todas as áreas':
        area = ''
    catalogo = CursoCatalogo()
    return jsonify({'success': True, 'cursos': catalogo.listar(area or None), 'areas': catalogo.areas()})


@bp.route('/cursos/buscar', methods=['GET'])
def cursos_buscar():
    id = request.args.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    c = Curso().buscar_por_id(id)
    if c:
        return jsonify({'success': True, 'curso': c})
    return jsonify({'success': False, 'message': 'Curso não encontrado.'})


@bp.route('/cursos/sugestoes', methods=['GET'])
def cursos_sugestoes():
    """Autocomplete do campo 'curso' nas buscas (home e /faculdades):
    nomes de curso já cadastrados que começam com o termo digitado."""
    termo = request.args.get('q', '').strip()
    if len(termo) < 2:
        return jsonify({'sugestoes': []})
    return jsonify({'sugestoes': Curso().sugestoes_por_nome(termo, limite=8)})


@bp.route('/busca/sugestoes', methods=['GET'])
def busca_sugestoes():
    """Busca dinâmica do card de pesquisa (home e /faculdades): sugestões
    de localizações, faculdades e cursos que contêm o termo digitado
    (sem diferenciar acentos/maiúsculas), agrupadas por tipo.

    Parâmetros: q (termo, mín. 2 caracteres), tipos (opcional, lista
    separada por vírgula: local,faculdade,curso), limite (por tipo, máx. 10)."""
    termo = request.args.get('q', '').strip()
    tipos = [t.strip() for t in request.args.get('tipos', '').split(',') if t.strip()]
    tipos = tipos or list(busca_service.TIPOS)
    try:
        limite = int(request.args.get('limite', busca_service.LIMITE_PADRAO))
    except ValueError:
        limite = busca_service.LIMITE_PADRAO
    resultados = busca_service.sugestoes(termo, tipos=tipos, limite=limite)
    total = sum(len(v) for v in resultados.values())
    return jsonify({'success': True, 'termo': termo, 'resultados': resultados, 'total': total})


@bp.route('/cursos/criar', methods=['POST'])
@admin_required
def cursos_criar():
    return jsonify(admin_service.criar_curso(request.form))


# ── Faculdades ──────────────────────────────────────────────────────────

@bp.route('/faculdades/listar', methods=['GET'])
def faculdades_listar():
    filtros = {}
    for campo in ('tipo_instituicao', 'uf', 'cidade', 'curso', 'busca'):
        valor = request.args.get(campo, '')
        if valor:
            filtros[campo] = valor
    modalidade = [m for m in request.args.getlist('modalidade') if m]
    if modalidade:
        filtros['modalidade'] = modalidade
    # curso_exato=1: o filtro de curso compara o nome inteiro (usado pelos
    # cards de curso da home — "Física" não traz "Educação Física").
    if filtros.get('curso') and request.args.get('curso_exato') in ('1', 'true'):
        filtros['curso_exato'] = True
    dados = paginar(Faculdade(), filtros, request.args.get('page'), request.args.get('limit'), 'faculdades')
    return jsonify({'success': True, **dados})


@bp.route('/faculdades/buscar', methods=['GET'])
def faculdades_buscar():
    id = request.args.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    f = Faculdade().buscar_por_id(id)
    if f:
        return jsonify({'success': True, 'faculdade': f})
    return jsonify({'success': False, 'message': 'Faculdade não encontrada.'})


@bp.route('/faculdades/criar', methods=['POST'])
@admin_required
def faculdades_criar():
    return jsonify(admin_service.criar_faculdade(request.form))


@bp.route('/faculdades/atualizar', methods=['POST'])
@admin_required
def faculdades_atualizar():
    id = request.form.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    return jsonify(admin_service.atualizar_faculdade(id, request.form))


@bp.route('/faculdades/deletar', methods=['POST'])
@admin_required
def faculdades_deletar():
    id = request.form.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    return jsonify(admin_service.excluir_faculdade(id))
