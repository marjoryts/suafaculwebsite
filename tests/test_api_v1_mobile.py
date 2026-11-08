"""Etapa 4: API v1 para o Mobile — contrato, erros, isolamento e OpenAPI.
(Autenticação por token: tests/test_auth_tokens.py.)"""
import re

import pytest

RESPOSTAS_A = {f'q{i}': 'a' for i in range(1, 11)}


# ── Helpers ─────────────────────────────────────────────────────────────

def _logar(client, nome='ana', email='ana@x.com', senha='segredo1'):
    """Registra pela API e passa a enviar o access token em todas as requisições do client."""
    r = client.post('/api/v1/auth/registrar', json={'nome_usuario': nome, 'email': email, 'password': senha})
    assert r.status_code == 201, r.get_data(as_text=True)
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + r.get_json()['data']['tokens']['access_token']
    return client


def _segundo_cliente(app, nome, email):
    c = app.app.test_client()
    return _logar(c, nome, email)


def _curso(app, **kw):
    d = {'nome': 'Curso V1', 'instituicao': 'Inst V1', 'faculdade_id': None, 'modalidade': 'presencial',
         'descricao': 'desc', 'duracao': '4 anos', 'grau': 'Bacharelado', 'area': 'Tecnologia',
         'tipo_instituicao': 'Pública'}
    d.update(kw)
    return app.Curso().criar(d)['id']


def _faculdade(app, **kw):
    d = {'nome': 'Faculdade V1', 'sigla': 'FV1', 'organizacao_academica': 'Universidade',
         'tipo_instituicao': 'Pública', 'url': 'https://fv1.example', 'endereco': 'Rua 1', 'cidade': 'Campinas',
         'uf': 'SP', 'telefone': '', 'email': '', 'situacao': 'ativa', 'fonte': 'manual', 'codigo_emec': '777'}
    d.update(kw)
    return app.Faculdade().criar(d)['id']


def _vestibular(app, **kw):
    d = {'nome': 'Vest V1', 'instituicao': 'Inst', 'tipo_instituicao': 'Pública', 'cidade': 'X', 'regiao': 'Sul',
         'periodo_inscricao': 'ago', 'data_prova': '2031-05-10', 'descricao': 'd', 'link_edital': 'http://e'}
    d.update(kw)
    return app.Vestibular().criar(d)['id']


def _erro(resposta, status, code):
    assert resposta.status_code == status, resposta.get_data(as_text=True)
    corpo = resposta.get_json()
    assert set(corpo) == {'error'}
    assert corpo['error']['code'] == code
    assert corpo['error']['message']
    assert corpo['error']['request_id'] == resposta.headers['X-Request-ID']
    return corpo['error']


# ── Envelope de erros e request id ──────────────────────────────────────

def test_rota_inexistente_devolve_envelope_404(client):
    _erro(client.get('/api/v1/nao-existe'), 404, 'RESOURCE_NOT_FOUND')


def test_metodo_nao_permitido_devolve_envelope_405_com_allow(client):
    r = client.post('/api/v1/cursos', json={})
    _erro(r, 405, 'METHOD_NOT_ALLOWED')
    assert 'GET' in r.headers['Allow']


def test_request_id_do_cliente_e_devolvido_e_ids_invalidos_sao_substituidos(client):
    r = client.get('/api/v1/cursos', headers={'X-Request-ID': 'app-mobile-123'})
    assert r.headers['X-Request-ID'] == 'app-mobile-123'
    r = client.get('/api/v1/cursos', headers={'X-Request-ID': 'x' * 200})
    assert len(r.headers['X-Request-ID']) == 32  # id gerado (o enviado era inválido)
    assert client.get('/').headers['X-Request-ID']  # vale para o site inteiro


def test_erro_500_nao_vaza_detalhes_internos(app, client, monkeypatch):
    app.app.config['PROPAGATE_EXCEPTIONS'] = False

    def _explode(self, filtros={}):
        raise RuntimeError('SELECT * FROM segredo -- senha=123')
    monkeypatch.setattr(app.Curso, 'listar', _explode)
    r = client.get('/api/v1/cursos')
    _erro(r, 500, 'INTERNAL_ERROR')
    assert 'SELECT' not in r.get_data(as_text=True) and 'senha' not in r.get_data(as_text=True)


