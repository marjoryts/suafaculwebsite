"""Comandos de linha de comando: `flask --app wsgi <comando>`.

A CLI é só uma "casca": cada comando chama um service (o mesmo que a Web e,
no futuro, uma fila/Workflow usariam) e registra a execução em
`automacao_logs`. Nenhuma regra de importação vive aqui.
"""
import json
import traceback

import click


def _executar_registrando(tipo, funcao):
    """Roda `funcao()`, imprime o resumo e grava a execução em automacao_logs."""
    from app.models.automacao_log import AutomacaoLog
    try:
        resultado = funcao()
    except Exception as e:
        AutomacaoLog().registrar(tipo, False, erro=f"{e}\n{traceback.format_exc()}", origem='cli')
        raise click.ClickException(f'Falha em {tipo}: {e}')
    sucesso = bool(resultado.get('success', True))
    resumo = resultado.get('resumo', {k: v for k, v in resultado.items() if k != 'itens'})
    AutomacaoLog().registrar(tipo, sucesso, resumo=resumo, erro=None if sucesso else resultado.get('message'),
                             origem='cli')
    click.echo(json.dumps(resumo, ensure_ascii=False, indent=2, default=str))
    if not sucesso:
        raise click.ClickException(resultado.get('message', 'Falha na importação.'))


def register_cli(app):
    @app.cli.command('init-db')
    def init_db_command():
        """Cria/migra o esquema do banco e roda o seed automático."""
        from app.bootstrap import init_database
        init_database(app)
        click.echo('Banco inicializado.')

    @app.cli.command('importar-instituicoes')
    @click.argument('arquivo', type=click.Path(exists=True, dir_okay=False))
    def importar_instituicoes(arquivo):
        """Importa instituições do CSV oficial de Dados Abertos do MEC."""
        from app.bootstrap import init_database
        from app.services import emec_service
        init_database(app)

        def _rodar():
            with open(arquivo, 'rb') as f:
                return emec_service.importar_instituicoes_de_csv_upload(f.read())
        _executar_registrando('importacao_instituicoes_csv', _rodar)

    @app.cli.command('importar-cursos')
    @click.argument('arquivo', type=click.Path(exists=True, dir_okay=False))
    def importar_cursos(arquivo):
        """Importa cursos do MICRODADOS_CADASTRO_CURSOS_<ano>.CSV (Censo INEP)."""
        from app.bootstrap import init_database
        from app.services import censo_service
        init_database(app)

        def _rodar():
            with open(arquivo, 'rb') as f:
                return censo_service.importar_cursos_de_csv_upload(f)
        _executar_registrando('importacao_cursos_censo', _rodar)

    @app.cli.command('validar-vestibulares')
    @click.option('--aplicar', is_flag=True, help='Grava o resultado (sem isso, só relatório).')
    def validar_vestibulares(aplicar):
        """Valida datas dos vestibulares e o vínculo com as faculdades."""
        from app.bootstrap import init_database
        from app.services import vestibular_service
        init_database(app)
        _executar_registrando('validacao_vestibulares_cli',
                              lambda: vestibular_service.validar_vestibulares(aplicar=aplicar))

    @app.cli.command('executar-automacao')
    @click.argument('nome')
    @click.option('--forcar', is_flag=True, help='Ignora a janela anti-duplicata (a trava de concorrência continua).')
    def executar_automacao(nome, forcar):
        """Roda uma automação agendada (a mesma do Vercel Cron), ex.: validacao-vestibulares."""
        from app.bootstrap import init_database
        from app.services import automacao_service
        from app.services.erros import NaoEncontradoError
        init_database(app)
        try:
            resultado = automacao_service.executar(nome, origem='cli', forcar=forcar)
        except NaoEncontradoError as e:
            raise click.ClickException(f"{e.message} Disponíveis: {', '.join(e.details['jobs'])}")
        click.echo(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))
        if resultado['status'] == 'falha':
            raise click.ClickException('A automação falhou; veja o erro em automacao_logs.')
