"""Etapa 6: automações via Vercel Cron — segurança, trava, duplicata, falha, limpeza."""
import json
import os
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.automacao_log import AutomacaoLog
from app.services import automacao_service, token_service, vestibular_service
from config.database import get_connection
from conftest import PROJECT_ROOT

SEGREDO = 'segredo-de-cron-com-32-caracteres!'
AUTH = {'Authorization': f'Bearer {SEGREDO}'}
URL_VALIDACAO = '/api/cron/validacao-vestibulares'
URL_LIMPEZA = '/api/cron/limpeza-refresh-tokens'


class Relogio:
    def __init__(self, monkeypatch):
        self.deslocamento = timedelta(0)
        monkeypatch.setattr(automacao_service, '_agora', lambda: datetime.now(timezone.utc) + self.deslocamento)

    def avancar(self, **kwargs):
        self.deslocamento += timedelta(**kwargs)


@pytest.fixture()
def relogio(monkeypatch):
    return Relogio(monkeypatch)


@pytest.fixture()
def cron(app, monkeypatch):
    """Client com CRON_SECRET configurado."""
    monkeypatch.setenv('CRON_SECRET', SEGREDO)
    return app.app.test_client()


def _logs(tipo=None):
    conn = get_connection()
    sql = "SELECT * FROM automacao_logs" + (" WHERE tipo=?" if tipo else "") + " ORDER BY id"
    linhas = [dict(r) for r in conn.execute(sql, (tipo,) if tipo else ())]
    conn.close()
    return linhas


def _vestibular(app, nome='Vest Cron', dias=10):
    return app.Vestibular().criar({
        'nome': nome, 'instituicao': 'Inst', 'tipo_instituicao': 'Pública', 'cidade': 'X', 'regiao': 'Sul',
        'periodo_inscricao': '', 'data_prova': (date.today() + timedelta(days=dias)).isoformat(),
        'descricao': '', 'link_edital': ''})['id']


def _status_vestibular(app, vid):
    return app.Vestibular().buscar_por_id(vid)['status_validacao']


# ── Segurança do endpoint ───────────────────────────────────────────────

def test_sem_cron_secret_os_endpoints_ficam_desligados(app, client, monkeypatch):
    monkeypatch.delenv('CRON_SECRET', raising=False)
    r = client.get(URL_VALIDACAO, headers=AUTH)
    assert r.status_code == 503 and r.get_json()['error']['code'] == 'CRON_DISABLED'
    assert _logs() == []  # nada foi executado


def test_segredo_curto_demais_desliga_o_cron(app, client, monkeypatch):
    monkeypatch.setenv('CRON_SECRET', 'curto')
    assert client.get(URL_VALIDACAO, headers={'Authorization': 'Bearer curto'}).status_code == 503


@pytest.mark.parametrize('cabecalhos', [
    {}, {'Authorization': 'Bearer errado'}, {'Authorization': SEGREDO}, {'Authorization': f'bearer {SEGREDO}'},
    {'Authorization': f'Bearer {SEGREDO} '}, {'Authorization': 'Basic abc'},
])
def test_requisicao_sem_credencial_valida_e_negada_e_nada_executa(app, cron, cabecalhos):
    r = cron.get(URL_VALIDACAO, headers=cabecalhos)
    assert r.status_code == 401 and r.get_json()['error']['code'] == 'UNAUTHENTICATED'
    assert _logs() == []


def test_jobs_desconhecidos_nao_sao_revelados_sem_autenticacao(cron):
    assert cron.get('/api/cron/qualquer-coisa').status_code == 401
    r = cron.get('/api/cron/qualquer-coisa', headers=AUTH)
    assert r.status_code == 404 and 'validacao-vestibulares' in r.get_json()['error']['details']['jobs']


def test_somente_get_e_resposta_nunca_e_cacheada(cron):
    assert cron.post(URL_VALIDACAO, headers=AUTH).status_code == 405
    r = cron.get(URL_VALIDACAO, headers=AUTH)
    assert r.headers['Cache-Control'] == 'no-store'
    assert cron.get(URL_VALIDACAO).headers['Cache-Control'] == 'no-store'


def test_cookie_de_admin_nao_substitui_o_segredo(app, cron, admin_client):
    assert admin_client.get(URL_VALIDACAO).status_code in (401, 503)


# ── Execução, identificação e registro ──────────────────────────────────

