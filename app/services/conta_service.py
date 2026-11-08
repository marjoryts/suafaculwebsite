"""Segurança da conta: verificação de e-mail, recuperação de senha, troca de senha
e troca de e-mail. Regras únicas para o site e o app (as duas interfaces chamam
estas funções).

Princípios:
- Respostas de "pedido" (enviar código, recuperar senha) são genéricas: não
  revelam se um e-mail está cadastrado.
- Códigos: ver codigo_service (HMAC, validade, tentativas, uso único).
- Limites de abuso: ver limite_service.
- Redefinir a senha encerra TODAS as sessões (app e site); trocar a senha logado
  encerra as outras (a atual continua).
"""
from app.models.usuario import Usuario, normalizar_email
from app.services import codigo_service, email_service, limite_service, token_service
from app.services.erros import ConflitoError, LimiteExcedidoError, ValidacaoError
from app.services.validacao import exigir_email_valido, exigir_senha_valida

MENSAGEM_ENVIO_GENERICA = ('Se houver uma conta com esse e-mail, enviaremos um código em instantes. '
                           'Confira também a caixa de spam.')


def _enviar(usuario, finalidade, destino):
    codigo = codigo_service.gerar(usuario['id'], finalidade, destino)
    return email_service.enviar_codigo(destino, finalidade, codigo, nome=usuario.get('nome_usuario'),
                                       validade_min=codigo_service.VALIDADE_MINUTOS[finalidade])


# ── Verificação de e-mail ───────────────────────────────────────────────

def enviar_verificacao(usuario):
    """Envia o código de verificação a uma conta ainda não verificada (ex.: logo após o
    cadastro). Devolve True se o e-mail saiu."""
    if not usuario or usuario.get('email_verificado'):
        return False
    return _enviar(usuario, 'verificacao', usuario['email'])


def solicitar_verificacao(email, ip=None):
    """Reenvio do código. Resposta sempre genérica (não diz se a conta existe)."""
    email = normalizar_email(email)
    exigir_email_valido(email)
    limite_service.consumir('verificacao_envio', email)
    limite_service.consumir('codigo_ip', ip)
    usuario = Usuario().buscar_por_email(email)
    if usuario and not usuario.get('email_verificado'):
        try:
            _enviar(usuario, 'verificacao', usuario['email'])
        except LimiteExcedidoError:
            # Reenvio antes do intervalo: a resposta não muda (sem enumeração);
            # o código anterior continua valendo.
            pass


def confirmar_verificacao(email, codigo, ip=None):
    """Confirma o e-mail com o código. O mesmo erro para conta inexistente e código
    errado (sem enumeração). Devolve o usuário atualizado."""
    limite_service.consumir('codigo_ip', ip)
    usuario = Usuario().buscar_por_email(normalizar_email(email))
    codigo_service.conferir(usuario['id'] if usuario else None, 'verificacao', codigo)
    Usuario().marcar_email_verificado(usuario['id'])
    return Usuario().buscar_por_id(usuario['id'])


# ── Recuperação de senha ────────────────────────────────────────────────

def solicitar_recuperacao(email, ip=None):
    """Envia o código de recuperação, se a conta existir. Resposta sempre genérica."""
    email = normalizar_email(email)
    exigir_email_valido(email)
    limite_service.consumir('recuperacao_ip', ip)
    limite_service.consumir('recuperacao_conta', email)
    usuario = Usuario().buscar_por_email(email)
    if usuario:
        try:
            _enviar(usuario, 'recuperacao', usuario['email'])
        except Exception:
            # Ex.: pediu de novo antes do intervalo mínimo. Não muda a resposta (sem enumeração).
            pass


def validar_recuperacao(email, codigo, ip=None):
    """Confere o código (sem consumir) para a interface liberar o passo da nova senha."""
    limite_service.consumir('codigo_ip', ip)
    usuario = Usuario().buscar_por_email(normalizar_email(email))
    codigo_service.conferir(usuario['id'] if usuario else None, 'recuperacao', codigo, consumir=False)


