"""Configuração por ambiente, lida das variáveis de ambiente (12-factor).

Nada aqui tem efeito colateral: só lê `os.environ` e devolve um dict.
Segredos nunca têm valor padrão no código.
"""
import os
from datetime import timedelta

# Chave que já esteve hardcoded no código-fonte (portanto pública): rejeitada.
CHAVE_LEGADA_PUBLICA = 'suafacul_secret_key_change_in_production'


def _env_bool(nome, padrao):
    valor = os.environ.get(nome, '').strip().lower()
    if not valor:
        return padrao
    return valor in ('1', 'true', 'yes', 'on')


def load_config(overrides=None):
    """Monta a configuração do Flask a partir do ambiente.

    Levanta RuntimeError se faltar SECRET_KEY fora do modo debug — o app
    não deve subir com sessões assináveis por qualquer pessoa.
    """
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'

    chave = os.environ.get('FLASK_SECRET_KEY', '').strip()
    chave_efemera = False
    if not chave or chave == CHAVE_LEGADA_PUBLICA:
        if not debug:
            raise RuntimeError(
                "FLASK_SECRET_KEY ausente ou insegura. Defina uma chave forte no "
                "ambiente (python -c \"import secrets; print(secrets.token_hex(32))\"). "
                "Para desenvolvimento local, use FLASK_DEBUG=1 (gera chave efêmera)."
            )
        chave = os.urandom(32).hex()
        chave_efemera = True

    config = {
        'DEBUG': debug,
        'SECRET_KEY': chave,
        'SECRET_KEY_EFEMERA': chave_efemera,
        'PERMANENT_SESSION_LIFETIME': timedelta(days=7),
        # Tokens da API v1 (Mobile). Prazos definidos pelo proprietário do projeto.
        'ACCESS_TOKEN_TTL_SECONDS': 15 * 60,
        'REFRESH_TOKEN_TTL_DAYS': 30,
        # Cookie de sessão: inacessível ao JS, não enviado em requisições
        # cross-site (mitiga CSRF) e, fora do debug, só trafega por HTTPS.
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'SESSION_COOKIE_SECURE': _env_bool('SESSION_COOKIE_SECURE', not debug),
    }
    if overrides:
        config.update(overrides)
    return config