def test_execucao_e_identificada_e_registrada(app, cron):
    vid = _vestibular(app)
    r = cron.get(URL_VALIDACAO, headers=AUTH)
    corpo = r.get_json()
    assert r.status_code == 200 and corpo['status'] == 'sucesso'
    assert re.fullmatch(r'[0-9a-f]{32}', corpo['execucao_id']) and isinstance(corpo['duracao_ms'], int)
    assert corpo['resumo']['aplicado'] is True
    assert _status_vestibular(app, vid) == 'ativo'

    log = _logs('validacao_vestibulares')[-1]
    assert log['execucao_id'] == corpo['execucao_id'] and log['status'] == 'sucesso' and log['sucesso'] == 1
    assert log['origem'] == 'cron' and log['iniciado_em'] and log['finalizado_em'] and log['duracao_ms'] is not None
    assert json.loads(log['resumo'])['aplicado'] is True


def test_admin_stats_mostra_as_execucoes(app, cron, admin_client):
    cron.get(URL_VALIDACAO, headers=AUTH)
    automacoes = admin_client.get('/api/admin/stats').get_json()['automacoes']
    assert automacoes[0]['tipo'] == 'validacao_vestibulares' and automacoes[0]['status'] == 'sucesso'
    assert automacoes[0]['execucao_id'] and automacoes[0]['sucesso'] is True


# ── Duplicata e reconciliação ───────────────────────────────────────────

def test_entrega_duplicada_do_cron_e_ignorada_e_registrada(app, cron):
    vid = _vestibular(app)
    primeira = cron.get(URL_VALIDACAO, headers=AUTH).get_json()
    conn = get_connection()  # simula estado alterado entre as duas entregas
    conn.execute("UPDATE vestibulares SET status_validacao='nao_validado' WHERE id=?", (vid,))
    conn.commit()
    conn.close()

    r = cron.get(URL_VALIDACAO, headers=AUTH)
    segunda = r.get_json()
    assert r.status_code == 200 and segunda['status'] == 'ignorada' and 'menos de 30 min' in segunda['motivo']
    assert segunda['execucao_id'] != primeira['execucao_id']
    assert _status_vestibular(app, vid) == 'nao_validado'  # a duplicata não reprocessou nada
    ignorada = _logs('validacao_vestibulares')[-1]
    assert ignorada['status'] == 'ignorada' and ignorada['sucesso'] == 1 and ignorada['origem'] == 'cron'


def test_proxima_execucao_agendada_reconcilia_o_que_ficou_pendente(app, cron, relogio):
    vid = _vestibular(app)
    cron.get(URL_VALIDACAO, headers=AUTH)
    conn = get_connection()
    conn.execute("UPDATE vestibulares SET status_validacao='nao_validado' WHERE id=?", (vid,))
    conn.commit()
    conn.close()
    relogio.avancar(hours=24)  # próximo dia: também cobre execução perdida (a de ontem foi a última)
    assert cron.get(URL_VALIDACAO, headers=AUTH).get_json()['status'] == 'sucesso'
    assert _status_vestibular(app, vid) == 'ativo'


def test_rodar_duas_vezes_produz_o_mesmo_estado(app, relogio):
    vid = _vestibular(app)
    automacao_service.executar('validacao-vestibulares', 'manual')
    antes = app.Vestibular().buscar_por_id(vid)
    relogio.avancar(hours=1)
    assert automacao_service.executar('validacao-vestibulares', 'manual')['status'] == 'sucesso'
    depois = app.Vestibular().buscar_por_id(vid)
    assert {k: v for k, v in antes.items() if k != 'ultima_validacao'} == \
           {k: v for k, v in depois.items() if k != 'ultima_validacao'}


# ── Trava contra execução concorrente ───────────────────────────────────

def test_indice_unico_impede_duas_execucoes_simultaneas_do_mesmo_tipo(app):
    log = AutomacaoLog()
    agora = '2026-01-01 00:00:00'
    assert log.iniciar('validacao_vestibulares', 'a' * 32, 'cron', agora, '2025-12-31 23:00:00') is True
    assert log.iniciar('validacao_vestibulares', 'b' * 32, 'cron', agora, '2025-12-31 23:00:00') is False
    assert log.iniciar('limpeza_refresh_tokens', 'c' * 32, 'cron', agora, '2025-12-31 23:00:00') is True  # outro tipo
    assert [l['status'] for l in _logs('validacao_vestibulares')] == ['executando']


