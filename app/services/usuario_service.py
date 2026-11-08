"""Regras de negócio de usuários: cadastro, login, perfil e administração.

Compartilhado por Web (cookie de sessão) e Mobile (tokens). Não conhece HTTP
nem sessão: recebe dados, valida, aplica a regra e devolve o resultado.
Violações de regra levantam ErroDeNegocio (ver services/erros.py).
"""
from app.models.usuario import Usuario, normalizar_email
from app.services import limite_service, token_service
from app.services.erros import ConflitoError, NaoAutenticadoError, PermissaoNegadaError, ValidacaoError
from app.services.validacao import SENHA_MINIMA, exigir_email_valido, exigir_senha_valida  # noqa: F401


def _como_id(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValidacaoError('ID inválido.', details={'campo': 'id'})


def registrar(username, email, password, ip=None):
    """Cria conta de aluno com o e-mail AINDA NÃO verificado e envia o código de
    verificação. Devolve o dict do model + 'verificacao_enviada'."""
    username, email, password = (username or '').strip(), normalizar_email(email), (password or '')
    if not username or not email or not password:
        raise ValidacaoError('Por favor, preencha todos os campos.')
    exigir_email_valido(email)
    exigir_senha_valida(password)
    limite_service.consumir('cadastro_ip', ip)
    if Usuario().existe_conflito(username, email):
        raise ConflitoError('Nome de usuário ou e-mail já cadastrado.')
    resultado = Usuario().criar(username, email, password)
    if resultado.get('success'):
        from app.services import conta_service  # import tardio: conta_service depende deste pacote
        resultado['verificacao_enviada'] = conta_service.enviar_verificacao(Usuario().buscar_por_email(email))
    return resultado


def _exigir_limite_login(login, ip):
    """Bloqueio temporário após muitas senhas erradas (por conta e por IP). A mesma
    resposta 429 vale para conta existente ou não: não revela quais contas existem."""
    limite_service.exigir('login_conta', normalizar_email(login))
    limite_service.exigir('login_ip', ip)


def _registrar_resultado_login(login, ip, sucesso):
    if sucesso:
        limite_service.limpar('login_conta', normalizar_email(login))
    else:
        limite_service.registrar('login_conta', normalizar_email(login))
        limite_service.registrar('login_ip', ip)


def autenticar(login, senha, ip=None):
    """Valida credenciais. Devolve {'success': True, 'user': {...}} ou
    {'success': False, 'message': ...} (mensagem única para usuário
    inexistente e senha errada)."""
    login, senha = (login or '').strip(), (senha or '')
    if not login or not senha:
        raise ValidacaoError('Por favor, preencha todos os campos.')
    _exigir_limite_login(login, ip)
    resultado = Usuario().autenticar(login, senha)
    _registrar_resultado_login(login, ip, resultado.get('success'))
    return resultado


def autenticar_por_email(email, senha, ip=None):
    """Login por e-mail + senha (usado pela API do Mobile). Devolve o usuário ou
    levanta NaoAutenticadoError('INVALID_CREDENTIALS') — mesma resposta para
    e-mail inexistente e senha errada."""
    email, senha = normalizar_email(email), (senha or '')
    if not email or not senha:
        raise ValidacaoError('Informe e-mail e senha.')
    _exigir_limite_login(email, ip)
    usuario = Usuario().autenticar_por_email(email, senha)
    _registrar_resultado_login(email, ip, usuario is not None)
    if usuario is None:
        raise NaoAutenticadoError('E-mail ou senha inválidos.', code='INVALID_CREDENTIALS')
    return usuario


def atualizar_perfil(usuario_id, username, email, password='', confirmacao='', manter_sessao_api=None,
                     senha_atual=''):
    """O usuário altera os PRÓPRIOS dados (nunca o tipo de acesso).

    - Nome de usuário: muda direto.
    - E-mail: NÃO muda aqui — exige confirmar o novo endereço por código
      (conta_service.solicitar_troca_email / confirmar_troca_email).
    - Senha: exige a senha atual (conta_service.alterar_senha), encerra as sessões
      do app nos outros aparelhos e as do site abertas antes."""
    username, email = (username or '').strip(), normalizar_email(email)
    if not username or not email:
        raise ValidacaoError('Nome de usuário e e-mail são obrigatórios.')
    atual = Usuario().buscar_por_id(usuario_id)
    if email != normalizar_email(atual['email']):
        raise ValidacaoError('Para trocar o e-mail é preciso confirmar o novo endereço com um código.',
                             code='EMAIL_CHANGE_REQUIRES_VERIFICATION', details={'campo': 'email'})
    if Usuario().existe_conflito(username, atual['email'], ignorar_id=usuario_id):
        raise ValidacaoError('Esse nome de usuário ou e-mail já está em uso.')
    if password:
        from app.services import conta_service  # import tardio (evita ciclo)
        conta_service.alterar_senha(usuario_id, senha_atual, password, confirmacao, manter_sessao_api)
    resultado = Usuario().atualizar(usuario_id, username, atual['email'])
    if resultado.get('success'):
        resultado['message'] = 'Perfil atualizado com sucesso!'
    elif 'UNIQUE' in resultado.get('message', ''):  # corrida entre a checagem e o UPDATE
        resultado['message'] = 'Esse nome de usuário ou e-mail já está em uso.'
    return resultado


def atualizar_por_admin(usuario_id, username, email, password=None):
    username, email = (username or '').strip(), (email or '').strip()
    if not usuario_id or not username or not email:
        raise ValidacaoError('Dados obrigatórios não fornecidos.')
    usuario_id = _como_id(usuario_id)
    email = normalizar_email(email)
    exigir_email_valido(email)
    senha = password or None
    if senha:
        exigir_senha_valida(senha)
    anterior = Usuario().buscar_por_id(usuario_id)
    resultado = Usuario().atualizar(usuario_id, username, email, senha)
    if resultado.get('success'):
        if senha:
            token_service.revogar_sessoes_do_usuario(usuario_id)
        if anterior and email != normalizar_email(anterior['email']):
            # O admin trocou o e-mail: o novo endereço ainda não foi confirmado pelo dono.
            Usuario().marcar_email_nao_verificado(usuario_id)
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