def test_contratos_fora_da_v1_nao_mudaram(client):
    # API legada continua HTTP 200 + {'success': False}; página 404 continua HTML
    r = client.post('/api/usuario/login', data={})
    assert r.status_code == 200 and r.get_json()['success'] is False
    r = client.get('/pagina-que-nao-existe')
    assert r.status_code == 404 and 'text/html' in r.content_type


def test_corpo_nao_json_e_rejeitado_com_415(client):
    _erro(client.post('/api/v1/teste-vocacional/resultados', data=RESPOSTAS_A), 415, 'UNSUPPORTED_MEDIA_TYPE')
    _logar(client)
    _erro(client.patch('/api/v1/me', data={'email': 'n@x.com'}), 415, 'UNSUPPORTED_MEDIA_TYPE')


# ── Catálogo ────────────────────────────────────────────────────────────

def test_cursos_lista_com_meta_e_dto_sem_colunas_internas(app, client):
    _curso(app, nome='Zeta Curso')
    corpo = client.get('/api/v1/cursos?busca=Zeta').get_json()
    assert set(corpo) == {'data', 'meta'}
    assert set(corpo['meta']) == {'total', 'page', 'limit', 'total_pages'}
    item = corpo['data'][0]
    assert item['nome'] == 'Zeta Curso'
    assert 'codigo_inep_curso' not in item and 'created_at' not in item and 'updated_at' not in item


def test_paginacao_limita_a_100_e_tolera_valores_invalidos(client):
    assert client.get('/api/v1/cursos?limit=9999').get_json()['meta']['limit'] == 100
    meta = client.get('/api/v1/cursos?page=abc&limit=xyz').get_json()['meta']
    assert meta['page'] == 1 and meta['limit'] == 20
    assert client.get('/api/v1/cursos?limit=-4').get_json()['meta']['limit'] == 1


def test_cursos_filtros_repetiveis(app, client):
    _curso(app, nome='Filtro EAD', modalidade='ead', area='Zzarea')
    _curso(app, nome='Filtro Pres', modalidade='presencial', area='Zzarea')
    nomes = lambda q: [c['nome'] for c in client.get('/api/v1/cursos?' + q).get_json()['data']]
    assert nomes('area=Zzarea&modalidade=ead') == ['Filtro EAD']
    assert sorted(nomes('area=Zzarea&modalidade=ead&modalidade=presencial')) == ['Filtro EAD', 'Filtro Pres']


def test_curso_detalhe_e_404_estruturado(app, client):
    cid = _curso(app, nome='Detalhe Curso')
    assert client.get(f'/api/v1/cursos/{cid}').get_json()['data']['nome'] == 'Detalhe Curso'
    _erro(client.get('/api/v1/cursos/99999999'), 404, 'RESOURCE_NOT_FOUND')
    _erro(client.get('/api/v1/cursos/abc'), 404, 'RESOURCE_NOT_FOUND')


def test_faculdades_lista_detalhe_e_filtros(app, client):
    fid = _faculdade(app, nome='Faculdade Detalhe V1', uf='RJ', cidade='Niterói', codigo_emec='888')
    _curso(app, nome='Curso Da Fac', faculdade_id=fid)
    lista = client.get('/api/v1/faculdades?uf=rj').get_json()  # UF em minúsculas é normalizada
    assert any(f['id'] == fid for f in lista['data'])
    assert 'fonte' not in lista['data'][0]
    det = client.get(f'/api/v1/faculdades/{fid}').get_json()['data']
    assert det['nome'] == 'Faculdade Detalhe V1' and det['total_cursos'] == 1
    assert [c['nome'] for c in det['cursos']] == ['Curso Da Fac']
    assert 'fonte' not in det and 'created_at' not in det
    _erro(client.get('/api/v1/faculdades/99999999'), 404, 'RESOURCE_NOT_FOUND')


