"""Login com Google (OAuth/OIDC). A validação do token é sempre do backend."""
import os

from flask import Blueprint, current_app, redirect, request, session, url_for

from app.security import destino_seguro, login_usuario_na_sessao
from app.services import google_service, oauth_service
from app.services.erros import PermissaoNegadaError

bp = Blueprint('auth', __name__)


def _erro(codigo):
    return redirect(url_for('pages.login', oauth_error=codigo))


def _redirect_pos_login():
    """Volta para a página que pediu o login (?next=, só caminhos internos) ou o dashboard."""
    return redirect(destino_seguro(session.pop('login_next', None)) or url_for('pages.dashboard'))


@bp.route('/auth/google')
def auth_google():
    destino = destino_seguro(request.args.get('next'))
    if destino:
        session['login_next'] = destino
    if not oauth_service.is_configured():
        current_app.logger.error("[auth] Tentativa de login com Google sem GOOGLE_CLIENT_ID/SECRET configurados.")
        return _erro('nao_configurado')
    redirect_uri = os.environ.get('GOOGLE_CALLBACK_URL') or url_for('auth.auth_google_callback', _external=True)
    try:
        return oauth_service.google_client().authorize_redirect(redirect_uri)
    except Exception:
        current_app.logger.exception("[auth] Falha ao iniciar redirecionamento para o Google")
        return _erro('comunicacao')


@bp.route('/auth/google/callback')
def auth_google_callback():
    log = current_app.logger
    if not oauth_service.is_configured():
        return _erro('nao_configurado')

    # Usuário cancelou o consentimento no Google (?error=access_denied&...)
    erro_google = request.args.get('error')
    if erro_google:
        log.info("[auth] Login com Google cancelado/negado: %s", erro_google)
        return _erro('cancelado')

    google = oauth_service.google_client()
    try:
        token = google.authorize_access_token()
    except Exception as e:
        # Cobre: state/CSRF inválido (ex.: sessão expirou entre o redirect e
        # o callback), falha de rede com o Google, resposta inesperada etc.
        log.warning("[auth] Falha ao trocar código por token com o Google: %s", e)
        msg = 'sessao_expirada' if 'state' in str(e).lower() or 'csrf' in str(e).lower() else 'comunicacao'
        return _erro(msg)

    try:
        userinfo = token.get('userinfo') or google.parse_id_token(token)
    except Exception:
        log.exception("[auth] Falha ao validar id_token do Google")
        return _erro('token_invalido')

    if not userinfo or not userinfo.get('email'):
        log.warning("[auth] Resposta do Google sem e-mail utilizável")
        return _erro('sem_email')

    # Mesma regra de conta do app (vincular por google_id, por e-mail verificado ou criar).
    try:
        usuario = google_service.entrar_com_claims(userinfo)
    except PermissaoNegadaError:
        log.warning("[auth] E-mail do Google não verificado; conta não vinculada")
        return _erro('email_nao_verificado')
    except Exception:
        log.exception("[auth] Falha ao entrar com Google")
        return _erro('erro_interno')
    login_usuario_na_sessao(usuario)
    return _redirect_pos_login()
