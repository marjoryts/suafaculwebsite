"""API legada /api/usuario/* (usada pelo frontend Web via cookie de sessão).

As regras vivem em app/services/usuario_service.py; aqui só há HTTP/sessão.
Violações de regra (ErroDeNegocio) viram {'success': False, 'message': ...}
pelo tratador registrado em app/factory.py.
"""
from flask import Blueprint, jsonify, request, session

from app.models.usuario import Usuario
from app.security import admin_required, login_usuario_na_sessao
from app.services import usuario_service

bp = Blueprint('api_usuario', __name__, url_prefix='/api/usuario')


@bp.route('/registrar', methods=['POST'])
def registrar():
    return jsonify(usuario_service.registrar(
        request.form.get('username'), request.form.get('email'), request.form.get('password')))


@bp.route('/login', methods=['POST'])
def login():
    result = usuario_service.autenticar(request.form.get('username'), request.form.get('password'))
    if result['success']:
        login_usuario_na_sessao(result['user'])
    return jsonify(result)


@bp.route('/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    return jsonify({'success': True})


@bp.route('/listar', methods=['GET'])
@admin_required
def listar():
    return jsonify({'success': True, 'usuarios': Usuario().listar()})


@bp.route('/buscar', methods=['GET'])
def buscar():
    # Dados de conta: só o próprio usuário ou um administrador podem ver.
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
    id = request.args.get('id')
    if not id:
        return jsonify({'success': False, 'message': 'ID não fornecido.'})
    if str(id) != str(session['user_id']) and session.get('tipo') != 'admin':
        return jsonify({'success': False, 'message': 'Acesso restrito a administradores.'}), 403
    u = Usuario().buscar_por_id(id)
    if u:
        return jsonify({'success': True, 'usuario': u})
    return jsonify({'success': False, 'message': 'Usuário não encontrado.'})


@bp.route('/atualizar', methods=['POST'])
@admin_required
def atualizar():
    return jsonify(usuario_service.atualizar_por_admin(
        request.form.get('id'), request.form.get('username'), request.form.get('email'),
        request.form.get('password')))


@bp.route('/perfil', methods=['POST'])
def perfil():
    """O usuário logado atualiza os PRÓPRIOS dados (nome de usuário, e-mail,
    senha). Não permite trocar o tipo de acesso nem editar outra conta — isso
    continua restrito a /api/usuario/atualizar e /definir-tipo (admin)."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
    resultado = usuario_service.atualizar_perfil(
        session['user_id'], request.form.get('username'), request.form.get('email'),
        request.form.get('password', ''), request.form.get('password_confirm', ''))
    if resultado.get('success'):
        session['username'] = request.form.get('username', '').strip()
        session['email'] = request.form.get('email', '').strip()
    return jsonify(resultado)


@bp.route('/definir-tipo', methods=['POST'])
@admin_required
def definir_tipo():
    return jsonify(usuario_service.definir_tipo(
        session['user_id'], request.form.get('id'), request.form.get('tipo')))


@bp.route('/deletar', methods=['POST'])
@admin_required
def deletar():
    return jsonify(usuario_service.excluir(session['user_id'], request.form.get('id')))