def test_vestibulares_padrao_publico_status_e_filtro_de_mes(app, client):
    vid = _vestibular(app, nome='Vest Publico Mar', data_prova='2031-03-15')
    _vestibular(app, nome='Vest Privado Mar', data_prova='2031-03-20', tipo_instituicao='Privada')
    nomes = lambda q: [v['nome'] for v in client.get('/api/v1/vestibulares?' + q).get_json()['data']]
    assert 'Vest Publico Mar' in nomes('mes=3') and 'Vest Privado Mar' not in nomes('mes=3')
    assert 'Vest Privado Mar' in nomes('mes=3&incluir_privados=true')
    assert 'Vest Publico Mar' not in nomes('mes=4')
    assert client.get('/api/v1/vestibulares?mes=99&mes=x').status_code == 200  # valores inválidos ignorados
    det = client.get(f'/api/v1/vestibulares/{vid}').get_json()['data']
    assert det['status'] in ('nao_validado', 'ativo') and 'cadastrado_ok' not in det


def test_busca_sugestoes_formato(app, client):
    _faculdade(app, nome='Universidade Sugestão Zeta', sigla='USZ', codigo_emec='999')
    corpo = client.get('/api/v1/busca/sugestoes?q=zeta&tipos=faculdade').get_json()
    assert set(corpo['data']) == {'faculdade'} and corpo['meta']['termo'] == 'zeta'
    assert any('Sugestão Zeta' in i['rotulo'] for i in corpo['data']['faculdade'])
    assert client.get('/api/v1/busca/sugestoes?q=a').get_json()['meta']['total'] == 0  # termo curto


def test_instituicoes_erro_agora_usa_envelope_e_continua_sem_id_interno(app, client):
    _faculdade(app, nome='Inst Envelope', codigo_emec='4242')
    assert 'id' not in client.get('/api/v1/instituicoes/4242').get_json()['data']
    _erro(client.get('/api/v1/instituicoes/0000'), 404, 'RESOURCE_NOT_FOUND')
    assert client.get('/api/v1/instituicoes?page=abc').status_code == 200


def test_cache_publico_no_catalogo_e_no_store_no_privado(client):
    assert 's-maxage=300' in client.get('/api/v1/cursos').headers['Cache-Control']
    assert client.get('/api/v1/openapi.json').headers['Cache-Control'].startswith('public')
    r = client.get('/api/v1/me')
    assert r.status_code == 401 and r.headers['Cache-Control'] == 'no-store'
    _logar(client)
    assert client.get('/api/v1/me').headers['Cache-Control'] == 'no-store'


# ── Autenticação e perfil ───────────────────────────────────────────────

@pytest.mark.parametrize('metodo,url', [
    ('get', '/api/v1/me'), ('patch', '/api/v1/me'), ('get', '/api/v1/me/dashboard'),
    ('get', '/api/v1/favoritos'), ('put', '/api/v1/favoritos/curso/1'),
    ('delete', '/api/v1/favoritos/curso/1'), ('get', '/api/v1/teste-vocacional/resultados'),
    ('get', '/api/v1/teste-vocacional/recomendacoes'),
    ('post', '/api/v1/me/email'), ('post', '/api/v1/me/email/confirmar'),
])
def test_rotas_protegidas_exigem_autenticacao(client, metodo, url):
    kwargs = {'json': {'email': 'a@b.com'}} if metodo == 'patch' else {}
    _erro(getattr(client, metodo)(url, **kwargs), 401, 'UNAUTHENTICATED')


def test_me_devolve_dto_sem_dados_sensiveis(client):
    _logar(client)
    dado = client.get('/api/v1/me').get_json()['data']
    assert dado['nome_usuario'] == 'ana' and dado['email'] == 'ana@x.com' and dado['tipo'] == 'aluno'
    assert 'senha' not in dado and 'google_id' not in dado


def test_conta_removida_perde_acesso_imediatamente(app, client):
    from config.database import get_connection
    _logar(client)
    assert client.get('/api/v1/me').status_code == 200
    conn = get_connection()
    conn.execute("DELETE FROM usuarios WHERE nome_usuario='ana'")
    conn.commit()
    conn.close()
    _erro(client.get('/api/v1/me'), 401, 'INVALID_TOKEN')  # sessão do token deixou de existir


