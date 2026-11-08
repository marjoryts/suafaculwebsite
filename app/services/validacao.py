"""Validações de entrada da conta (formato de e-mail e política de senha), usadas no
cadastro, na troca e na recuperação de senha — no site e no app."""
import re

from app.services.erros import ValidacaoError

SENHA_MINIMA = 8
SENHA_MAXIMA = 128  # limite também protege o hash (scrypt) de entradas gigantes
EMAIL_MAXIMO = 254
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')

MENSAGEM_SENHA = f'A senha deve ter pelo menos {SENHA_MINIMA} caracteres, com letras e números.'


def exigir_email_valido(email):
    email = (email or '').strip()
    if len(email) > EMAIL_MAXIMO or not _EMAIL_RE.match(email):
        raise ValidacaoError('Formato de e-mail inválido.', details={'campo': 'email'})


def exigir_senha_valida(senha):
    """Política: 8 a 128 caracteres, com pelo menos uma letra e um número. Vale para senhas
    NOVAS; contas antigas com senhas menores continuam entrando e são convidadas a trocar."""
    senha = senha or ''
    if (len(senha) < SENHA_MINIMA or len(senha) > SENHA_MAXIMA
            or not re.search(r'[A-Za-zÀ-ÿ]', senha) or not re.search(r'\d', senha)):
        raise ValidacaoError(MENSAGEM_SENHA, details={'campo': 'password'})
