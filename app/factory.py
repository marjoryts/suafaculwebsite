"""Application factory do SuaFacul.

`create_app()` só monta o objeto Flask (configuração, blueprints, filtros de
template). Não toca no banco, não importa dados e não inicia agendadores:
esses passos ficam em `app/bootstrap.py` e são chamados explicitamente pelo
`run.py` (desenvolvimento), pelo CLI (`flask init-db`) ou pelos testes. Isso
permite importar o app em ambiente serverless (Vercel) sem efeitos colaterais.
"""
import os
from datetime import date, datetime

from dotenv import load_dotenv
from flask import Flask, session

from app.settings import load_config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app(config=None, load_env=True):
    """Cria uma instância do app.

    config   -- dict opcional que sobrescreve a configuração lida do ambiente.
    load_env -- lê o arquivo .env (se existir) sem sobrescrever variáveis já
                definidas no ambiente. Na Vercel não há .env: vale o painel.
    """
    if load_env:
        load_dotenv(os.path.join(BASE_DIR, '.env'))

    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'app', 'templates'),
        static_folder=os.path.join(BASE_DIR, 'public'),
        static_url_path='/static',
    )
    app.config.from_mapping(load_config(config))
    if app.config.get('SECRET_KEY_EFEMERA'):
        app.logger.warning(
            "[app] FLASK_SECRET_KEY não definida — usando chave efêmera de "
            "desenvolvimento (as sessões são perdidas a cada reinício)."
        )

    from app.services import oauth_service
    oauth_service.init_app(app)  # desabilitado sem quebrar o app se não configurado

    from app import observability
    observability.registrar(app)
    _registrar_blueprints(app)
    _registrar_helpers_de_template(app)
    _registrar_erros(app)

    from app.cli import register_cli
    register_cli(app)
    return app


def _registrar_blueprints(app):
    from app.api.v1 import bp as api_v1
    from app.routes import (api_admin, api_catalogo, api_favoritos, api_teste_vocacional,
                            api_usuario, api_vestibulares, auth_google, cron, pages)
    for modulo in (pages, auth_google, api_usuario, api_catalogo, api_vestibulares,
                   api_admin, api_favoritos, api_teste_vocacional, cron):
        app.register_blueprint(modulo.bp)
    app.register_blueprint(api_v1)  # contrato oficial do Mobile: /api/v1


def _registrar_helpers_de_template(app):
    @app.template_filter('data_br')
    def _filtro_data_br(valor, com_hora=False):
        """'2026-09-23 10:24:00' / '2026-09-23' -> '23/09/2026' (ou com hora)."""
        if not valor:
            return ''
        texto = str(valor)
        for formato in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
            try:
                d = datetime.strptime(texto[:19], formato)
                return d.strftime('%d/%m/%Y %H:%M' if com_hora else '%d/%m/%Y')
            except ValueError:
                continue
        return texto

    @app.context_processor
    def _injetar_ano_atual():
        return {'current_year': date.today().year}

    @app.context_processor
    def _injetar_usuario_sessao():
        # Usuário da sessão disponível em qualquer template (header com foto/nome)
        usuario_sessao = None
        if 'user_id' in session:
            usuario_sessao = {
                'id': session.get('user_id'),
                'nome_usuario': session.get('username'),
                'email': session.get('email'),
                'tipo': session.get('tipo'),
                'avatar_url': session.get('avatar_url'),
            }
        return dict(usuario_sessao=usuario_sessao)


def _registrar_erros(app):
    from app.errors import registrar_tratadores
    from app.security import verificar_sessao_web
    registrar_tratadores(app)
    app.before_request(verificar_sessao_web)
