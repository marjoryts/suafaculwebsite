"""Entrypoint WSGI (Vercel, gunicorn, `flask --app wsgi ...`).

Importar este módulo NÃO acessa o banco nem inicia agendadores (ver
app/factory.py). O banco é o PostgreSQL do Supabase (persistente): esquema e
dados de referência são um passo de deploy — `flask --app wsgi init-db` —,
não algo refeito a cada cold start. `pyproject.toml` ([tool.vercel]
entrypoint) aponta para este arquivo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.factory import create_app  # noqa: E402

app = create_app()
