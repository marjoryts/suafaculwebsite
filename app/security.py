"""Controle de acesso compartilhado por todas as rotas (páginas e API).

Autenticação por cookie de sessão assinado (stateless: funciona em ambiente
serverless, sem sessão em memória). O papel do usuário é sempre conferido no
banco, nunca confiado ao cookie.
"""
from functools import wraps

from flask import jsonify, redirect, request, session, url_for

from app.models.teste_vocacional import TesteVocacional
from app.models.usuario import Usuario


def login_usuario_na_sessao(user):
    session.permanent = True
    session['user_id'] = user['id']
    session['username'] = user['nome_usuario']
    session['email'] = user['email']
    session['tipo'] = user.get('tipo', 'aluno')
    session['avatar_url'] = user.get('avatar_url')
    # Muda quando a senha é trocada/recuperada: sessões abertas antes deixam de valer.
    session['credencial_versao'] = user.get('credencial_versao')
    _vincular_teste_pendente(user['id'])


def verificar_sessao_web():
    """before_request do site: o cookie é assinado e não tem como ser revogado, então
    a cada requisição conferimos no banco se a conta existe e se a credencial é a
    mesma do login. Trocar/recuperar a senha ou excluir a conta derruba a sessão."""
    if 'user_id' not in session or request.path.startswith(('/api/v1/', '/static/')):
        return
    atual = Usuario().buscar_por_id(session['user_id'])
    if not atual or session.get('credencial_versao') != atual.get('credencial_versao'):
        session.clear()


def _vincular_teste_pendente(user_id):
    """Se a pessoa fez o teste vocacional sem login neste navegador, o id
    do resultado fica no cookie de sessão (assinado pelo Flask, não pode ser
    forjado). Ao entrar/cadastrar, o resultado passa a ser da conta que
    acabou de se autenticar — só se ainda não tiver dono."""
    pendente = session.pop('teste_pendente_id', None)
    if pendente:
        TesteVocacional().vincular_a_usuario(pendente, user_id)


def destino_seguro(valor):
    """Só aceita caminhos internos (evita redirecionamento aberto)."""
    valor = (valor or '').strip()
    if valor.startswith('/') and not valor.startswith('//') and '\\' not in valor:
        return valor
    return None


def check_auth():
    """None se autenticado; senão a resposta 401 pronta (uso em rotas de API)."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
    return None


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('pages.login'))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
            return redirect(url_for('pages.login'))
        # O papel é conferido no banco a cada requisição: o cookie pode ter
        # até 7 dias e não reflete rebaixamento/exclusão feitos depois do login.
        atual = Usuario().buscar_por_id(session['user_id'])
        if not atual:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Usuário não autenticado.'}), 401
            return redirect(url_for('pages.login'))
        session['tipo'] = atual['tipo']
        if atual['tipo'] != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Acesso restrito a administradores.'}), 403
            return redirect(url_for('pages.dashboard'))
        return f(*args, **kwargs)
    return wrapper
