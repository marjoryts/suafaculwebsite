"""Testes da importação de cursos via Censo da Educação Superior (INEP) —
deduplicação por polo de EAD, filtro de graduação, e vínculo com
instituições já cadastradas na base local."""
import io


HEADER = ("NU_ANO_CENSO;NO_MUNICIPIO;SG_UF;TP_DIMENSAO;TP_ORGANIZACAO_ACADEMICA;TP_REDE;"
          "TP_CATEGORIA_ADMINISTRATIVA;CO_IES;NO_CURSO;CO_CURSO;NO_CINE_AREA_GERAL;"
          "TP_GRAU_ACADEMICO;TP_MODALIDADE_ENSINO;TP_NIVEL_ACADEMICO\n")


def _linha(municipio='', uf='', dimensao='1', co_ies='417', nome='Pedagogia', co_curso='89380',
           area='Educação', grau='2', modalidade='2', nivel='1'):
    return f"2024;{municipio};{uf};{dimensao};1;2;4;{co_ies};{nome};{co_curso};{area};{grau};{modalidade};{nivel}\n"


def _csv_bytes(*linhas):
    return (HEADER + ''.join(linhas)).encode('latin-1')


def _criar_faculdade(app, **kwargs):
    dados = {
        'nome': 'Universidade Exemplo', 'sigla': 'UEX', 'organizacao_academica': 'Federal',
        'tipo_instituicao': 'Pública', 'url': '', 'endereco': '', 'cidade': 'Brasília', 'uf': 'DF',
        'telefone': '', 'email': '', 'situacao': 'ativa', 'fonte': 'manual', 'codigo_emec': '417',
    }
    dados.update(kwargs)
    return app.Faculdade().criar(dados)


def _cursos_por_codigo_inep(app, codigo_inep_curso):
    """Helper de teste: o banco já vem com cursos de exemplo (seed do
    init_db.py), então nunca dá pra assumir lista vazia — filtramos pelo
    codigo_inep_curso específico que cada teste importou."""
    return [c for c in app.Curso().listar({}) if c.get('codigo_inep_curso') == codigo_inep_curso]


def test_dedup_por_polo_de_ead_mantem_so_um_curso(app):
    """O mesmo CO_CURSO aparecendo em 5 polos de EAD (TP_DIMENSAO=2) mais
    uma linha consolidada (TP_DIMENSAO=3) deve virar UM único curso."""
    from app.services import censo_service
    _criar_faculdade(app)

    linhas = [_linha(dimensao='3')]  # linha consolidada, sem município — deve ser a escolhida
    for cidade in ['Anápolis', 'Anicuns', 'Aparecida de Goiânia', 'Caiapônia', 'Caldas Novas']:
        linhas.append(_linha(dimensao='2', municipio=cidade, uf='GO'))

    resultado = censo_service.importar_cursos_de_csv_upload(io.BytesIO(_csv_bytes(*linhas)))
    assert resultado['success'] is True
    assert resultado['cursos_no_arquivo'] == 1  # deduplicado pra 1 curso único
    assert resultado['criados'] == 1

    cursos = _cursos_por_codigo_inep(app, '89380')
    assert len(cursos) == 1
    assert cursos[0]['nome'] == 'Pedagogia'
    assert cursos[0]['modalidade'] == 'ead'


def test_prefere_dimensao_1_quando_nao_ha_dimensao_3(app):
    """Sem linha consolidada (DIM=3), usa a de sede (DIM=1) em vez de um polo qualquer."""
    from app.services import censo_service
    _criar_faculdade(app)

    linhas = [
        _linha(dimensao='2', municipio='Polo A', uf='GO', co_curso='999', nome='Administração', grau='1', modalidade='2'),
        _linha(dimensao='1', municipio='Brasília', uf='DF', co_curso='999', nome='Administração', grau='1', modalidade='1'),
    ]
    resultado = censo_service.importar_cursos_de_csv_upload(io.BytesIO(_csv_bytes(*linhas)))
    assert resultado['criados'] == 1

    curso = _cursos_por_codigo_inep(app, '999')[0]
    assert curso['modalidade'] == 'presencial'  # veio da linha DIM=1, não da DIM=2 (polo)


