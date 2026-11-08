"""Limites de tentativas e requisições (força bruta, abuso, enumeração).

Janela deslizante por chave, guardada no banco (tentativas_acesso): funciona
com vários processos/instâncias que dividem o mesmo banco, sem Redis. A chave
é um hash (tipo + valor), então a tabela não guarda e-mails nem IPs em claro.

Os mesmos limites valem para o site e para o app (as duas interfaces chamam
os mesmos serviços).
"""
import hashlib
from datetime import datetime, timedelta, timezone

from app.models.tentativa_acesso import TentativaAcesso
from app.services.erros import LimiteExcedidoError

# tipo -> (máximo de tentativas, janela em minutos)
LIMITES = {
    'login_conta': (5, 15),         # senha errada para a mesma conta
    'login_ip': (30, 15),           # senha errada a partir do mesmo IP (várias contas)
    'cadastro_ip': (10, 60),
    'google_ip': (30, 15),
    'verificacao_envio': (5, 60),   # pedidos de código de verificação por e-mail
    'recuperacao_conta': (3, 60),   # pedidos de recuperação para o mesmo e-mail
    'recuperacao_ip': (10, 60),
    'codigo_ip': (30, 15),          # tentativas de confirmar códigos a partir do mesmo IP
    'senha_atual': (5, 15),         # senha atual errada ao trocar senha/e-mail logado
    'troca_email': (5, 60),
}

MENSAGEM = 'Muitas tentativas. Aguarde alguns minutos e tente novamente.'


def _agora():
    """Relógio único do módulo (os testes o substituem para simular o tempo)."""
    return datetime.now(timezone.utc)


def _fmt(momento):
    return momento.strftime('%Y-%m-%d %H:%M:%S')  # mesmo formato de CURRENT_TIMESTAMP (UTC)


def _chave(tipo, valor):
    bruto = f'{tipo}:{str(valor or "").strip().lower()}'
    return f'{tipo}:{hashlib.sha256(bruto.encode()).hexdigest()}'


def _inicio_janela(tipo):
    return _fmt(_agora() - timedelta(minutes=LIMITES[tipo][1]))


def exigir(tipo, valor):
    """Levanta LimiteExcedidoError se a chave já atingiu o limite na janela."""
    if valor in (None, ''):
        return
    maximo, minutos = LIMITES[tipo]
    chave, desde = _chave(tipo, valor), _inicio_janela(tipo)
    modelo = TentativaAcesso()
    if modelo.contar_desde(chave, desde) >= maximo:
        mais_antiga = modelo.mais_antiga_desde(chave, desde)
        espera = 60
        if mais_antiga:
            libera = datetime.strptime(mais_antiga, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc) + timedelta(minutes=minutos)
            espera = max(1, int((libera - _agora()).total_seconds()))
        raise LimiteExcedidoError(MENSAGEM, retry_after=espera)


def registrar(tipo, valor):
    if valor in (None, ''):
        return
    TentativaAcesso().registrar(_chave(tipo, valor), _fmt(_agora()))


def consumir(tipo, valor):
    """Confere o limite e já conta esta tentativa (para pedidos que sempre contam)."""
    exigir(tipo, valor)
    registrar(tipo, valor)


def limpar(tipo, valor):
    """Zera a contagem (ex.: login certo apaga as falhas daquela conta)."""
    if valor not in (None, ''):
        TentativaAcesso().limpar(_chave(tipo, valor))


def remover_antigas(dias=1):
    return TentativaAcesso().remover_antigas(_fmt(_agora() - timedelta(days=dias)))
