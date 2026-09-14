"""
Login com Google (OpenID Connect) via Authlib.

Configuração necessária (ver .env.example):
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_CALLBACK_URL   (ex.: http://localhost:5000/auth/google/callback)

Se as credenciais não estiverem configuradas, o app continua funcionando
normalmente (login local não é afetado) — apenas a rota /auth/google
retorna um erro amigável em vez de redirecionar para o Google.
"""
import os
from authlib.integrations.flask_client import OAuth

oauth = OAuth()
_google = None


def init_app(app):
    """Registra o provedor Google no OAuth do Authlib. Chamar uma vez, na
    criação da aplicação Flask."""
    global _google
    oauth.init_app(app)

    client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()

    if not client_id or not client_secret:
        app.logger.warning(
            "[oauth] GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET não configurados — "
            "login com Google ficará desabilitado até serem definidos no .env."
        )
        _google = None
        return

    _google = oauth.register(
        name='google',
        client_id=client_id,
        client_secret=client_secret,
        # Endpoints fixos do Google (em vez de server_metadata_url) para não
        # depender de uma chamada de descoberta OIDC a cada login — os
        # endpoints abaixo são estáveis e documentados publicamente por
        # https://developers.google.com/identity/protocols/oauth2/openid-connect
        access_token_url='https://oauth2.googleapis.com/token',
        authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
        jwks_uri='https://www.googleapis.com/oauth2/v3/certs',
        client_kwargs={'scope': 'openid email profile'},
    )


def is_configured():
    return _google is not None


def google_client():
    return _google
