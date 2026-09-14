"""
Automação diária: roda uma vez por dia (via APScheduler, dentro do próprio
processo Flask) a validação de vestibulares — sem depender de nenhum
usuário estar com o site aberto, e sem usar setInterval() no frontend.

Cada execução:
  - Chama vestibular_service.validar_vestibulares(aplicar=True), que já
    trata cada vestibular individualmente (uma instituição com dado
    inválido não interrompe as demais — ver vestibular_service.py).
  - Grava um resumo em `automacao_logs` (tabela criada no init_db) para
    auditoria: quando rodou, quantos ficaram ativos/encerrados/inválidos,
    e o erro completo caso a execução falhe.

Para trocar o horário, ajuste AUTOMACAO_HORA/AUTOMACAO_MINUTO (ou defina
as variáveis de ambiente VESTIBULARES_CRON_HORA / VESTIBULARES_CRON_MINUTO).
"""
import os
import sys
import json
import logging
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection

logger = logging.getLogger('suafacul.scheduler')

_scheduler = None


def _registrar_log(tipo, sucesso, resumo=None, erro=None):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO automacao_logs (tipo, sucesso, resumo, erro) VALUES (?,?,?,?)",
            (tipo, 1 if sucesso else 0, json.dumps(resumo, ensure_ascii=False) if resumo else None, erro)
        )
        conn.commit()
        conn.close()
    except Exception:
        # Se nem o log puder ser gravado, ao menos registra no log de aplicação.
        logger.exception("[scheduler] Falha ao gravar log da automação em automacao_logs")


def rodar_validacao_vestibulares_diaria():
    """Job diário. Nunca deixa uma exceção "matar" o scheduler — registra o
    erro e segue (o scheduler continua agendado para o próximo dia)."""
    from app.services import vestibular_service
    logger.info("[scheduler] Iniciando validação diária de vestibulares...")
    try:
        resultado = vestibular_service.validar_vestibulares(aplicar=True)
        _registrar_log('validacao_vestibulares', sucesso=True, resumo=resultado.get('resumo'))
        logger.info("[scheduler] Validação diária concluída: %s", resultado.get('resumo'))
    except Exception as e:
        logger.exception("[scheduler] Falha na validação diária de vestibulares")
        _registrar_log('validacao_vestibulares', sucesso=False, erro=f"{e}\n{traceback.format_exc()}")


def start(app):
    """Inicia o BackgroundScheduler uma única vez por processo."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        app.logger.warning(
            "[scheduler] APScheduler não instalado — a automação diária de "
            "vestibulares não vai rodar. `pip install apscheduler`."
        )
        return None

    hora = int(os.environ.get('VESTIBULARES_CRON_HORA', 3))
    minuto = int(os.environ.get('VESTIBULARES_CRON_MINUTO', 0))

    _scheduler = BackgroundScheduler(daemon=True, timezone='America/Sao_Paulo')
    _scheduler.add_job(
        rodar_validacao_vestibulares_diaria,
        trigger='cron',
        hour=hora,
        minute=minuto,
        id='validacao_vestibulares_diaria',
        replace_existing=True,
        misfire_grace_time=3600,  # se o processo estava fora do ar no horário, roda em até 1h
    )
    _scheduler.start()
    app.logger.info(f"[scheduler] Automação diária de vestibulares agendada para {hora:02d}:{minuto:02d} (America/Sao_Paulo).")
    return _scheduler


def shutdown():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
