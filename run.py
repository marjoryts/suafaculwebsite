"""Servidor de DESENVOLVIMENTO local: `python run.py`.

Inicializa o banco (SQLite) e roda o seed — o que o import do app deixou de fazer
sozinho. Automações rodam via Vercel Cron (produção) ou `flask --app wsgi executar-automacao
NOME` (local). Não use em produção.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.bootstrap import init_database  # noqa: E402
from app.factory import create_app  # noqa: E402

if __name__ == '__main__':
    app = create_app()
    init_database(app)
    # Por padrão só aceita conexões do próprio computador. Para testar o app mobile no celular
    # (Expo Go, mesma rede Wi-Fi), defina HOST=0.0.0.0 com FLASK_DEBUG desligado e uma
    # FLASK_SECRET_KEY: o depurador do Werkzeug executa código e não pode ficar exposto na rede.
    host = os.environ.get('HOST', '127.0.0.1')
    if host not in ('127.0.0.1', 'localhost', '::1') and app.debug:
        raise SystemExit(
            f"HOST={host} expõe o servidor na rede: desligue o FLASK_DEBUG e defina FLASK_SECRET_KEY "
            "(o depurador do Werkzeug executa código arbitrário)."
        )
    port = int(os.environ.get('PORT', 5000))
    print(f"SuaFacul rodando em http://{host}:{port}")
    app.run(debug=app.debug, host=host, port=port)