def test_execucao_em_andamento_faz_a_nova_ser_ignorada(app, cron):
    vid = _vestibular(app)
    agora = automacao_service._fmt(automacao_service._agora())
    AutomacaoLog().iniciar('validacao_vestibulares', 'e' * 32, 'cron', agora, '2000-01-01 00:00:00')
    corpo = cron.get(URL_VALIDACAO, headers=AUTH).get_json()
    assert corpo['status'] == 'ignorada' and 'em andamento' in corpo['motivo']
    assert _status_vestibular(app, vid) == 'nao_validado'  # o job não rodou


def test_trava_de_processo_morto_expira_e_a_execucao_prossegue(app, cron):
    vid = _vestibular(app)
    velha = automacao_service._fmt(automacao_service._agora() - timedelta(minutes=20))
    AutomacaoLog().iniciar('validacao_vestibulares', 'd' * 32, 'cron', velha, '2000-01-01 00:00:00')
    assert cron.get(URL_VALIDACAO, headers=AUTH).get_json()['status'] == 'sucesso'
    presa = next(l for l in _logs() if l['execucao_id'] == 'd' * 32)
    assert presa['status'] == 'falha' and 'trava expirada' in presa['erro']
    assert _status_vestibular(app, vid) == 'ativo'


# ── Falhas ──────────────────────────────────────────────────────────────

def test_falha_do_job_vira_500_sem_vazar_detalhe_e_libera_a_trava(app, cron, monkeypatch):
    original = vestibular_service.validar_vestibulares

    def explode(aplicar=False):
        raise RuntimeError('senha=hunter2 conexão recusada')
    monkeypatch.setattr(vestibular_service, 'validar_vestibulares', explode)

    r = cron.get(URL_VALIDACAO, headers=AUTH)
    assert r.status_code == 500 and r.get_json()['status'] == 'falha'
    assert 'hunter2' not in r.get_data(as_text=True) and 'Traceback' not in r.get_data(as_text=True)

    log = _logs('validacao_vestibulares')[-1]
    assert log['status'] == 'falha' and log['sucesso'] == 0 and 'hunter2' in log['erro']  # detalhe só no banco
    assert log['finalizado_em'] and log['duracao_ms'] is not None
    assert not [l for l in _logs() if l['status'] == 'executando']  # trava liberada

    # a falha não impede a próxima execução (não houve sucesso recente)
    monkeypatch.setattr(vestibular_service, 'validar_vestibulares', original)
    assert cron.get(URL_VALIDACAO, headers=AUTH).get_json()['status'] == 'sucesso'


# ── Limpeza de refresh tokens ───────────────────────────────────────────

def _criar_sessoes(app, client_usuario):
    uid = app.Usuario().buscar_por_email('ana@x.com')['id']
    with app.app.app_context():
        return uid, [token_service.iniciar_sessao(uid) for _ in range(3)]


def test_limpeza_remove_apenas_expirados_ha_mais_de_7_dias(app, cron, client):
    client.post('/api/v1/auth/registrar', json={'nome_usuario': 'ana', 'email': 'ana@x.com', 'password': 'segredo1'})
    uid, sessoes = _criar_sessoes(app, client)
    agora = datetime.now(timezone.utc)
    conn = get_connection()
    ids = [r['id'] for r in conn.execute("SELECT id FROM refresh_tokens ORDER BY id")]
    fmt = lambda d: (agora - timedelta(days=d)).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("UPDATE refresh_tokens SET expira_em=? WHERE id=?", (fmt(8), ids[1]))  # expirou há 8 dias
    conn.execute("UPDATE refresh_tokens SET expira_em=? WHERE id=?", (fmt(1), ids[2]))  # expirou ontem
    conn.commit()
    conn.close()

    r = cron.get(URL_LIMPEZA, headers=AUTH)
    assert r.status_code == 200 and r.get_json()['resumo']['removidos'] == 1
    restantes = [l['id'] for l in _restantes()]
    assert ids[1] not in restantes and ids[0] in restantes and ids[2] in restantes
    # a sessão válida continua funcionando
    # ids[0] é a sessão criada pelo cadastro; sessoes[i] correspondem a ids[i+1]; sessoes[2] (ids[3]) segue válida
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': sessoes[2]['refresh_token']}).status_code == 200


def _restantes():
    conn = get_connection()
    linhas = [dict(r) for r in conn.execute("SELECT id FROM refresh_tokens")]
    conn.close()
    return linhas


