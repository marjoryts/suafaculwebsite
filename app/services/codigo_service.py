"""Códigos de 5 dígitos enviados por e-mail (verificação, recuperação, troca de e-mail).

- Gerados com `secrets` (criptograficamente seguros).
- Guardados só como HMAC-SHA256 com a chave secreta do servidor: um código de
  5 dígitos com hash simples seria quebrado por força bruta em segundos; com a
  chave, quem lê o banco não consegue.
- Validade curta, no máximo MAX_TENTATIVAS erros por código, uso único, e um
  novo envio invalida o anterior (com intervalo mínimo entre envios).
- Nunca aparecem em logs nem nas respostas da API.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app

from app.models.codigo_email import CodigoEmail
from app.services.erros import LimiteExcedidoError, ValidacaoError

DIGITOS = 5  # como no Figma ("Digite os 5 códigos")
VALIDADE_MINUTOS = {'verificacao': 30, 'recuperacao': 15, 'troca_email': 30}
MAX_TENTATIVAS = 5
INTERVALO_REENVIO_SEGUNDOS = 60


def _agora():
    """Relógio único do módulo (os testes o substituem para simular o tempo)."""
    return datetime.now(timezone.utc)


def _fmt(momento):
    return momento.strftime('%Y-%m-%d %H:%M:%S')


def _ler(texto):
    return datetime.strptime(texto, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)


def _hmac(codigo, usuario_id, finalidade):
    chave = (current_app.secret_key or '').encode()
    mensagem = f'{finalidade}:{usuario_id}:{codigo}'.encode()
    return hmac.new(chave, mensagem, hashlib.sha256).hexdigest()


def gerar(usuario_id, finalidade, email_destino):
    """Cria um código novo (invalida o anterior) e o devolve para ser enviado por e-mail."""
    ultimo = CodigoEmail().ultimo_envio(usuario_id, finalidade)
    if ultimo:
        decorrido = (_agora() - _ler(ultimo)).total_seconds()
        if decorrido < INTERVALO_REENVIO_SEGUNDOS:
            espera = int(INTERVALO_REENVIO_SEGUNDOS - decorrido) + 1
            raise LimiteExcedidoError(f'Aguarde {espera} segundos para pedir um novo código.', retry_after=espera,
                                      code='RESEND_TOO_SOON')
    codigo = f'{secrets.randbelow(10 ** DIGITOS):0{DIGITOS}d}'
    expira = _fmt(_agora() + timedelta(minutes=VALIDADE_MINUTOS[finalidade]))
    CodigoEmail().criar(usuario_id, finalidade, _hmac(codigo, usuario_id, finalidade), email_destino, expira)
    return codigo


def conferir(usuario_id, finalidade, codigo, consumir=True):
    """Valida o código informado. Devolve o registro (com `email_destino`).

    Erros (ValidacaoError 422 com códigos distintos para a interface):
    INVALID_CODE, CODE_EXPIRED; TOO_MANY_ATTEMPTS (429) depois de MAX_TENTATIVAS erros.
    """
    codigo = str(codigo or '').strip()
    modelo = CodigoEmail()
    registro = modelo.ativo(usuario_id, finalidade) if usuario_id else None
    if registro is None:
        raise ValidacaoError('Código inválido. Peça um novo código.', code='INVALID_CODE')
    if _agora() > _ler(registro['expira_em']):
        raise ValidacaoError('Este código expirou. Peça um novo código.', code='CODE_EXPIRED')
    if registro['tentativas'] >= MAX_TENTATIVAS:
        modelo.consumir(registro['id'])  # esgotado: não vale mais
        raise LimiteExcedidoError('Muitas tentativas com este código. Peça um novo código.',
                                  retry_after=INTERVALO_REENVIO_SEGUNDOS, code='TOO_MANY_ATTEMPTS')
    certo = len(codigo) == DIGITOS and codigo.isdigit() and hmac.compare_digest(
        _hmac(codigo, usuario_id, finalidade), registro['codigo_hash'])
    if not certo:
        modelo.registrar_tentativa(registro['id'])
        restantes = MAX_TENTATIVAS - registro['tentativas'] - 1
        if restantes <= 0:
            modelo.consumir(registro['id'])
            raise LimiteExcedidoError('Muitas tentativas com este código. Peça um novo código.',
                                      retry_after=INTERVALO_REENVIO_SEGUNDOS, code='TOO_MANY_ATTEMPTS')
        raise ValidacaoError('Código incorreto.', code='INVALID_CODE', details={'tentativas_restantes': restantes})
    if consumir and not modelo.consumir(registro['id']):
        raise ValidacaoError('Este código já foi usado. Peça um novo código.', code='INVALID_CODE')
    return registro


def remover_antigos(dias=7):
    return CodigoEmail().remover_antigos(_fmt(_agora() - timedelta(days=dias)))
