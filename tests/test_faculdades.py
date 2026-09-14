"""Testes de busca de faculdades: por nome, parcial, sem resultado, e
comportamento amigável quando a integração externa (e-MEC) falha."""


def _criar_faculdade(app, **kwargs):
    dados = {
        'nome': 'Universidade Federal de Exemplo', 'sigla': 'UFEX',
        'organizacao_academica': 'Federal', 'tipo_instituicao': 'Pública',
        'url': '', 'endereco': '', 'cidade': 'São Paulo', 'uf': 'SP',
        'telefone': '', 'email': '', 'situacao': 'ativa', 'fonte': 'manual',
        'codigo_emec': None,
    }
    dados.update(kwargs)
    return app.Faculdade().criar(dados)


def test_busca_por_nome_encontra_resultado(app, client):
    _criar_faculdade(app, nome='Universidade Federal de São Carlos', sigla='UFSCAR')
    r = client.get('/api/faculdades/listar?busca=São Carlos')
    body = r.get_json()
    assert body['success'] is True
    assert any('São Carlos' in f['nome'] for f in body['faculdades'])


def test_busca_parcial(app, client):
    _criar_faculdade(app, nome='Pontifícia Universidade Católica de São Paulo', sigla='PUC-SP')
    r = client.get('/api/faculdades/listar?busca=Pontif')
    body = r.get_json()
    assert body['success'] is True
    assert len(body['faculdades']) >= 1


def test_busca_sem_resultado(app, client):
    r = client.get('/api/faculdades/listar?busca=NomeQueNaoExisteInstituicaoXYZ123')
    body = r.get_json()
    assert body['success'] is True
    assert body['faculdades'] == []


def test_importar_emec_erro_de_rede_nao_quebra(app, client, monkeypatch):
    """Se o e-MEC estiver indisponível, a API deve responder com um erro
    amigável (success=False + mensagem) e nunca um 500."""
    def _falha(*a, **kw):
        raise Exception("Connection timed out")
    monkeypatch.setattr(app.emec_service, '_buscar_html_emec', _falha)

    client.post('/api/usuario/login', data={'username': 'admin', 'password': 'admin123'})
    r = client.post('/api/faculdades/emec/importar', data={'codigo': '339'})
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is False
    assert 'e-mec' in body['message'].lower() or 'falha' in body['message'].lower()


def test_importar_uf_falha_isolada_nao_interrompe_lote(app, monkeypatch):
    """Uma instituição com dado inesperado não pode travar a importação
    das demais instituições da mesma UF (requisito da automação)."""
    from app.services import emec_service

    instituicoes_fake = [
        {'codigo_emec': '1', 'nome': 'Instituição OK 1', 'organizacao_academica': '', 'tipo_instituicao': 'Pública', 'situacao': 'ativa', 'uf': 'SP'},
        {'codigo_emec': '2', 'organizacao_academica': '', 'tipo_instituicao': 'Pública', 'situacao': 'ativa', 'uf': 'SP'},  # sem 'nome' -> KeyError ao processar
        {'codigo_emec': '3', 'nome': 'Instituição OK 2', 'organizacao_academica': '', 'tipo_instituicao': 'Pública', 'situacao': 'ativa', 'uf': 'SP'},
    ]
    monkeypatch.setattr(emec_service, 'listar_instituicoes_emec_por_uf', lambda uf: instituicoes_fake)

    resultado = emec_service.importar_todas_faculdades_por_uf('SP')
    assert resultado['success'] is True
    assert resultado['total_encontradas'] == 3
    assert resultado['falhas'] == 1
    # As duas instituições válidas devem ter sido processadas mesmo com a terceira falhando
    assert resultado['criadas'] + resultado['atualizadas'] == 2


# ── Fonte de dados: CSV oficial de Dados Abertos do MEC ────────────────