def test_patch_me_atualiza_apenas_campos_permitidos(client):
    _logar(client)
    r = client.patch('/api/v1/me', json={'nome_usuario': 'ana2', 'email': 'ana@x.com'})
    assert r.status_code == 200 and r.get_json()['data']['nome_usuario'] == 'ana2'
    # campo isolado mantém os demais
    assert client.patch('/api/v1/me', json={'nome_usuario': 'ana3'}).get_json()['data']['email'] == 'ana@x.com'
    # e-mail novo só com confirmação por código (POST /me/email)
    _erro(client.patch('/api/v1/me', json={'email': 'ana2@x.com'}), 422, 'EMAIL_CHANGE_REQUIRES_VERIFICATION')
    assert client.get('/api/v1/me').get_json()['data']['email'] == 'ana@x.com'


def test_patch_me_nao_permite_escalar_privilegio(client):
    _logar(client)
    erro = _erro(client.patch('/api/v1/me', json={'tipo': 'admin'}), 422, 'VALIDATION_ERROR')
    assert erro['details']['campos'] == ['tipo']
    assert client.get('/api/v1/me').get_json()['data']['tipo'] == 'aluno'


def test_patch_me_validacoes(app, client):
    _logar(client)
    _segundo_cliente(app, 'bia', 'bia@x.com')
    _erro(client.patch('/api/v1/me', json={}), 422, 'VALIDATION_ERROR')
    _erro(client.patch('/api/v1/me', json={'email': 'sem-arroba'}), 422, 'EMAIL_CHANGE_REQUIRES_VERIFICATION')
    _erro(client.patch('/api/v1/me', json={'nome_usuario': 'bia'}), 422, 'VALIDATION_ERROR')  # já em uso
    atual = {'password_atual': 'segredo1'}
    _erro(client.patch('/api/v1/me', json={'password': 'nova1234', 'password_confirm': 'outra', **atual}), 422, 'VALIDATION_ERROR')
    _erro(client.patch('/api/v1/me', json={'password': '123', 'password_confirm': '123', **atual}), 422, 'VALIDATION_ERROR')
    _erro(client.patch('/api/v1/me', json={'password': 'nova1234', 'password_confirm': 'nova1234'}), 422,
          'INVALID_CURRENT_PASSWORD')  # sem a senha atual
    _erro(client.patch('/api/v1/me', data='lixo', content_type='application/json'), 422, 'VALIDATION_ERROR')
    assert client.patch('/api/v1/me', json={'password': 'nova1234', 'password_confirm': 'nova1234', **atual}).status_code == 200


def test_dashboard_reaproveita_o_service_e_expoe_dto(app, client):
    _logar(client)
    vid = _vestibular(app, nome='Vest Dash', data_prova='2099-01-10')
    client.put(f'/api/v1/favoritos/vestibular/{vid}')
    client.post('/api/v1/teste-vocacional/resultados', json={'respostas': RESPOSTAS_A})
    d = client.get('/api/v1/me/dashboard').get_json()['data']
    assert d['contagem_favoritos'] == {'cursos': 0, 'faculdades': 0, 'vestibulares': 1}
    assert d['proximas_provas'][0]['nome'] == 'Vest Dash'
    assert d['ultimo_teste']['perfil'] == 'tecnico'
    assert 'senha' not in d['usuario'] and 'id' not in d['favoritos_recentes'][0]


# ── Favoritos ───────────────────────────────────────────────────────────

def test_favoritar_e_idempotente_e_o_nome_vem_do_banco(app, client):
    _logar(client)
    cid = _curso(app, nome='Nome Real Do Banco')
    r = client.put(f'/api/v1/favoritos/curso/{cid}', json={'nome_item': 'nome forjado'})
    assert r.status_code == 201 and r.get_json()['data']['nome_item'] == 'Nome Real Do Banco'
    r2 = client.put(f'/api/v1/favoritos/curso/{cid}')
    assert r2.status_code == 200 and r2.get_json()['data']['item_id'] == cid
    assert len(client.get('/api/v1/favoritos?tipo=curso').get_json()['data']) == 1


def test_desfavoritar_e_idempotente(app, client):
    _logar(client)
    cid = _curso(app)
    client.put(f'/api/v1/favoritos/curso/{cid}')
    assert client.delete(f'/api/v1/favoritos/curso/{cid}').status_code == 204
    r = client.delete(f'/api/v1/favoritos/curso/{cid}')
    assert r.status_code == 204 and r.get_data() == b''
    assert client.get('/api/v1/favoritos').get_json()['data'] == []


