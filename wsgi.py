"""Entrypoint WSGI (Vercel, gunicorn, `flask --app wsgi ...`).

Localmente, importar este módulo NÃO acessa o banco nem inicia agendadores
(ver app/factory.py); o servidor de desenvolvimento é `python run.py`.

Na Vercel o banco SQLite fica em /tmp (config/database.py) e começa vazio a
cada inicialização da função, então lá o esquema e o seed são criados aqui,
uma vez por instância. `pyproject.toml` ([tool.vercel] entrypoint) aponta
para este arquivo.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.factory import create_app  # noqa: E402

app = create_app()

if os.environ.get('VERCEL'):
    from app.bootstrap import init_database  # noqa: E402

    init_database(app)