def test_ignora_cursos_sequenciais(app):
    """TP_NIVEL_ACADEMICO=2 (sequencial de formação específica) não é
    graduação — não deve ser importado."""
    from app.services import censo_service
    _criar_faculdade(app)

    linhas = [_linha(nivel='2', co_curso='555')]
    resultado = censo_service.importar_cursos_de_csv_upload(io.BytesIO(_csv_bytes(*linhas)))
    assert resultado['cursos_no_arquivo'] == 0
    assert _cursos_por_codigo_inep(app, '555') == []


def test_pula_curso_de_instituicao_nao_cadastrada(app):
    """CO_IES que não bate com nenhum codigo_emec local é contado, mas
    não vira registro em cursos (não podemos linkar a faculdade_id)."""
    from app.services import censo_service
    # nenhuma faculdade criada — CO_IES=417 não existe na base local

    linhas = [_linha()]
    resultado = censo_service.importar_cursos_de_csv_upload(io.BytesIO(_csv_bytes(*linhas)))
    assert resultado['cursos_no_arquivo'] == 1
    assert resultado['importados'] == 0
    assert resultado['sem_faculdade_local'] == 1
    assert _cursos_por_codigo_inep(app, '89380') == []


def test_decodifica_grau_e_area_corretamente(app):
    from app.services import censo_service
    _criar_faculdade(app)
    linhas = [_linha(co_curso='111', nome='Engenharia de Software', grau='1', area='Computação e TIC', modalidade='1')]
    censo_service.importar_cursos_de_csv_upload(io.BytesIO(_csv_bytes(*linhas)))

    curso = _cursos_por_codigo_inep(app, '111')[0]
    assert curso['grau'] == 'Bacharelado'
    assert curso['area'] == 'Computação e TIC'
    assert curso['modalidade'] == 'presencial'


def test_reimportacao_atualiza_em_vez_de_duplicar(app):
    """Rodar a importação duas vezes (ex.: Censo de dois anos, ou
    reenviar o mesmo arquivo) não deve criar cursos duplicados."""
    from app.services import censo_service
    _criar_faculdade(app)
    linhas = [_linha(co_curso='777', nome='Direito')]

    r1 = censo_service.importar_cursos_de_csv_upload(io.BytesIO(_csv_bytes(*linhas)))
    assert r1['criados'] == 1

    r2 = censo_service.importar_cursos_de_csv_upload(io.BytesIO(_csv_bytes(*linhas)))
    assert r2['criados'] == 0
    assert r2['atualizados'] == 1
    assert len(_cursos_por_codigo_inep(app, '777')) == 1


def test_rota_exige_admin(client):
    r = client.post('/api/cursos/censo/importar-csv', data={
        'arquivo': (io.BytesIO(_csv_bytes(_linha())), 'cursos.csv')
    }, content_type='multipart/form-data')
    assert r.status_code in (302, 401, 403)


def test_rota_funciona_logado_como_admin(app, admin_client):
    _criar_faculdade(app)
    r = admin_client.post('/api/cursos/censo/importar-csv', data={
        'arquivo': (io.BytesIO(_csv_bytes(_linha())), 'cursos.csv')
    }, content_type='multipart/form-data')
    body = r.get_json()
    assert body['success'] is True
    assert body['criados'] == 1


def test_v1_lista_cursos_da_instituicao(app, client):
    _criar_faculdade(app, codigo_emec='888')
    from app.services import censo_service
    linhas = [_linha(co_ies='888', co_curso='321', nome='Psicologia', grau='1', modalidade='1')]
    censo_service.importar_cursos_de_csv_upload(io.BytesIO(_csv_bytes(*linhas)))

    r = client.get('/api/v1/instituicoes/888/cursos')
    assert r.status_code == 200
    body = r.get_json()
    assert body['meta']['total'] == 1
    assert body['data'][0]['nome'] == 'Psicologia'
