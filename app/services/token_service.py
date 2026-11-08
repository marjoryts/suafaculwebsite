"""Sessões do Mobile: access token curto + refresh token rotativo.

Independente do método de login: quem autentica o usuário (hoje e-mail/senha;
no futuro o Google, validado no backend) chama `iniciar_sessao(usuario_id)` e
recebe os tokens. Nada aqui conhece HTTP.

Access token (15 min)   Assinado (HMAC via itsdangerous, com a SECRET_KEY) e
                        stateless: {uid, fam, exp}. A cada uso a camada de API
                        confere no banco se a sessão (família) não foi revogada,
                        então logout / reuso cortam o acesso na hora.
Refresh token (30 dias) Opaco (48 bytes aleatórios); só o SHA-256 vai ao banco.
                        Uso único: cada renovação invalida o token usado e emite
                        outro da mesma família. Reapresentar um token já usado é
                        tratado como comprometimento: a família inteira é revogada.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app
from itsdangerous import BadSignature, URLSafeSerializer

from app.models.refresh_token import RefreshToken
from app.services.erros import NaoAutenticadoError

_SAL_ACCESS_TOKEN = 'suafacul.access-token.v1'
_MAX_DISPOSITIVO = 200


def _agora():
    """Relógio único do módulo (os testes o substituem para simular o tempo)."""
    return datetime.now(timezone.utc)


def _fmt(momento):
    return momento.strftime('%Y-%m-%d %H:%M:%S')  # mesmo formato de CURRENT_TIMESTAMP (UTC)


def _hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _assinador():
    return URLSafeSerializer(current_app.config['SECRET_KEY'], salt=_SAL_ACCESS_TOKEN)


def _ttl_access():
    return int(current_app.config['ACCESS_TOKEN_TTL_SECONDS'])


def _ttl_refresh():
    return timedelta(days=int(current_app.config['REFRESH_TOKEN_TTL_DAYS']))


def _montar_resposta(usuario_id, familia_id, refresh_token):
    expira = int(_agora().timestamp()) + _ttl_access()
    access = _assinador().dumps({'uid': usuario_id, 'fam': familia_id, 'exp': expira})
    return {
        'token_type': 'Bearer',
        'access_token': access,
        'expires_in': _ttl_access(),
        'refresh_token': refresh_token,
        'refresh_expires_in': int(_ttl_refresh().total_seconds()),
    }


def _novo_refresh(usuario_id, familia_id, dispositivo):
    token = secrets.token_urlsafe(48)
    expira = _fmt(_agora() + _ttl_refresh())
    dados = {'familia_id': familia_id, 'usuario_id': usuario_id, 'token_hash': _hash(token),
             'dispositivo': (dispositivo or '')[:_MAX_DISPOSITIVO] or None, 'expira_em': expira}
    return token, dados


# ── API do service ──────────────────────────────────────────────────────

def iniciar_sessao(usuario_id, dispositivo=None):
    """Abre uma sessão nova (nova família) para um usuário JÁ autenticado."""
    familia_id = uuid.uuid4().hex
    token, d = _novo_refresh(usuario_id, familia_id, dispositivo)
    RefreshToken().criar(d['familia_id'], usuario_id, d['token_hash'], d['expira_em'], d['dispositivo'])
    return _montar_resposta(usuario_id, familia_id, token)


def renovar(refresh_token, dispositivo=None):
    """Troca um refresh token válido por um novo par de tokens (rotação)."""
    if not isinstance(refresh_token, str) or not refresh_token:
        raise NaoAutenticadoError('Refresh token inválido.', code='INVALID_REFRESH_TOKEN')
    repo = RefreshToken()
    linha = repo.buscar_por_hash(_hash(refresh_token))
    if linha is None or linha['revogado_em']:
        raise NaoAutenticadoError('Refresh token inválido ou sessão encerrada.', code='INVALID_REFRESH_TOKEN')
    if linha['usado_em']:
        _reutilizacao(linha)
    if linha['expira_em'] <= _fmt(_agora()):
        raise NaoAutenticadoError('Refresh token expirado. Faça login novamente.', code='REFRESH_TOKEN_EXPIRED')

    token, novo = _novo_refresh(linha['usuario_id'], linha['familia_id'], dispositivo or linha['dispositivo'])
    if not repo.rotacionar(linha['id'], novo, _fmt(_agora())):
        _reutilizacao(linha)  # perdeu a corrida: alguém usou este mesmo token antes
    return _montar_resposta(linha['usuario_id'], linha['familia_id'], token)


def _reutilizacao(linha):
    """Token já usado foi reapresentado: assume comprometimento e revoga a sessão inteira."""
    RefreshToken().revogar_familia(linha['familia_id'], _fmt(_agora()), 'reuso_de_refresh_token')
    current_app.logger.warning(
        "[auth] Reutilização de refresh token detectada; sessão revogada (usuario_id=%s, familia=%s).",
        linha['usuario_id'], linha['familia_id'])
    raise NaoAutenticadoError('Sessão encerrada por segurança. Faça login novamente.',
                              code='REFRESH_TOKEN_REUSED')


def encerrar_sessao(refresh_token):
    """Logout: revoga a sessão do refresh token informado. Idempotente e sem
    revelar se o token existia."""
    if not isinstance(refresh_token, str) or not refresh_token:
        return
    linha = RefreshToken().buscar_por_hash(_hash(refresh_token))
    if linha:
        RefreshToken().revogar_familia(linha['familia_id'], _fmt(_agora()), 'logout')


def revogar_sessoes_do_usuario(usuario_id, manter_familia=None):
    """Encerra todas as sessões do usuário (ex.: troca de senha), opcionalmente
    preservando a atual."""
    RefreshToken().revogar_do_usuario(usuario_id, _fmt(_agora()), 'troca_de_senha', exceto_familia=manter_familia)


def validar_access_token(token):
    """Devolve {'uid', 'fam'} de um access token válido; senão NaoAutenticadoError
    (TOKEN_EXPIRED quando só expirou — o cliente deve chamar /auth/refresh)."""
    try:
        dados = _assinador().loads(token)
        usuario_id, familia_id, expira = dados['uid'], dados['fam'], int(dados['exp'])
    except (BadSignature, KeyError, TypeError, ValueError):
        raise NaoAutenticadoError('Access token inválido.', code='INVALID_TOKEN')
    if expira <= int(_agora().timestamp()):
        raise NaoAutenticadoError('Access token expirado.', code='TOKEN_EXPIRED')
    if not RefreshToken().familia_ativa(familia_id):
        raise NaoAutenticadoError('Sessão encerrada.', code='INVALID_TOKEN')
    return {'uid': usuario_id, 'fam': familia_id}
