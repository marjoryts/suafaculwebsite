"""Persistência dos refresh tokens (tabela refresh_tokens). Só SQL, sem regra:
a rotação, a detecção de reuso e os prazos vivem em services/token_service.py.

Nunca recebe nem guarda o token em si — apenas o hash SHA-256.
"""
from config.database import get_connection, inserir

_INSERT = ("INSERT INTO refresh_tokens (familia_id, usuario_id, token_hash, dispositivo, expira_em) "
           "VALUES (?,?,?,?,?)")


class RefreshToken:
    def criar(self, familia_id, usuario_id, token_hash, expira_em, dispositivo=None):
        conn = get_connection()
        try:
            c = conn.cursor()
            id = inserir(c, _INSERT, (familia_id, usuario_id, token_hash, dispositivo, expira_em))
            conn.commit()
            return id
        finally:
            conn.close()

    def buscar_por_hash(self, token_hash):
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM refresh_tokens WHERE token_hash=?", (token_hash,))
            row = c.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def rotacionar(self, token_id, novo, usado_em):
        """Marca o token como usado E grava o próximo, na mesma transação.

        O UPDATE é condicional (só se ainda não foi usado nem revogado): se duas
        requisições tentarem consumir o mesmo token, só uma vence. Devolve False
        para quem perdeu — o chamador trata como reutilização.
        """
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("UPDATE refresh_tokens SET usado_em=? WHERE id=? AND usado_em IS NULL AND revogado_em IS NULL",
                      (usado_em, token_id))
            if c.rowcount != 1:
                conn.rollback()
                return False
            inserir(c, _INSERT, (novo['familia_id'], novo['usuario_id'], novo['token_hash'],
                                 novo.get('dispositivo'), novo['expira_em']))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def revogar_familia(self, familia_id, revogado_em, motivo):
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("UPDATE refresh_tokens SET revogado_em=?, motivo_revogacao=? "
                      "WHERE familia_id=? AND revogado_em IS NULL", (revogado_em, motivo, familia_id))
            conn.commit()
            return c.rowcount
        finally:
            conn.close()

    def revogar_do_usuario(self, usuario_id, revogado_em, motivo, exceto_familia=None):
        """Revoga todas as sessões do usuário (opcionalmente preservando uma)."""
        conn = get_connection()
        try:
            c = conn.cursor()
            sql = ("UPDATE refresh_tokens SET revogado_em=?, motivo_revogacao=? "
                   "WHERE usuario_id=? AND revogado_em IS NULL")
            params = [revogado_em, motivo, usuario_id]
            if exceto_familia:
                sql += " AND familia_id<>?"
                params.append(exceto_familia)
            c.execute(sql, params)
            conn.commit()
            return c.rowcount
        finally:
            conn.close()

    def familia_ativa(self, familia_id):
        """A sessão (família) ainda não foi revogada?"""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT 1 FROM refresh_tokens WHERE familia_id=? AND revogado_em IS NULL LIMIT 1",
                      (familia_id,))
            return c.fetchone() is not None
        finally:
            conn.close()

    def remover_expirados(self, expirados_ate):
        """Apaga tokens cuja expiração é anterior a `expirados_ate` ('AAAA-MM-DD HH:MM:SS').
        Idempotente. Devolve quantas linhas foram removidas."""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("DELETE FROM refresh_tokens WHERE expira_em < ?", (expirados_ate,))
            conn.commit()
            return c.rowcount
        finally:
            conn.close()
