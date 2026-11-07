"""Regras de negócio de usuários: cadastro, login, perfil e administração.

Compartilhado por Web (cookie de sessão) e Mobile (tokens). Não conhece HTTP
nem sessão: recebe dados, valida, aplica a regra e devolve o resultado.
Violações de regra levantam ErroDeNegocio (ver services/erros.py).
"""
import re

from app.models.usuario import Usuario
from app.services import token_service
from app.services.erros import ConflitoError, NaoAutenticadoError, PermissaoNegadaError, ValidacaoError

SENHA_MINIMA = 6
_EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')


def _exigir_email_valido(email):
    if not _EMAIL_RE.match(email):
        raise ValidacaoError('Formato de e-mail inválido.', details={'campo': 'email'})


def _exigir_senha_valida(senha, mensagem):
    if len(senha) < SENHA_MINIMA:
        raise ValidacaoError(mensagem, details={'campo': 'password'})


def _como_id(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValidacaoError('ID inválido.', details={'campo': 'id'})


def registrar(username, email, password):
    """Cria conta de aluno. Devolve o dict do model ({'success', 'message'})."""
    username, email, password = (username or '').strip(), (email or '').strip(), (password or '').strip()
    if not username or not email or not password:
        raise ValidacaoError('Por favor, preencha todos os campos.')
    _exigir_email_valido(email)
    _exigir_senha_valida(password, f'A senha deve ter pelo menos {SENHA_MINIMA} caracteres.')
    if Usuario().existe_conflito(username, email):
        raise ConflitoError('Nome de usuário ou e-mail já cadastrado.')
    return Usuario().criar(username, email, password)


def autenticar(login, senha):
    """Valida credenciais. Devolve {'success': True, 'user': {...}} ou
    {'success': False, 'message': ...} (mensagem única para usuário
    inexistente e senha errada)."""
    login, senha = (login or '').strip(), (senha or '').strip()
    if not login or not senha:
        raise ValidacaoError('Por favor, preencha todos os campos.')
    return Usuario().autenticar(login, senha)


def autenticar_por_email(email, senha):
    """Login por e-mail + senha (usado pela API do Mobile). Devolve o usuário ou
    levanta NaoAutenticadoError('INVALID_CREDENTIALS') — mesma resposta para
    e-mail inexistente e senha errada."""
    email, senha = (email or '').strip(), (senha or '').strip()
    if not email or not senha:
        raise ValidacaoError('Informe e-mail e senha.')
    usuario = Usuario().autenticar_por_email(email, senha)
    if usuario is None:
        raise NaoAutenticadoError('E-mail ou senha inválidos.', code='INVALID_CREDENTIALS')
    return usuario


def atualizar_perfil(usuario_id, username, email, password='', confirmacao='', manter_sessao_api=None):
    """O usuário altera os PRÓPRIOS dados (nunca o tipo de acesso).

    Trocar a senha encerra as sessões do app (refresh tokens) em outros
    dispositivos; `manter_sessao_api` preserva a sessão de quem fez a troca."""
    username, email = (username or '').strip(), (email or '').strip()
    if not username or not email:
        raise ValidacaoError('Nome de usuário e e-mail são obrigatórios.')
    _exigir_email_valido(email)
    if password:
        _exigir_senha_valida(password, f'A nova senha deve ter pelo menos {SENHA_MINIMA} caracteres.')
        if password != confirmacao:
            raise ValidacaoError('A confirmação não confere com a nova senha.')
    if Usuario().existe_conflito(username, email, ignorar_id=usuario_id):
        raise ValidacaoError('Esse nome de usuário ou e-mail já está em uso.')
    resultado = Usuario().atualizar(usuario_id, username, email, password or None)
    if resultado.get('success'):
        resultado['message'] = 'Perfil atualizado com sucesso!'
        if password:
            token_service.revogar_sessoes_do_usuario(usuario_id, manter_familia=manter_sessao_api)
    elif 'UNIQUE' in resultado.get('message', ''):  # corrida entre a checagem e o UPDATE
        resultado['message'] = 'Esse nome de usuário ou e-mail já está em uso.'
    return resultado


def atualizar_por_admin(usuario_id, username, email, password=None):
    username, email = (username or '').strip(), (email or '').strip()
    if not usuario_id or not username or not email:
        raise ValidacaoError('Dados obrigatórios não fornecidos.')
    usuario_id = _como_id(usuario_id)
    senha = (password or '').strip() or None
    resultado = Usuario().atualizar(usuario_id, username, email, senha)
    if senha and resultado.get('success'):
        token_service.revogar_sessoes_do_usuario(usuario_id)
    return resultado


def definir_tipo(ator_id, alvo_id, tipo):
    """Promove/rebaixa. Regra: ninguém remove o próprio acesso de admin."""
    tipo = (tipo or '').strip()
    if not alvo_id or not tipo:
        raise ValidacaoError('Dados obrigatórios não fornecidos.')
    alvo_id = _como_id(alvo_id)
    if alvo_id == ator_id and tipo != 'admin':
        raise PermissaoNegadaError('Você não pode remover seu próprio acesso de admin.')
    return Usuario().definir_tipo(alvo_id, tipo)


def excluir(ator_id, alvo_id):
    """Regra: ninguém exclui a própria conta pelo painel administrativo."""
    if not alvo_id:
        raise ValidacaoError('ID não fornecido.')
    alvo_id = _como_id(alvo_id)
    if alvo_id == ator_id:
        raise PermissaoNegadaError('Você não pode excluir seu próprio usuário.')
    return Usuario().deletar(alvo_id)
