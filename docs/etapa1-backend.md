# Etapa 1 — Preparação do backend

## O que mudou
- `app.py` (945 linhas, executava banco/seed/scheduler no import) foi substituído por:
  - `app/factory.py` — `create_app(config=None, load_env=True)`; **sem efeitos colaterais**
    (não abre o banco, não importa dados, não inicia threads).
  - `app/settings.py` — configuração por ambiente (12-factor); segredo obrigatório fora do debug.
  - `app/security.py` — `login_required`, `admin_required`, `check_auth`, login na sessão.
  - `app/routes/*` — 9 blueprints; **as 55 rotas (URL + método) foram preservadas** (teste
    `test_todas_as_rotas_existentes_foram_preservadas`). Nenhum template usava `url_for`.
  - `app/bootstrap.py` — `init_database()` (esquema + seed) e `start_scheduler()` (só dev).
  - `app/cli.py` — `flask --app wsgi init-db`.
  - `wsgi.py` — entrypoint WSGI (Vercel/gunicorn). `run.py` — servidor de desenvolvimento.
- Eliminado o conflito de nomes `app.py` × pacote `app/`.
- `requirements.txt` = só runtime; `pytest` em `requirements-dev.txt`. `.vercelignore` novo.
- Bug corrigido: `app/models/usuario.py` inseria o diretório errado em `sys.path`
  (`app/` em vez da raiz), o que fazia `config` resolver para outro módulo conforme a ordem de import.

## Como validar
```bash
pip install -r requirements-dev.txt
python -m pytest -q                                   # 138 testes
FLASK_DEBUG=1 python run.py                           # dev (http://localhost:5000)
FLASK_SECRET_KEY=... flask --app wsgi init-db         # esquema/seed sem subir servidor
```

## Fora de escopo desta etapa (próximas)
- SQL ainda dentro de `api_admin.stats` e `api_v1.instituicao_cursos` → Etapa 3 (services).
- Estáticos ainda por `static_folder`/`/static` (na Vercel devem sair da CDN via `public/`) → validar no deploy de staging.
- `scheduler_service` (APScheduler) só roda via `run.py`; em produção será substituído por Vercel Cron → Etapa 6.
