"""Testes do seed automático — popula instituições/cursos sozinho na
subida se o banco estiver vazio e os arquivos existirem em
data/seeds/, pra não precisar clicar em 'Importar' em cada deploy novo."""
import io


CSV_INSTITUICOES = (
    "CODIGO_DA_IES,NOME_DA_IES,SIGLA,CATEGORIA_DA_IES,COMUNITARIA,CONFESSIONAL,"
    "FILANTROPICA,ORGANIZACAO_ACADEMICA,CODIGO_MUNICIPIO_IBGE,MUNICIPIO,UF,SITUACAO_IES\n"
    "555,Faculdade Seed Automático,,Privada,N,N,N,Faculdade,3548708,São Bernardo do Campo,SP,Ativa\n"
).encode('utf-8')


def test_seed_instituicoes_roda_quando_ainda_nao_ha_importacao_real(app, tmp_path, monkeypatch):
    from app.services import seed_service
    caminho = tmp_path / "instituicoes.csv"
    caminho.write_bytes(CSV_INSTITUICOES)
    monkeypatch.setattr(seed_service, 'CAMINHO_INSTITUICOES', str(caminho))

    # A base tem as faculdades de exemplo do init_db.py (fonte='manual'),
    # mas nenhuma importada de verdade ainda — o seed deve rodar mesmo assim.
    seed_service._seed_instituicoes_se_necessario()

    faculdade = app.Faculdade().buscar_por_codigo_emec('555')
    assert faculdade is not None
    assert 'Seed Automático' in faculdade['nome']


def test_seed_instituicoes_nao_faz_nada_sem_arquivo(app, tmp_path, monkeypatch):
    from app.services import seed_service
    monkeypatch.setattr(seed_service, 'CAMINHO_INSTITUICOES', str(tmp_path / "nao_existe.csv"))

    seed_service._seed_instituicoes_se_necessario()  # não deve levantar exceção

    assert app.Faculdade().buscar_por_codigo_emec('555') is None


def test_seed_instituicoes_pula_se_ja_importou_do_emec_antes(app, tmp_path, monkeypatch):
    """Se alguém já importou dados reais do e-MEC (manualmente ou via
    seed numa subida anterior), não deve importar de novo por cima."""
    from app.services import seed_service

    # simula uma importação real já ter acontecido antes
    app.Faculdade().criar({
        'nome': 'Já Importada Antes', 'sigla': None, 'organizacao_academica': '', 'tipo_instituicao': 'Privada',
        'url': '', 'endereco': '', 'cidade': '', 'uf': 'SP', 'telefone': '', 'email': '',
        'situacao': 'ativa', 'fonte': 'emec_csv_upload', 'codigo_emec': '999',
    })

    caminho = tmp_path / "instituicoes.csv"
    caminho.write_bytes(CSV_INSTITUICOES)
    monkeypatch.setattr(seed_service, 'CAMINHO_INSTITUICOES', str(caminho))

    seed_service._seed_instituicoes_se_necessario()
    assert app.Faculdade().buscar_por_codigo_emec('555') is None


def test_rodar_seed_automatico_nunca_levanta_excecao(app, monkeypatch):
    """Uma falha no seed (arquivo corrompido, erro de banco) não pode
    impedir o app de subir — só registra e segue."""
    from app.services import seed_service

    def _explode():
        raise RuntimeError("banco indisponível")

    monkeypatch.setattr(seed_service, '_seed_instituicoes_se_necessario', _explode)
    monkeypatch.setattr(seed_service, '_seed_cursos_se_necessario', _explode)

    seed_service.rodar_seed_automatico_se_necessario()  # não deve levantar
