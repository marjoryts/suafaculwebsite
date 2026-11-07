"""API legada do painel administrativo (somente Web): estatísticas e importações.

As importações longas (e-MEC por UF/Brasil, CSV do INEP) continuam síncronas
aqui por compatibilidade; a meta é movê-las para CLI + serviço reutilizável
(Etapa 3/6), pois a Vercel limita corpo (4,5 MB) e duração da função.
"""
from flask import Blueprint, current_app, jsonify, request

from app.security import admin_required
from app.services import admin_service, censo_service, emec_service

bp = Blueprint('api_admin', __name__, url_prefix='/api')


@bp.route('/admin/stats', methods=['GET'])
@admin_required
def stats():
    return jsonify({'success': True, **admin_service.estatisticas()})


@bp.route('/faculdades/emec/importar', methods=['POST'])
@admin_required
def emec_importar():
    """Importa uma ou várias faculdades do e-MEC por código.
    Aceita 'codigo' (único) ou 'codigos' (vários, separados por vírgula)."""
    codigo = request.form.get('codigo', '').strip()
    codigos_raw = request.form.get('codigos', '').strip()
    if codigo:
        return jsonify(emec_service.importar_faculdade_por_codigo(codigo))
    if codigos_raw:
        codigos = [c.strip() for c in codigos_raw.split(',') if c.strip()]
        return jsonify({'success': True, 'relatorio': emec_service.importar_faculdades_em_lote(codigos)})
    return jsonify({'success': False, 'message': "Informe 'codigo' ou 'codigos' do e-MEC."})


@bp.route('/faculdades/emec/importar-uf', methods=['POST'])
@admin_required
def emec_importar_uf():
    """Importa TODAS as instituições em atividade de uma UF a partir do e-MEC."""
    uf = request.form.get('uf', '').strip().upper()
    if not uf:
        return jsonify({'success': False, 'message': "Informe a UF (ex: 'SP')."})
    if uf not in emec_service.UFS_BRASIL:
        return jsonify({'success': False, 'message': f"UF inválida: {uf}"})
    return jsonify(emec_service.importar_todas_faculdades_por_uf(uf))


@bp.route('/faculdades/emec/importar-csv', methods=['POST'])
@admin_required
def emec_importar_csv():
    """Importa instituições a partir do CSV oficial de Dados Abertos do MEC
    enviado manualmente pelo admin."""
    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return jsonify({'success': False, 'message': 'Selecione o arquivo CSV.'})
    if not arquivo.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': 'Envie um arquivo .csv (baixado de dadosabertos.mec.gov.br).'})
    try:
        conteudo = arquivo.read()
        tamanho_mb = len(conteudo) / (1024 * 1024)
        if tamanho_mb > 300:  # só barra upload do arquivo errado por engano
            return jsonify({'success': False, 'message': f'Arquivo de {tamanho_mb:.1f}MB é maior do que o esperado — confirme que é o CSV de instituições (não outro dataset do INEP/MEC).'})
        return jsonify(emec_service.importar_instituicoes_de_csv_upload(conteudo))
    except Exception as e:
        current_app.logger.warning("[emec] Falha ao importar CSV enviado pelo admin: %s", e)
        return jsonify({'success': False, 'message': f'Falha ao processar o CSV: {e}'})


@bp.route('/cursos/censo/importar-csv', methods=['POST'])
@admin_required
def censo_importar_csv():
    """Importa cursos a partir do MICRODADOS_CADASTRO_CURSOS_<ano>.CSV do
    Censo da Educação Superior (INEP), em streaming."""
    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return jsonify({'success': False, 'message': 'Selecione o arquivo CSV.'})
    if not arquivo.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'message': 'Envie o arquivo MICRODADOS_CADASTRO_CURSOS_<ano>.CSV.'})
    try:
        return jsonify(censo_service.importar_cursos_de_csv_upload(arquivo.stream))
    except Exception as e:
        current_app.logger.warning("[censo] Falha ao importar cursos do Censo INEP: %s", e)
        return jsonify({'success': False, 'message': f'Falha ao processar o CSV: {e}'})


@bp.route('/faculdades/emec/importar-brasil', methods=['POST'])
@admin_required
def emec_importar_brasil():
    """Importa TODAS as instituições em atividade do Brasil (27 UFs)."""
    return jsonify(emec_service.importar_todas_faculdades_brasil())