def test_favoritos_validam_tipo_e_existencia_do_item(client):
    _logar(client)
    _erro(client.put('/api/v1/favoritos/foo/1'), 422, 'VALIDATION_ERROR')
    _erro(client.put('/api/v1/favoritos/curso/99999999'), 404, 'RESOURCE_NOT_FOUND')
    _erro(client.delete('/api/v1/favoritos/foo/1'), 422, 'VALIDATION_ERROR')
    _erro(client.get('/api/v1/favoritos?tipo=foo'), 422, 'VALIDATION_ERROR')


def test_favoritos_sao_isolados_por_usuario(app, client):
    _logar(client)
    outro = _segundo_cliente(app, 'bia', 'bia@x.com')
    cid = _curso(app)
    client.put(f'/api/v1/favoritos/curso/{cid}')
    assert outro.get('/api/v1/favoritos').get_json()['data'] == []
    outro.delete(f'/api/v1/favoritos/curso/{cid}')  # não remove o favorito da ana
    assert len(client.get('/api/v1/favoritos').get_json()['data']) == 1


def test_favoritar_faculdade_e_vestibular(app, client):
    _logar(client)
    fid, vid = _faculdade(app, codigo_emec='555'), _vestibular(app)
    assert client.put(f'/api/v1/favoritos/faculdade/{fid}').status_code == 201
    assert client.put(f'/api/v1/favoritos/vestibular/{vid}').status_code == 201
    assert {f['tipo'] for f in client.get('/api/v1/favoritos').get_json()['data']} == {'faculdade', 'vestibular'}


# ── Teste vocacional ────────────────────────────────────────────────────

def test_teste_perguntas_publicas(client):
    corpo = client.get('/api/v1/teste-vocacional/perguntas').get_json()
    assert len(corpo['data']['secoes']) == 5 and 'perfis' not in str(corpo)  # sem pesos


def test_teste_anonimo_recebe_resultado_e_nao_tem_historico(client):
    r = client.post('/api/v1/teste-vocacional/resultados', json={'respostas': RESPOSTAS_A})
    assert r.status_code == 201
    dado = r.get_json()['data']
    assert [p['chave'] for p in dado['perfis']] == ['tecnico'] and dado['salvo'] is True
    _erro(client.get('/api/v1/teste-vocacional/resultados'), 401, 'UNAUTHENTICATED')


def test_teste_logado_salva_no_historico(client):
    _logar(client)
    client.post('/api/v1/teste-vocacional/resultados', json={'respostas': RESPOSTAS_A})
    hist = client.get('/api/v1/teste-vocacional/resultados').get_json()
    assert hist['meta']['total'] == 1 and hist['data'][0]['perfil_nome'] == 'Perfil Técnico / Exato'


def test_teste_validacoes(client):
    erro = _erro(client.post('/api/v1/teste-vocacional/resultados', json={'respostas': {'q1': 'a'}}),
                 422, 'VALIDATION_ERROR')
    assert 'q2' in erro['details']['perguntas_sem_resposta']
    _erro(client.post('/api/v1/teste-vocacional/resultados', json={'respostas': {**RESPOSTAS_A, 'q3': 'zz'}}),
          422, 'VALIDATION_ERROR')
    _erro(client.post('/api/v1/teste-vocacional/resultados', json={'respostas': 'x'}), 422, 'VALIDATION_ERROR')
    _erro(client.post('/api/v1/teste-vocacional/resultados', json=[1, 2]), 422, 'VALIDATION_ERROR')


# ── Escopo e OpenAPI ────────────────────────────────────────────────────

def _rotas_v1(app):
    achadas = set()
    for regra in app.app.url_map.iter_rules():
        if regra.rule.startswith('/api/v1/'):
            caminho = re.sub(r'<(?:\w+:)?(\w+)>', r'{\1}', regra.rule[len('/api/v1'):])
            for metodo in regra.methods - {'HEAD', 'OPTIONS'}:
                achadas.add((caminho, metodo.lower()))
    return achadas