def redefinir_senha(email, codigo, senha, confirmacao, ip=None):
    """Nova senha a partir do código de recuperação. Consome o código, confirma o e-mail
    (quem recebeu o código é dono do endereço) e encerra todas as sessões da conta."""
    exigir_senha_valida(senha)
    if senha != confirmacao:
        raise ValidacaoError('A confirmação não confere com a nova senha.', details={'campo': 'password_confirm'})
    limite_service.consumir('codigo_ip', ip)
    usuario = Usuario().buscar_por_email(normalizar_email(email))
    codigo_service.conferir(usuario['id'] if usuario else None, 'recuperacao', codigo)
    modelo = Usuario()
    modelo.definir_senha(usuario['id'], senha)
    if not usuario.get('email_verificado'):
        modelo.marcar_email_verificado(usuario['id'])
    token_service.revogar_sessoes_do_usuario(usuario['id'])
    limite_service.limpar('login_conta', usuario['email'])


# ── Troca de senha e de e-mail (usuário logado) ─────────────────────────

def _exigir_senha_atual(usuario, senha_atual):
    """Contas com senha conhecida precisam confirmá-la (protege uma sessão esquecida aberta).
    Contas sem senha própria (criadas pelo Google) definem a primeira sem ela."""
    if not usuario.get('senha_definida'):
        return
    limite_service.exigir('senha_atual', usuario['id'])
    if not Usuario().senha_confere(usuario['id'], senha_atual):
        limite_service.registrar('senha_atual', usuario['id'])
        raise ValidacaoError('Senha atual incorreta.', code='INVALID_CURRENT_PASSWORD',
                             details={'campo': 'password_atual'})
    limite_service.limpar('senha_atual', usuario['id'])


def alterar_senha(usuario_id, senha_atual, nova, confirmacao, manter_sessao_api=None):
    """Troca a senha de quem está logado. Encerra as sessões do app nos OUTROS aparelhos
    (`manter_sessao_api` preserva a atual) e as do site abertas antes da troca."""
    usuario = Usuario().buscar_por_id(usuario_id)
    _exigir_senha_atual(usuario, senha_atual)
    exigir_senha_valida(nova)
    if nova != confirmacao:
        raise ValidacaoError('A confirmação não confere com a nova senha.', details={'campo': 'password_confirm'})
    Usuario().definir_senha(usuario_id, nova)
    token_service.revogar_sessoes_do_usuario(usuario_id, manter_familia=manter_sessao_api)
    return Usuario().buscar_por_id(usuario_id)


def solicitar_troca_email(usuario_id, novo_email, senha_atual):
    """Envia um código ao NOVO endereço; o e-mail só muda depois da confirmação."""
    usuario = Usuario().buscar_por_id(usuario_id)
    novo_email = normalizar_email(novo_email)
    exigir_email_valido(novo_email)
    if novo_email == normalizar_email(usuario['email']):
        raise ValidacaoError('Esse já é o e-mail da sua conta.', details={'campo': 'email'})
    _exigir_senha_atual(usuario, senha_atual)
    limite_service.consumir('troca_email', usuario_id)
    if Usuario().existe_conflito('', novo_email, ignorar_id=usuario_id):
        raise ConflitoError('Esse e-mail já está em uso por outra conta.')
    if not _enviar(usuario, 'troca_email', novo_email):
        raise ValidacaoError('Não foi possível enviar o código agora. Tente novamente em instantes.',
                             code='EMAIL_NOT_SENT')


def confirmar_troca_email(usuario_id, codigo, ip=None):
    limite_service.consumir('codigo_ip', ip)
    registro = codigo_service.conferir(usuario_id, 'troca_email', codigo)
    novo = registro['email_destino']
    if Usuario().existe_conflito('', novo, ignorar_id=usuario_id):  # alguém pegou o e-mail nesse meio-tempo
        raise ConflitoError('Esse e-mail já está em uso por outra conta.')
    Usuario().trocar_email(usuario_id, novo)
    return Usuario().buscar_por_id(usuario_id)
