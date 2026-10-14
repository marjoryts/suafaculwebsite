"""Entrypoint WSGI para produção (Vercel / gunicorn).

Por que este arquivo existe: o projeto tem ao mesmo tempo o arquivo
`app.py` (onde a instância Flask é criada) e o pacote `app/` (models,
services, templates). Em Python, `import app` resolve para o PACOTE
`app/`, que não tem nenhuma variável `app` — então qualquer servidor que
carregue o projeto como módulo ("app:app") não encontra o Flask e a
função cai antes de atender a primeira requisição.

Aqui carregamos `app.py` pelo caminho do arquivo, com um nome de módulo
próprio (o mesmo truque usado em tests/conftest.py), e reexportamos a
instância como `app`. `pyproject.toml` ([tool.vercel] entrypoint) aponta
para cá. Localmente nada muda: continue usando `python app.py`.
"""
import importlib.util
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

_spec = importlib.util.spec_from_file_location('suafacul_main', os.path.join(BASE_DIR, 'app.py'))
_modulo = importlib.util.module_from_spec(_spec)
sys.modules['suafacul_main'] = _modulo
_spec.loader.exec_module(_modulo)

app = _modulo.app
