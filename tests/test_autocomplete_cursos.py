"""Testes do autocomplete de nomes de curso (sugestões por prefixo) usado
no campo de busca de curso na home e em /faculdades."""


def _criar_curso(app, **kwargs):
    dados = {
        'nome': 'Engenharia de Software', 'instituicao': 'Instituição Teste', 'faculdade_id': None,
        'modalidade': 'presencial', 'descricao': '', 'duracao': '4 anos', 'grau': 'Bacharelado',
        'area': 'Computação', 'tipo_instituicao': 'Privada',
    }
    dados.update(kwargs)
    return app.Curso().criar(dados)


def test_sugestoes_por_prefixo(app):
    _criar_curso(app, nome='Engenharia de Software')
    _criar_curso(app, nome='Engenharia Civil')
    _criar_curso(app, nome='Engenharia Mecânica')
    _criar_curso(app, nome='Medicina')

    sugestoes = app.Curso().sugestoes_por_nome('Engenharia')
    assert 'Engenharia de Software' in sugestoes
    assert 'Engenharia Civil' in sugestoes
    assert 'Engenharia Mecânica' in sugestoes
    assert 'Medicina' not in sugestoes


def test_sugestoes_case_insensitive(app):
    _criar_curso(app, nome='Direito')
    sugestoes = app.Curso().sugestoes_por_nome('direi')
    assert 'Direito' in sugestoes


def test_sugestoes_nao_casa_no_meio_do_nome(app):
    """Prefixo, não 'contém' — 'oftware' não deve sugerir 'Engenharia de
    Software' (o termo não está no início do nome)."""
    _criar_curso(app, nome='Engenharia de Software')
    sugestoes = app.Curso().sugestoes_por_nome('oftware')
    assert sugestoes == []


def test_sugestoes_sem_duplicatas(app):
    """Mesmo curso oferecido por várias instituições (nomes iguais) deve
    aparecer uma única vez na lista de sugestões."""
    _criar_curso(app, nome='Pedagogia', instituicao='Instituição A')
    _criar_curso(app, nome='Pedagogia', instituicao='Instituição B')
    sugestoes = app.Curso().sugestoes_por_nome('Pedagogia')
    assert sugestoes.count('Pedagogia') == 1


def test_sugestoes_respeita_limite(app):
    for i in range(15):
        _criar_curso(app, nome=f'Curso Teste {i:02d}')
    sugestoes = app.Curso().sugestoes_por_nome('Curso Teste', limite=5)
    assert len(sugestoes) == 5


def test_sugestoes_termo_vazio_retorna_lista_vazia(app):
    assert app.Curso().sugestoes_por_nome('') == []
    assert app.Curso().sugestoes_por_nome('   ') == []


def test_sugestoes_escapa_curinga_like(app):
    """Um termo com '%' ou '_' (curingas do LIKE) não pode se comportar
    como wildcard — deve ser tratado como texto literal."""
    _criar_curso(app, nome='C# Avançado')
    sugestoes = app.Curso().sugestoes_por_nome('50%')  # não deve casar com nada por acidente
    assert sugestoes == []


def test_rota_sugestoes_retorna_lista(app, client):
    _criar_curso(app, nome='Arquitetura e Urbanismo')
    r = client.get('/api/cursos/sugestoes?q=Arquitetura')
    assert r.status_code == 200
    body = r.get_json()
    assert 'Arquitetura e Urbanismo' in body['sugestoes']


def test_rota_sugestoes_termo_curto_retorna_vazio(client):
    r = client.get('/api/cursos/sugestoes?q=a')
    body = r.get_json()
    assert body['sugestoes'] == []


def test_rota_sugestoes_sem_termo_retorna_vazio(client):
    r = client.get('/api/cursos/sugestoes')
    body = r.get_json()
    assert body['sugestoes'] == []
