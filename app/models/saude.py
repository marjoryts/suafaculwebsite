"""Consulta mínima para o health check (o SQL fica nos models)."""
from config.database import get_connection


class Saude:
    def verificar_banco(self):
        conn = get_connection()
        try:
            conn.execute("SELECT 1 FROM public.suafacul_migracoes LIMIT 1").fetchone()
        finally:
            conn.close()
