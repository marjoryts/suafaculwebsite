"""Testes da API própria (v1) de instituições — a camada que substitui a
dependência de consultar o e-MEC em tempo real."""


def _criar_faculdade(app, **kwargs):
    dados = {
        'nome': 'Universidade Federal de Exemplo', 'sigla': 'UFEX',
        'organizacao_academica': 'Federal', 'tipo_instituicao': 'Pública',
        'url': 'https://ufex.example.com', 'endereco': 'Rua Exemplo, 100', 'cidade': 'São Paulo', 'uf': 'SP',
        'telefone': '(11) 1234-5678', 'email': 'contato@ufex.example.com', 'situacao': 'ativa', 'fonte': 'manual',
        'codigo_emec': '12345',
    }
    dados.update(kwargs)
    return app.Faculdade().criar(dados)


def test_v1_listar_retorna_envelope_data_meta(app, client):
    _criar_faculdade(app, nome='Faculdade V1 Teste', codigo_emec='11111')
    r = client.get('/api/v1/instituicoes')
    assert r.status_code == 200
    body = r.get_json()
    assert 'data' in body and 'meta' in body
    assert body['meta']['total'] >= 1
    assert any(i['nome'] == 'Faculdade V1 Teste' for i in body['data'])


def test_v1_filtro_por_uf(app, client):
    _criar_faculdade(app, nome='Faculdade SP', codigo_emec='22222', uf='SP', cidade='São Paulo')
    _criar_faculdade(app, nome='Faculdade RJ', codigo_emec='22223', uf='RJ', cidade='Rio de Janeiro')
    r = client.get('/api/v1/instituicoes?uf=RJ')
    body = r.get_json()
    nomes = [i['nome'] for i in body['data']]
    assert 'Faculdade RJ' in nomes
    assert 'Faculdade SP' not in nomes


def test_v1_paginacao_respeita_limite_maximo(app, client):
    r = client.get('/api/v1/instituicoes?limit=500')
    body = r.get_json()
    assert body['meta']['limit'] == 100  # limite máximo é 100, mesmo pedindo mais


def test_v1_detalhe_por_codigo_emec(app, client):
    _criar_faculdade(app, nome='Faculdade Detalhe', codigo_emec='33333')
    r = client.get('/api/v1/instituicoes/33333')
    assert r.status_code == 200
    body = r.get_json()
    assert body['data']['nome'] == 'Faculdade Detalhe'
    assert body['data']['codigo_emec'] == '33333'


def test_v1_detalhe_404_quando_nao_existe(client):
    r = client.get('/api/v1/instituicoes/999999999')
    assert r.status_code == 404
    body = r.get_json()
    assert 'error' in body


def test_v1_nao_expoe_id_interno(app, client):
    """A API própria não deve vazar detalhes de implementação (id
    numérico interno, campo 'fonte' da importação) — só o que faz
    sentido pra quem consome de fora."""
    _criar_faculdade(app, nome='Faculdade Sem ID Interno', codigo_emec='44444')
    r = client.get('/api/v1/instituicoes/44444')
    body = r.get_json()
    assert 'id' not in body['data']
    assert 'fonte' not in body['data']