def test_dados_abertos_csv_parseado_corretamente(app, monkeypatch):
    """Simula o download do CSV oficial (sem rede) e confirma que o
    parser reconhece as colunas e filtra por UF/situação ativa."""
    from app.services import emec_service

    csv_fake = (
        "CODIGO_DA_IES,NOME_DA_IES,SIGLA,CATEGORIA_DA_IES,COMUNITARIA,CONFESSIONAL,"
        "FILANTROPICA,ORGANIZACAO_ACADEMICA,CODIGO_MUNICIPIO_IBGE,MUNICIPIO,UF,SITUACAO_IES\n"
        "21995,Faculdade de Tecnologia Senac Curitiba,,Privada,N,N,N,Faculdade,4106902,Curitiba,PR,Ativa\n"
        "5701,UNIVERSIDADE DO ESTADO DO AMAPÁ,UEAP,Pública,N,N,N,Universidade,1600303,Macapá,AP,Ativa\n"
        "1768,FACULDADE REGIONAL SERRANA,FUNPAC,Privada,N,N,N,Faculdade,3205069,Venda Nova do Imigrante,ES,Extinta\n"
        "23261,Faculdade São Judas de São Bernardo do Campo,,Privada,N,N,N,Faculdade,3548708,São Bernardo do Campo,SP,Ativa\n"
    ).encode('utf-8')

    class FakeResponse:
        content = csv_fake
        def raise_for_status(self): pass

    monkeypatch.setattr(emec_service.requests, 'get', lambda *a, **kw: FakeResponse())
    emec_service._cache_dados_abertos['instituicoes'] = None  # limpa cache entre testes

    instituicoes_sp = emec_service._listar_instituicoes_via_dados_abertos('SP')
    assert len(instituicoes_sp) == 1
    assert 'São Bernardo' in instituicoes_sp[0]['nome']
    assert instituicoes_sp[0]['tipo_instituicao'] == 'Privada'

    instituicoes_ap = emec_service._listar_instituicoes_via_dados_abertos('AP')
    assert len(instituicoes_ap) == 1
    assert instituicoes_ap[0]['tipo_instituicao'] == 'Pública'

    # ES só tem a instituição "Extinta" -> não deve aparecer na listagem de ativas
    instituicoes_es = emec_service._listar_instituicoes_via_dados_abertos('ES')
    assert instituicoes_es == []


def test_listar_por_uf_cai_para_scraping_se_csv_falhar(app, monkeypatch):
    """Se o download do CSV oficial falhar por qualquer motivo, a função
    principal deve tentar o scraping do e-MEC como fallback, não quebrar."""
    from app.services import emec_service

    monkeypatch.setattr(emec_service, '_listar_instituicoes_via_dados_abertos',
                         lambda uf: (_ for _ in ()).throw(RuntimeError("CSV indisponível")))
    chamou_fallback = {'sim': False}

    def fallback_fake(uf):
        chamou_fallback['sim'] = True
        return [{'codigo_emec': '99', 'nome': 'Via Scraping', 'organizacao_academica': '', 'tipo_instituicao': 'Privada', 'situacao': 'ativa', 'uf': uf}]

    monkeypatch.setattr(emec_service, 'listar_instituicoes_emec_por_uf_via_scraping', fallback_fake)

    resultado = emec_service.listar_instituicoes_emec_por_uf('SP')
    assert chamou_fallback['sim'] is True
    assert resultado[0]['nome'] == 'Via Scraping'


# ── Upload manual do CSV (fallback quando o WAF bloqueia o download automático) ──

_CSV_EXEMPLO = (
    "CODIGO_DA_IES,NOME_DA_IES,SIGLA,CATEGORIA_DA_IES,COMUNITARIA,CONFESSIONAL,"
    "FILANTROPICA,ORGANIZACAO_ACADEMICA,CODIGO_MUNICIPIO_IBGE,MUNICIPIO,UF,SITUACAO_IES\n"
    "21995,Faculdade Exemplo Upload,,Privada,N,N,N,Faculdade,4106902,Curitiba,PR,Ativa\n"
    "23261,Faculdade São Judas de São Bernardo do Campo,,Privada,N,N,N,Faculdade,3548708,São Bernardo do Campo,SP,Ativa\n"
).encode('utf-8')


def test_importar_csv_upload_cria_faculdades(app):
    from app.services import emec_service
    resultado = emec_service.importar_instituicoes_de_csv_upload(_CSV_EXEMPLO)
    assert resultado['success'] is True
    assert resultado['total_no_arquivo'] == 2
    assert resultado['criadas'] == 2

    faculdade = app.Faculdade().buscar_por_codigo_emec('21995')
    assert faculdade is not None
    assert 'Exemplo Upload' in faculdade['nome']


def test_rota_upload_csv_exige_admin(client):
    import io
    r = client.post('/api/faculdades/emec/importar-csv', data={
        'arquivo': (io.BytesIO(_CSV_EXEMPLO), 'ies.csv')
    }, content_type='multipart/form-data')
    assert r.status_code in (302, 401, 403)


def test_rota_upload_csv_funciona_logado_como_admin(admin_client):
    import io
    r = admin_client.post('/api/faculdades/emec/importar-csv', data={
        'arquivo': (io.BytesIO(_CSV_EXEMPLO), 'ies.csv')
    }, content_type='multipart/form-data')
    body = r.get_json()
    assert body['success'] is True
    assert body['criadas'] == 2


def test_rota_upload_csv_rejeita_arquivo_nao_csv(admin_client):
    import io
    r = admin_client.post('/api/faculdades/emec/importar-csv', data={
        'arquivo': (io.BytesIO(b'nao e um csv'), 'arquivo.txt')
    }, content_type='multipart/form-data')
    body = r.get_json()
    assert body['success'] is False
