"""Códigos enviados por e-mail (verificação, recuperação de senha, troca de e-mail).
Só o HMAC do código é guardado; a regra (geração, validade, tentativas) fica em
app/services/codigo_service.py."""
from config.database import get_connection, inserir


class CodigoEmail:
    def criar(self, usuario_id, finalidade, codigo_hash, email_destino, expira_em):
        """Novo código e invalidação dos anteriores da mesma finalidade (só o último vale)."""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("UPDATE codigos_email SET usado_em=CURRENT_TIMESTAMP "
                      "WHERE usuario_id=? AND finalidade=? AND usado_em IS NULL", (usuario_id, finalidade))
            novo_id = inserir(c, "INSERT INTO codigos_email (usuario_id, finalidade, codigo_hash, email_destino, expira_em) "
                                 "VALUES (?,?,?,?,?)", (usuario_id, finalidade, codigo_hash, email_destino, expira_em))
            conn.commit()
            return novo_id
        finally:
            conn.close()

    def ativo(self, usuario_id, finalidade):
        """O código vigente (não usado) da finalidade, ou None."""
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM codigos_email WHERE usuario_id=? AND finalidade=? AND usado_em IS NULL "
                               "ORDER BY id DESC LIMIT 1", (usuario_id, finalidade)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def ultimo_envio(self, usuario_id, finalidade):
        conn = get_connection()
        try:
            row = conn.execute("SELECT created_at FROM codigos_email WHERE usuario_id=? AND finalidade=? "
                               "ORDER BY id DESC LIMIT 1", (usuario_id, finalidade)).fetchone()
            return row['created_at'] if row else None
        finally:
            conn.close()

    def registrar_tentativa(self, codigo_id):
        conn = get_connection()
        try:
            conn.execute("UPDATE codigos_email SET tentativas=tentativas+1 WHERE id=?", (codigo_id,))
            conn.commit()
        finally:
            conn.close()

    def consumir(self, codigo_id):
        """Marca como usado; devolve False se outra requisição já o consumiu (uso único)."""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("UPDATE codigos_email SET usado_em=CURRENT_TIMESTAMP WHERE id=? AND usado_em IS NULL", (codigo_id,))
            conn.commit()
            return c.rowcount == 1
        finally:
            conn.close()

    def remover_antigos(self, antes_de):
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("DELETE FROM codigos_email WHERE created_at < ?", (antes_de,))
            conn.commit()
            return c.rowcount
        finally:
            conn.close()
