"""Login com Google (OpenID Connect) via Authlib.

Sem GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET no ambiente, `is_configured()`
retorna False e as rotas /auth/google ficam desabilitadas — o resto do
site continua funcionando normalmente.
"""
import os
from authlib.integrations.flask_client import OAuth

oauth = OAuth()


def init_app(app):
    oauth.init_app(app)
    if is_configured():
        oauth.register(
            name='google',
            client_id=os.environ.get('GOOGLE_CLIENT_ID'),
            client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )


def is_configured():
    return bool(os.environ.get('GOOGLE_CLIENT_ID')) and bool(os.environ.get('GOOGLE_CLIENT_SECRET'))


def google_client():
    """Só chame depois de checar is_configured() — o cliente 'google' só é
    registrado no Authlib quando as credenciais existem."""
    return oauth.google