def test_operacoes_administrativas_so_existem_sob_admin(app):
    """Alterar o catálogo ou importar dados só é possível em /admin/* (que exige
    conta admin — ver tests/test_api_v1_admin.py); as rotas públicas só leem."""
    for caminho, metodo in _rotas_v1(app):
        if caminho.startswith('/admin/'):
            continue
        assert 'admin' not in caminho and 'importa' not in caminho, caminho
        assert not (metodo in ('post', 'put', 'patch', 'delete') and caminho.split('/')[1] in
                    ('cursos', 'faculdades', 'vestibulares', 'instituicoes')), (caminho, metodo)


def test_openapi_descreve_todas_as_rotas(app, client):
    spec = client.get('/api/v1/openapi.json').get_json()
    assert spec['openapi'].startswith('3.')
    documentadas = {(c, m) for c, ops in spec['paths'].items() for m in ops}
    assert documentadas == _rotas_v1(app)


def test_openapi_referencias_resolvem_e_seguranca_confere(app, client):
    spec = client.get('/api/v1/openapi.json').get_json()
    bruto = client.get('/api/v1/openapi.json').get_data(as_text=True)
    for ref in set(re.findall(r'"\$ref":\s*"#/components/(\w+)/(\w+)"', bruto)):
        assert ref[1] in spec['components'][ref[0]], ref
    protegidas = {('/me', 'get'), ('/me', 'patch'), ('/me/dashboard', 'get'), ('/favoritos', 'get'),
                  ('/favoritos/{tipo}/{item_id}', 'put'), ('/favoritos/{tipo}/{item_id}', 'delete'),
                  ('/teste-vocacional/resultados', 'get'), ('/teste-vocacional/recomendacoes', 'get'),
                  ('/me/email', 'post'), ('/me/email/confirmar', 'post')}
    for caminho, ops in spec['paths'].items():
        for metodo, op in ops.items():
            protegida = (caminho, metodo) in protegidas or caminho.startswith('/admin/')
            assert bool(op['security']) == protegida, (caminho, metodo)


# ── Favoritos com resumo do item e cursos recomendados com id (Etapa 7) ─────

def test_favoritos_trazem_resumo_do_item_por_tipo(app, client):
    _logar(client)
    cid = _curso(app, nome='Curso Resumo', area='Saúde')
    fid = _faculdade(app, nome='Faculdade Resumo', sigla='FR', cidade='Recife', uf='PE', codigo_emec='9001')
    vid = _vestibular(app, nome='Vest Resumo', data_prova='2031-08-09')
    for tipo, i in (('curso', cid), ('faculdade', fid), ('vestibular', vid)):
        client.put(f'/api/v1/favoritos/{tipo}/{i}')
    por_tipo = {f['tipo']: f for f in client.get('/api/v1/favoritos').get_json()['data']}
    assert por_tipo['curso']['item'] == {'id': cid, 'nome': 'Curso Resumo', 'instituicao': 'Inst V1', 'area': 'Saúde',
                                         'modalidade': 'presencial', 'grau': 'Bacharelado', 'duracao': '4 anos'}
    assert por_tipo['faculdade']['item']['cidade'] == 'Recife' and por_tipo['faculdade']['item']['uf'] == 'PE'
    assert por_tipo['vestibular']['item']['data_prova'] == '2031-08-09' and 'status' in por_tipo['vestibular']['item']
    assert 'fonte' not in por_tipo['faculdade']['item'] and 'cadastrado_ok' not in por_tipo['vestibular']['item']


def test_put_de_favorito_tambem_devolve_o_item(app, client):
    _logar(client)
    cid = _curso(app, nome='Curso Put')
    assert client.put(f'/api/v1/favoritos/curso/{cid}').get_json()['data']['item']['nome'] == 'Curso Put'


