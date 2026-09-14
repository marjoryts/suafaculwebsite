"""Testes da automação diária de vestibulares: validação de datas,
vínculo automático com faculdade cadastrada, resiliência por item e o
job do scheduler."""
from datetime import date, timedelta

REQUIRED = dict(tipo_instituicao='Pública', cidade='São Paulo', regiao='Sudeste',
                 periodo_inscricao='01/01 a 01/02', descricao='desc', link_edital='https://example.com')


def _criar_vestibular(app, **kwargs):
    dados = dict(REQUIRED)
    dados.update(kwargs)
    return app.Vestibular().criar(dados)


def test_vestibular_com_data_futura_fica_ativo(app):
    from app.services import vestibular_service
    amanha = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    _criar_vestibular(app, nome='Vestibular Futuro', instituicao='Instituição X', data_prova=amanha)

    resultado = vestibular_service.validar_vestibulares(aplicar=True)
    assert resultado['success'] is True
    item = next(i for i in resultado['itens'] if i['nome'] == 'Vestibular Futuro')
    assert item['status_validacao'] == 'ativo'


def test_vestibular_com_data_passada_fica_encerrado(app):
    from app.services import vestibular_service
    ontem = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    _criar_vestibular(app, nome='Vestibular Passado', instituicao='Instituição Y', data_prova=ontem)

    resultado = vestibular_service.validar_vestibulares(aplicar=True)
    item = next(i for i in resultado['itens'] if i['nome'] == 'Vestibular Passado')
    assert item['status_validacao'] == 'encerrado'


def test_vestibular_com_data_invalida_e_marcado(app):
    from app.services import vestibular_service
    _criar_vestibular(app, nome='Vestibular Data Ruim', instituicao='Instituição Z', data_prova='não é uma data')

    resultado = vestibular_service.validar_vestibulares(aplicar=True)
    item = next(i for i in resultado['itens'] if i['nome'] == 'Vestibular Data Ruim')
    assert item['status_validacao'] == 'data_invalida'


def test_vestibular_vincula_faculdade_cadastrada(app):
    from app.services import vestibular_service
    app.Faculdade().criar({
        'nome': 'Universidade Federal de São Carlos', 'sigla': 'UFSCAR',
        'organizacao_academica': 'Federal', 'tipo_instituicao': 'Pública',
        'url': '', 'endereco': '', 'cidade': 'São Carlos', 'uf': 'SP',
        'telefone': '', 'email': '', 'situacao': 'ativa', 'fonte': 'manual', 'codigo_emec': None,
    })
    amanha = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    _criar_vestibular(app, nome='Vestibular UFSCAR', instituicao='Universidade Federal de São Carlos', data_prova=amanha)

    resultado = vestibular_service.validar_vestibulares(aplicar=True)
    item = next(i for i in resultado['itens'] if i['nome'] == 'Vestibular UFSCAR')
    assert item['cadastrado_ok'] is True
    assert 'São Carlos' in item['faculdade_nome']


def test_vestibular_sem_faculdade_cadastrada(app):
    from app.services import vestibular_service
    amanha = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    _criar_vestibular(app, nome='Vestibular Orfao', instituicao='Instituição Inexistente XPTO', data_prova=amanha)

    resultado = vestibular_service.validar_vestibulares(aplicar=True)
    item = next(i for i in resultado['itens'] if i['nome'] == 'Vestibular Orfao')
    assert item['cadastrado_ok'] is False


def test_falha_em_um_item_nao_interrompe_os_demais(app, monkeypatch):
    """Um vestibular com dado que quebra o processamento não pode impedir
    que os demais sejam validados (requisito da automação diária)."""
    from app.services import vestibular_service

    amanha = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    _criar_vestibular(app, nome='Vestibular Bom 1', instituicao='Inst A', data_prova=amanha)
    _criar_vestibular(app, nome='Vestibular Bom 2', instituicao='Inst B', data_prova=amanha)

    original_normalizar = vestibular_service._normalizar
    chamadas = {'n': 0}

    def normalizar_com_falha_no_segundo(texto):
        chamadas['n'] += 1
        if chamadas['n'] == 2:
            raise RuntimeError("falha simulada")
        return original_normalizar(texto)

    monkeypatch.setattr(vestibular_service, '_normalizar', normalizar_com_falha_no_segundo)

    resultado = vestibular_service.validar_vestibulares(aplicar=True)
    assert resultado['success'] is True
    # Pelo menos um item processado com sucesso apesar da falha no outro
    assert len(resultado['itens']) >= 1
    assert len(resultado['falhas']) >= 1


def test_job_diario_do_scheduler_grava_log(app):
    """O job que o APScheduler roda uma vez por dia deve gravar um
    registro em automacao_logs, sucesso ou falha."""
    from app.services import scheduler_service
    from config.database import get_connection

    amanha = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    _criar_vestibular(app, nome='Vestibular Job', instituicao='Inst Job', data_prova=amanha)

    scheduler_service.rodar_validacao_vestibulares_diaria()

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM automacao_logs WHERE tipo='validacao_vestibulares' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    assert row is not None
    assert row['sucesso'] == 1


def test_job_diario_nao_quebra_com_excecao_interna(app, monkeypatch):
    """Mesmo se validar_vestibulares levantar uma exceção inesperada, o job
    não deve propagar o erro (senão o scheduler pararia de agendar) — ele
    deve registrar a falha em automacao_logs e seguir."""
    from app.services import scheduler_service, vestibular_service
    from config.database import get_connection

    def _explode(aplicar=False):
        raise RuntimeError("banco de dados indisponível")

    monkeypatch.setattr(vestibular_service, 'validar_vestibulares', _explode)

    scheduler_service.rodar_validacao_vestibulares_diaria()  # não deve levantar

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM automacao_logs WHERE tipo='validacao_vestibulares' ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    assert row is not None
    assert row['sucesso'] == 0
    assert 'banco de dados indisponível' in row['erro']
