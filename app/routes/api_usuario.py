"""API legada /api/usuario/* (usada pelo frontend Web via cookie de sessão).

As regras vivem em app/services/usuario_service.py; aqui só há HTTP/sessão.
Violações de regra (ErroDeNegocio) viram {'success': False, 'message': ...}
pelo tratador registrado em app/factory.py.
"""
from flask import Blueprint, jsonify, request, session

from app.models.usuario import Usuario, normalizar_email
from app.rede import ip_cliente
from app.security import admin_required, login_usuario_na_sessao
from app.services import conta_service, usuario_service

# Campos do usuário que o frontend recebe (nada de versão de credencial, google_id...).
_CAMPOS_PUBLICOS = ('id', 'nome_usuario', 'email', 'tipo', 'avatar_url', 'email_verificado')


def _publico(usuario):
    return {k: usuario.get(k) for k in _CAMPOS_PUBLICOS}

bp = Blueprint('api_usuario', __name__, url_prefix='/api/usuario')


@bp.route('/registrar', methods=['POST'])
def registrar():
    """Cria a conta (e-mail ainda não verificado) e envia o código de verificação;
    o frontend leva a pessoa para /verificar-email."""
    resultado = usuario_service.registrar(
        request.form.get('username'), request.form.get('email'), request.form.get('password'), ip=ip_cliente())
    if resultado.get('success'):
        resultado['email'] = normalizar_email(request.form.get('email'))
        resultado['message'] = ('Conta criada! Enviamos um código para o seu e-mail.'
                                if resultado.get('verificacao_enviada') else
                                'Conta criada! Não foi possível enviar o código agora; peça um novo na próxima tela.')
    return jsonify(resultado)


@bp.route('/login', methods=['POST'])
def login():
    result = usuario_service.autenticar(request.form.get('username'), request.form.get('password'), ip=ip_cliente())
    if result['success']:
        login_usuario_na_sessao(result['user'])
        result['user'] = _publico(result['user'])
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
    """O usuário logado atualiza os PRÓPRIOS dados. Nome de usuário muda direto;
    trocar a senha exige a senha atual; trocar o e-mail envia um código ao novo
    endereço (confirmado em /email/confirmar). Tipo de acesso e outras contas
    continuam restritos ao admin."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
    uid = session['user_id']
    atual = Usuario().buscar_por_id(uid)
    novo_email = normalizar_email(request.form.get('email'))
    troca_email = bool(novo_email) and novo_email != normalizar_email(atual['email'])
    if troca_email:  # antes da troca de senha: confere a senha atual ainda válida
        conta_service.solicitar_troca_email(uid, novo_email, request.form.get('password_atual', ''))
    resultado = usuario_service.atualizar_perfil(
        uid, request.form.get('username'), atual['email'],
        request.form.get('password', ''), request.form.get('password_confirm', ''),
        senha_atual=request.form.get('password_atual', ''))
    if resultado.get('success'):
        atualizado = Usuario().buscar_por_id(uid)
        session['username'] = atualizado['nome_usuario']
        # A troca da própria senha muda a versão da credencial: esta sessão continua.
        session['credencial_versao'] = atualizado['credencial_versao']
        if troca_email:
            resultado.update({'email_pendente': True, 'email_novo': novo_email,
                              'message': f'Perfil salvo. Enviamos um código para {novo_email}: '
                                         'confirme-o para trocar o e-mail.'})
    return jsonify(resultado)


@bp.route('/email/confirmar', methods=['POST'])
def confirmar_email_novo():
    """Confirma a troca de e-mail com o código enviado ao novo endereço."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
    usuario = conta_service.confirmar_troca_email(session['user_id'], request.form.get('codigo'), ip=ip_cliente())
    session['email'] = usuario['email']
    return jsonify({'success': True, 'message': 'E-mail atualizado e confirmado!', 'email': usuario['email']})


@bp.route('/definir-tipo', methods=['POST'])
@admin_required
def definir_tipo():
    return jsonify(usuario_service.definir_tipo(
        session['user_id'], request.form.get('id'), request.form.get('tipo')))


@bp.route('/deletar', methods=['POST'])
@admin_required
def deletar():
    return jsonify(usuario_service.excluir(session['user_id'], request.form.get('id')))