def test_favorito_de_item_removido_vem_com_item_nulo(app, client):
    from config.database import get_connection
    _logar(client)
    cid = _curso(app, nome='Curso Efemero')
    client.put(f'/api/v1/favoritos/curso/{cid}')
    conn = get_connection()
    conn.execute("DELETE FROM cursos WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    f = client.get('/api/v1/favoritos').get_json()['data'][0]
    assert f['nome_item'] == 'Curso Efemero' and f['item'] is None


def test_lista_de_favoritos_faz_uma_consulta_por_tipo_e_nao_uma_por_item(app, client, monkeypatch):
    _logar(client)
    for i in range(5):
        client.put(f'/api/v1/favoritos/curso/{_curso(app, nome=f"Curso Lote {i}")}')
    chamadas = []
    original = app.Curso.resumos_por_ids
    monkeypatch.setattr(app.Curso, 'resumos_por_ids', lambda self, ids: (chamadas.append(len(list(ids))), original(self, ids))[1])
    assert len(client.get('/api/v1/favoritos?tipo=curso').get_json()['data']) == 5
    assert chamadas == [5]  # uma única consulta para os 5 cursos


def test_cursos_recomendados_do_teste_trazem_id_que_abre_o_detalhe(app, client):
    r = client.post('/api/v1/teste-vocacional/resultados', json={'respostas': RESPOSTAS_A}).get_json()['data']
    sugeridos = r['perfis'][0]['cursos_sugeridos']
    assert sugeridos and all(set(c) == {'id', 'nome', 'instituicao'} for c in sugeridos)
    for c in sugeridos:  # cada id sugerido abre o detalhe do mesmo curso
        detalhe = client.get(f"/api/v1/cursos/{c['id']}").get_json()['data']
        assert detalhe['nome'] == c['nome'] and detalhe['instituicao'] == c['instituicao']


def test_v1_vestibulares_tem_campos_novos_e_filtro_de_varias_regioes(client):
    """Integração com a atualização do site: taxa, cursos oferecidos e requisitos
    chegam ao app, e ?regiao= pode repetir (como no filtro da página web)."""
    dados = client.get('/api/v1/vestibulares?incluir_privados=true&limit=100').get_json()
    assert {'taxa_inscricao', 'cursos_oferecidos', 'requisitos'} <= set(dados['data'][0])
    duas = client.get('/api/v1/vestibulares?incluir_privados=true&limit=100&regiao=Sudeste&regiao=Sul').get_json()
    regioes = {v['regiao'] for v in duas['data']}
    assert regioes and regioes <= {'Sudeste', 'Sul'}
    so_sul = client.get('/api/v1/vestibulares?incluir_privados=true&limit=100&regiao=Sul').get_json()
    assert so_sul['meta']['total'] < duas['meta']['total']


def test_teste_recomendacoes_com_compatibilidade(client):
    """Mesma regra da página de resultado do site: cursos por compatibilidade (%),
    só para a própria conta."""
    _erro(client.get('/api/v1/teste-vocacional/recomendacoes'), 401, 'UNAUTHENTICATED')
    _logar(client)
    _erro(client.get('/api/v1/teste-vocacional/recomendacoes'), 404, 'RESOURCE_NOT_FOUND')  # ainda sem teste

    enviado = client.post('/api/v1/teste-vocacional/resultados', json={'respostas': RESPOSTAS_A}).get_json()['data']
    assert enviado['resultado_id'] and sum(p['percentual'] for p in enviado['pontuacoes']) in range(98, 103)

    rec = client.get(f"/api/v1/teste-vocacional/recomendacoes?id={enviado['resultado_id']}&limite=5").get_json()['data']
    assert rec['resultado_id'] == enviado['resultado_id'] and rec['perfil'] == 'tecnico'
    assert 0 < len(rec['cursos']) <= 5
    pct = [c['compatibilidade'] for c in rec['cursos']]
    assert pct == sorted(pct, reverse=True) and all(1 <= p <= 100 for p in pct)
    assert {'id', 'nome', 'area', 'criterio', 'total_instituicoes'} <= set(rec['cursos'][0])


def test_teste_recomendacoes_nao_expoe_resultado_de_outra_conta(app, client):
    _logar(client)
    id_ana = client.post('/api/v1/teste-vocacional/resultados', json={'respostas': RESPOSTAS_A}).get_json()['data']['resultado_id']
    outro = _segundo_cliente(app, 'bia', 'bia@x.com')
    _erro(outro.get(f'/api/v1/teste-vocacional/recomendacoes?id={id_ana}'), 404, 'RESOURCE_NOT_FOUND')
