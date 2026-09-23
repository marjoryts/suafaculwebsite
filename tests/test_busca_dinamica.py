"""Testes da busca dinâmica (/api/busca/sugestoes): sugestões de
localizações, faculdades e cursos a partir dos dados do banco, por parte do
nome e sem diferenciar acentos; e o filtro de localização de /faculdades
aceitando cidade, sigla de UF e região."""


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


def _criar_curso(app, **kwargs):
    dados = {
        'nome': 'Curso Teste', 'instituicao': 'Instituição Teste', 'faculdade_id': None,
        'modalidade': 'presencial', 'descricao': '', 'duracao': '4 anos', 'grau': 'Bacharelado',
        'area': 'Tecnologia', 'tipo_instituicao': 'Pública',
    }
    dados.update(kwargs)
    return app.Curso().criar(dados)


def _sugestoes(client, q, **extra):
    params = {'q': q, **extra}
    r = client.get('/api/busca/sugestoes', query_string=params)
    assert r.status_code == 200
    body = r.get_json()
    assert body['success'] is True
    return body['resultados']


def _rotulos(itens):
    return [i['rotulo'] for i in itens]


def test_localizacao_por_parte_do_nome(app, client):
    _criar_faculdade(app, nome='Faculdade Bernardense', sigla='FBER',
                     cidade='São Bernardo do Campo', uf='SP')
    res = _sugestoes(client, 'São')
    cidades = [i for i in res['local'] if i['subtipo'] == 'cidade']
    assert 'São Bernardo do Campo' in _rotulos(cidades)
    item = next(i for i in cidades if i['rotulo'] == 'São Bernardo do Campo')
    assert item['campo'] == 'cidade'
    assert item['valor'] == 'São Bernardo do Campo'


def test_busca_ignora_acentos_e_maiusculas(app, client):
    _criar_faculdade(app, nome='Instituto Joseense', sigla='IJOS',
                     cidade='São José dos Campos', uf='SP')
    for termo in ('sao jose', 'SÃO JOSÉ', 'São José'):
        res = _sugestoes(client, termo)
        assert 'São José dos Campos' in _rotulos(res['local']), termo


def test_faculdade_por_nome_parcial_e_sigla(app, client):
    _criar_faculdade(app, nome='Universidade Tecnológica Imaginária', sigla='UTIMG')
    assert 'Universidade Tecnológica Imaginária' in _rotulos(_sugestoes(client, 'Imaginária')['faculdade'])
    assert 'Universidade Tecnológica Imaginária' in _rotulos(_sugestoes(client, 'tecnologica imag')['faculdade'])
    item = _sugestoes(client, 'utimg')['faculdade'][0]
    assert item['rotulo'] == 'Universidade Tecnológica Imaginária'
    assert item['campo'] == 'faculdade'


def test_curso_por_parte_do_nome_sem_duplicatas(app, client):
    _criar_curso(app, nome='Bioengenharia Marinha', instituicao='A')
    _criar_curso(app, nome='Bioengenharia Marinha', instituicao='B')
    res = _sugestoes(client, 'engenharia mar')
    assert _rotulos(res['curso']).count('Bioengenharia Marinha') == 1
    item = next(i for i in res['curso'] if i['rotulo'] == 'Bioengenharia Marinha')
    assert item['campo'] == 'curso'
    assert '2 instituições' in item['detalhe']


def test_prefixo_vem_antes_de_meio_do_nome(app, client):
    _criar_curso(app, nome='Zootecnia Aplicada')
    _criar_curso(app, nome='Gestão de Zootecnia')
    rotulos = _rotulos(_sugestoes(client, 'zootec')['curso'])
    assert rotulos.index('Zootecnia Aplicada') < rotulos.index('Gestão de Zootecnia')


def test_estado_e_regiao_derivados_das_faculdades(app, client):
    _criar_faculdade(app, nome='Universidade do Acre Teste', sigla='UACT', cidade='Rio Branco', uf='AC')
    estados = [i for i in _sugestoes(client, 'acre')['local'] if i['subtipo'] == 'estado']
    assert estados and estados[0]['valor'] == 'AC'
    regioes = [i for i in _sugestoes(client, 'norte')['local'] if i['subtipo'] == 'regiao']
    assert regioes and regioes[0]['valor'] == 'Norte'


def test_sem_resultado_retorna_listas_vazias(client):
    res = _sugestoes(client, 'xyzqwk-nao-existe')
    assert res == {'local': [], 'faculdade': [], 'curso': []}


def test_termo_curto_nao_busca(client):
    res = _sugestoes(client, 'a')
    assert all(v == [] for v in res.values())


def test_curinga_like_e_texto_literal(client):
    res = _sugestoes(client, '%%')
    assert all(v == [] for v in res.values())


def test_filtro_por_tipos_e_limite(app, client):
    for i in range(8):
        _criar_curso(app, nome=f'Oceanografia Nível {i}')
    res = _sugestoes(client, 'oceanografia', tipos='curso', limite=3)
    assert list(res.keys()) == ['curso']
    assert len(res['curso']) == 3


def test_listagem_filtra_por_sigla_de_uf_e_regiao(app, client):
    _criar_faculdade(app, nome='Universidade Amapaense Teste', sigla='UAPT', cidade='Macapá', uf='AP')
    por_uf = client.get('/api/faculdades/listar?cidade=AP').get_json()['faculdades']
    assert [f['nome'] for f in por_uf] == ['Universidade Amapaense Teste']
    por_regiao = [f['nome'] for f in client.get('/api/faculdades/listar?cidade=Norte&limit=100').get_json()['faculdades']]
    assert 'Universidade Amapaense Teste' in por_regiao
    assert all(f['uf'] in ('AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO')
               for f in client.get('/api/faculdades/listar?cidade=Norte&limit=100').get_json()['faculdades'])


def test_listagem_cidade_ignora_acentos(app, client):
    _criar_faculdade(app, nome='Faculdade Maringaense Teste', sigla='FMT', cidade='Maringá', uf='PR')
    nomes = [f['nome'] for f in client.get('/api/faculdades/listar?cidade=maringa').get_json()['faculdades']]
    assert 'Faculdade Maringaense Teste' in nomes
