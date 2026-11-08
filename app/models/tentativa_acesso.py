"""Registro de tentativas por chave (hash de e-mail, IP...) para limitar abuso.
A regra (janelas e limites) fica em app/services/limite_service.py."""
from config.database import get_connection


class TentativaAcesso:
    def registrar(self, chave, momento):
        conn = get_connection()
        try:
            conn.execute("INSERT INTO tentativas_acesso (chave, criado_em) VALUES (?, ?)", (chave, momento))
            conn.commit()
        finally:
            conn.close()

    def contar_desde(self, chave, desde):
        conn = get_connection()
        try:
            return conn.execute("SELECT COUNT(*) FROM tentativas_acesso WHERE chave=? AND criado_em >= ?",
                                (chave, desde)).fetchone()[0]
        finally:
            conn.close()

    def mais_antiga_desde(self, chave, desde):
        conn = get_connection()
        try:
            row = conn.execute("SELECT MIN(criado_em) FROM tentativas_acesso WHERE chave=? AND criado_em >= ?",
                               (chave, desde)).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def limpar(self, chave):
        conn = get_connection()
        try:
            conn.execute("DELETE FROM tentativas_acesso WHERE chave=?", (chave,))
            conn.commit()
        finally:
            conn.close()

    def remover_antigas(self, antes_de):
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("DELETE FROM tentativas_acesso WHERE criado_em < ?", (antes_de,))
            conn.commit()
            return c.rowcount
        finally:
            conn.close()
