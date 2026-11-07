"""Histórico e controle de execução das automações (tabela automacao_logs).

Só SQL: a decisão de rodar/ignorar, a trava e os prazos vivem em
services/automacao_service.py. Cada linha é UMA execução, identificada por
`execucao_id`, com estado: executando | sucesso | falha | ignorada.
"""
import json

from config.database import ErroDeIntegridade, get_connection, inserir


def _resumo(valor):
    try:
        return json.loads(valor) if valor else None
    except ValueError:
        return None


class AutomacaoLog:
    # ── Ciclo de vida de uma execução ───────────────────────────────────

    def iniciar(self, tipo, execucao_id, origem, iniciado_em, bloqueio_valido_desde):
        """Tenta assumir a trava do `tipo`. True se esta execução pode rodar.

        Trava = uma linha 'executando' (índice único parcial: só existe uma por tipo).
        Antes, execuções presas há mais tempo que `bloqueio_valido_desde` (processo
        que morreu no meio) são marcadas como falha, liberando a trava.
        """
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE automacao_logs SET status='falha', sucesso=0, finalizado_em=?, "
                "erro='Execução interrompida (trava expirada)' "
                "WHERE tipo=? AND status='executando' AND iniciado_em < ?",
                (iniciado_em, tipo, bloqueio_valido_desde))
            try:
                inserir(c, "INSERT INTO automacao_logs (tipo, sucesso, execucao_id, status, origem, iniciado_em) "
                           "VALUES (?, 0, ?, 'executando', ?, ?)", (tipo, execucao_id, origem, iniciado_em))
            except ErroDeIntegridade:
                conn.rollback()
                return False
            conn.commit()
            return True
        finally:
            conn.close()

    def finalizar(self, execucao_id, status, finalizado_em, duracao_ms, resumo=None, erro=None):
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE automacao_logs SET status=?, sucesso=?, finalizado_em=?, duracao_ms=?, resumo=?, erro=? "
                "WHERE execucao_id=?",
                (status, 1 if status == 'sucesso' else 0, finalizado_em, duracao_ms,
                 json.dumps(resumo, ensure_ascii=False, default=str) if resumo else None, erro, execucao_id))
            conn.commit()
        finally:
            conn.close()

    def registrar_ignorada(self, tipo, execucao_id, origem, momento, motivo):
        """Execução que não rodou (duplicada/concorrente). `sucesso=1`: não é falha."""
        conn = get_connection()
        try:
            c = conn.cursor()
            inserir(c, "INSERT INTO automacao_logs (tipo, sucesso, execucao_id, status, origem, iniciado_em, "
                       "finalizado_em, duracao_ms, resumo) VALUES (?, 1, ?, 'ignorada', ?, ?, ?, 0, ?)",
                    (tipo, execucao_id, origem, momento, momento, json.dumps({'motivo': motivo}, ensure_ascii=False)))
            conn.commit()
        finally:
            conn.close()

    def ultimo_sucesso_em(self, tipo):
        """'AAAA-MM-DD HH:MM:SS' do fim da última execução bem-sucedida, ou None."""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT MAX(finalizado_em) AS ultimo FROM automacao_logs WHERE tipo=? AND status='sucesso'",
                      (tipo,))
            return c.fetchone()['ultimo']
        finally:
            conn.close()

    # ── Registro avulso (CLI e execuções antigas) ───────────────────────

    def registrar(self, tipo, sucesso, resumo=None, erro=None, origem=None):
        conn = get_connection()
        try:
            c = conn.cursor()
            id = inserir(
                c,
                "INSERT INTO automacao_logs (tipo, sucesso, resumo, erro, status, origem) VALUES (?,?,?,?,?,?)",
                (tipo, 1 if sucesso else 0, json.dumps(resumo, ensure_ascii=False) if resumo else None, erro,
                 'sucesso' if sucesso else 'falha', origem),
            )
            conn.commit()
            return id
        finally:
            conn.close()

    # ── Consultas ───────────────────────────────────────────────────────

    def ultimos(self, limite=5, tipo=None):
        try:
            conn = get_connection()
            c = conn.cursor()
            sql = ("SELECT id, tipo, executado_em, sucesso, resumo, execucao_id, status, origem, "
                   "iniciado_em, finalizado_em, duracao_ms, erro FROM automacao_logs")
            params = []
            if tipo:
                sql += " WHERE tipo=?"
                params.append(tipo)
            c.execute(sql + " ORDER BY executado_em DESC, id DESC LIMIT ?", params + [limite])
            linhas = c.fetchall()
            conn.close()
        except Exception:
            return []
        return [{'id': r['id'], 'tipo': r['tipo'], 'executado_em': r['executado_em'],
                 'sucesso': bool(r['sucesso']), 'resumo': _resumo(r['resumo']),
                 'execucao_id': r['execucao_id'], 'status': r['status'], 'origem': r['origem'],
                 'iniciado_em': r['iniciado_em'], 'finalizado_em': r['finalizado_em'],
                 'duracao_ms': r['duracao_ms'], 'erro': r['erro']} for r in linhas]
