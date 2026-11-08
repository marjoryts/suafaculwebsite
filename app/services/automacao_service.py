"""Execução das automações agendadas (Vercel Cron) e manuais (CLI).

Premissas da Vercel (docs, 2026-08/09): o Cron chama por GET, é "best effort" —
pode PERDER e pode DUPLICAR uma execução —, não repete se falhar e pode disparar
uma segunda instância enquanto a primeira ainda roda. Por isso todo job aqui é:

  * idempotente e "reconciliador": recalcula/apaga o que estiver pendente, então
    uma execução perdida é compensada pela seguinte e uma duplicada é inofensiva;
  * protegido por trava no banco (uma execução 'executando' por tipo);
  * protegido contra duplicata próxima (não roda de novo dentro de `intervalo_minimo`);
  * registrado em automacao_logs com `execucao_id`, origem, estado, duração e erro.

Nada aqui conhece HTTP: a rota de Cron e a CLI são só "cascas" que chamam executar().
"""
import logging
import time
import traceback
import uuid
from collections import namedtuple
from datetime import datetime, timedelta, timezone

from app.models.automacao_log import AutomacaoLog
from app.models.refresh_token import RefreshToken
from app.services import vestibular_service
from app.services.erros import NaoEncontradoError

logger = logging.getLogger('suafacul.automacao')

# Trava presa por mais tempo que isto é considerada de um processo que morreu
# (funções da Vercel têm limite de duração menor que isso).
TRAVA_EXPIRA_MINUTOS = 15
# Refresh tokens expirados há mais que isto podem ser apagados.
RETENCAO_REFRESH_TOKENS_DIAS = 7

Job = namedtuple('Job', 'tipo descricao funcao intervalo_minimo_minutos')


def _agora():
    """Relógio único do módulo (os testes o substituem)."""
    return datetime.now(timezone.utc)


def _fmt(momento):
    return momento.strftime('%Y-%m-%d %H:%M:%S')  # mesmo formato de CURRENT_TIMESTAMP (UTC)


# ── Jobs ────────────────────────────────────────────────────────────────

def _validar_vestibulares():
    """Recalcula status (ativo/encerrado/data inválida) e vínculo com faculdades
    de TODOS os vestibulares. Idempotente por construção: o resultado depende só
    do estado atual e da data de hoje."""
    resultado = vestibular_service.validar_vestibulares(aplicar=True)
    return resultado['resumo']


def _limpar_refresh_tokens():
    """Apaga refresh tokens expirados há mais de RETENCAO_REFRESH_TOKENS_DIAS dias e, no
    mesmo job (o plano Hobby da Vercel limita a 2 crons), tentativas de acesso com mais
    de 1 dia e códigos de e-mail com mais de 7 dias (já expirados há muito)."""
    from app.services import codigo_service, limite_service
    limite = _fmt(_agora() - timedelta(days=RETENCAO_REFRESH_TOKENS_DIAS))
    return {'removidos': RefreshToken().remover_expirados(limite), 'expirados_antes_de': limite,
            'tentativas_removidas': limite_service.remover_antigas(dias=1),
            'codigos_removidos': codigo_service.remover_antigos(dias=7)}


# Nome na URL/CLI -> job. Manter em sincronia com "crons" do vercel.json (há teste).
JOBS = {
    'validacao-vestibulares': Job('validacao_vestibulares', 'Valida datas e vínculos dos vestibulares',
                                  _validar_vestibulares, 30),
    'limpeza-refresh-tokens': Job('limpeza_refresh_tokens', 'Remove refresh tokens expirados',
                                  _limpar_refresh_tokens, 30),
}


# ── Execução ────────────────────────────────────────────────────────────

def executar(nome, origem, forcar=False):
    """Executa o job `nome` com trava, anti-duplicação e registro.

    origem: 'cron' | 'cli' | 'manual'. `forcar=True` ignora só a janela anti-duplicata
    (a trava contra execução concorrente continua valendo).
    Devolve {'execucao_id', 'job', 'status', 'duracao_ms', 'resumo'?, 'motivo'?} com
    status 'sucesso' | 'falha' | 'ignorada'. Levanta NaoEncontradoError se o job não existe.
    """
    job = JOBS.get(nome)
    if job is None:
        raise NaoEncontradoError('Automação não encontrada.', details={'jobs': sorted(JOBS)})

    log = AutomacaoLog()
    execucao_id = uuid.uuid4().hex
    inicio = _agora()

    # 1) Duplicata próxima (Cron pode entregar o mesmo agendamento mais de uma vez).
    ultimo = log.ultimo_sucesso_em(job.tipo)
    if not forcar and ultimo and ultimo >= _fmt(inicio - timedelta(minutes=job.intervalo_minimo_minutos)):
        return _ignorar(log, job, nome, execucao_id, origem, inicio,
                        f'Executada com sucesso há menos de {job.intervalo_minimo_minutos} min.')

    # 2) Trava contra execução concorrente.
    if not log.iniciar(job.tipo, execucao_id, origem, _fmt(inicio),
                       _fmt(inicio - timedelta(minutes=TRAVA_EXPIRA_MINUTOS))):
        return _ignorar(log, job, nome, execucao_id, origem, inicio, 'Já existe uma execução em andamento.')

    logger.info("[automacao] inicio job=%s execucao=%s origem=%s", nome, execucao_id, origem)
    cronometro = time.monotonic()
    try:
        resumo = job.funcao()
        status, erro = 'sucesso', None
    except Exception as e:
        resumo, status = None, 'falha'
        erro = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"[:4000]
        logger.exception("[automacao] falha job=%s execucao=%s", nome, execucao_id)

    duracao_ms = int((time.monotonic() - cronometro) * 1000)
    log.finalizar(execucao_id, status, _fmt(_agora()), duracao_ms, resumo=resumo, erro=erro)
    logger.info("[automacao] fim job=%s execucao=%s status=%s duracao_ms=%d", nome, execucao_id, status, duracao_ms)
    resposta = {'execucao_id': execucao_id, 'job': nome, 'status': status, 'duracao_ms': duracao_ms}
    if resumo is not None:
        resposta['resumo'] = resumo
    return resposta


def _ignorar(log, job, nome, execucao_id, origem, inicio, motivo):
    log.registrar_ignorada(job.tipo, execucao_id, origem, _fmt(inicio), motivo)
    logger.info("[automacao] ignorada job=%s execucao=%s motivo=%s", nome, execucao_id, motivo)
    return {'execucao_id': execucao_id, 'job': nome, 'status': 'ignorada', 'duracao_ms': 0, 'motivo': motivo}