def test_limpeza_e_idempotente(app, cron, relogio):
    r1 = cron.get(URL_LIMPEZA, headers=AUTH).get_json()
    assert r1['status'] == 'sucesso' and r1['resumo']['removidos'] == 0
    assert cron.get(URL_LIMPEZA, headers=AUTH).get_json()['status'] == 'ignorada'
    relogio.avancar(hours=24)
    assert cron.get(URL_LIMPEZA, headers=AUTH).get_json()['resumo']['removidos'] == 0


def test_tipos_de_job_tem_trava_e_janela_independentes(app, cron):
    assert cron.get(URL_VALIDACAO, headers=AUTH).get_json()['status'] == 'sucesso'
    assert cron.get(URL_LIMPEZA, headers=AUTH).get_json()['status'] == 'sucesso'  # não é bloqueado pelo outro


# ── CLI usa o mesmo caminho ─────────────────────────────────────────────

def test_cli_executar_automacao_e_forcar(app):
    runner = app.app.test_cli_runner()
    r = runner.invoke(args=['executar-automacao', 'validacao-vestibulares'])
    assert r.exit_code == 0 and '"status": "sucesso"' in r.output
    assert _logs('validacao_vestibulares')[-1]['origem'] == 'cli'
    r = runner.invoke(args=['executar-automacao', 'validacao-vestibulares'])
    assert r.exit_code == 0 and '"status": "ignorada"' in r.output
    r = runner.invoke(args=['executar-automacao', 'validacao-vestibulares', '--forcar'])
    assert r.exit_code == 0 and '"status": "sucesso"' in r.output


def test_cli_job_desconhecido_lista_os_disponiveis(app):
    r = app.app.test_cli_runner().invoke(args=['executar-automacao', 'nao-existe'])
    assert r.exit_code != 0 and 'validacao-vestibulares' in r.output


# ── Configuração e migração ─────────────────────────────────────────────

def test_vercel_json_agenda_exatamente_os_jobs_registrados_uma_vez_por_dia():
    config = json.load(open(os.path.join(PROJECT_ROOT, 'vercel.json'), encoding='utf-8'))
    agendados = {c['path'].rsplit('/', 1)[1] for c in config['crons']}
    assert agendados == set(automacao_service.JOBS)
    assert len(config['crons']) == len(agendados)  # nenhum job agendado duas vezes
    for c in config['crons']:
        assert c['path'].startswith('/api/cron/')
        # Compatível com o plano Hobby: minuto e hora fixos, todo dia (no máximo 1x/dia)
        m = re.fullmatch(r'(\d{1,2}) (\d{1,2}) \* \* \*', c['schedule'])
        assert m and int(m.group(1)) < 60 and int(m.group(2)) < 24, c


def test_apscheduler_foi_removido():
    assert 'apscheduler' not in open(os.path.join(PROJECT_ROOT, 'requirements.txt')).read().lower()
    assert not os.path.exists(os.path.join(PROJECT_ROOT, 'app', 'services', 'scheduler_service.py'))


def test_migracao_de_banco_antigo_preserva_logs_e_preenche_status(tmp_path, monkeypatch):
    """Um banco criado antes desta etapa (automacao_logs sem as colunas novas) é migrado sem perder dados."""
    caminho = tmp_path / 'antigo.db'
    conn = sqlite3.connect(caminho)
    conn.execute("CREATE TABLE automacao_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, "
                 "executado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP, sucesso INTEGER NOT NULL DEFAULT 1, "
                 "resumo TEXT, erro TEXT)")
    conn.execute("INSERT INTO automacao_logs (tipo, sucesso, resumo) VALUES ('validacao_vestibulares', 1, '{\"total\": 3}')")
    conn.execute("INSERT INTO automacao_logs (tipo, sucesso, erro) VALUES ('validacao_vestibulares', 0, 'boom')")
    conn.commit()
    conn.close()

    monkeypatch.setenv('SUAFACUL_DB_PATH', str(caminho))
    monkeypatch.setenv('SUAFACUL_ADMIN_PASSWORD', '')
    from database.init_db import init_db
    init_db()
    init_db()  # idempotente

    linhas = _logs()
    assert [(l['status'], l['sucesso'], l['execucao_id']) for l in linhas] == [('sucesso', 1, None), ('falha', 0, None)]
    assert json.loads(linhas[0]['resumo']) == {'total': 3} and linhas[1]['erro'] == 'boom'
    conn = get_connection()
    indices = {r['name'] for r in conn.execute("PRAGMA index_list(automacao_logs)")}
    conn.close()
    assert 'idx_automacao_em_execucao' in indices
