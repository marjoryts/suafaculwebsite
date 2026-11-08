"""Especificação OpenAPI 3.0 da API v1, servida em GET /api/v1/openapi.json.

Escrita à mão (sem dependências extras). O teste `test_openapi_descreve_todas_as_rotas`
falha se uma rota for criada/removida sem atualizar este arquivo.
"""
from flask import jsonify

from app.api.v1 import bp
from app.api.v1.http import cache_publico

_REF = lambda nome: {'$ref': f'#/components/schemas/{nome}'}
_STR = {'type': 'string'}
_STR_N = {'type': 'string', 'nullable': True}
_INT = {'type': 'integer'}


def _obj(**props):
    return {'type': 'object', 'properties': props}


SCHEMAS = {
    'Erro': _obj(error=_obj(
        code={'type': 'string', 'example': 'RESOURCE_NOT_FOUND',
              'enum': ['BAD_REQUEST', 'UNAUTHENTICATED', 'FORBIDDEN', 'RESOURCE_NOT_FOUND',
                       'METHOD_NOT_ALLOWED', 'UNSUPPORTED_MEDIA_TYPE', 'VALIDATION_ERROR', 'CONFLICT',
                       'INVALID_CREDENTIALS', 'INVALID_TOKEN', 'TOKEN_EXPIRED', 'INVALID_REFRESH_TOKEN',
                       'REFRESH_TOKEN_EXPIRED', 'REFRESH_TOKEN_REUSED', 'INTERNAL_ERROR']},
        message=_STR, request_id=_STR,
        details={'type': 'object', 'description': 'Opcional; dados adicionais do erro.'})),
    'Tokens': _obj(
        token_type={'type': 'string', 'example': 'Bearer'},
        access_token={'type': 'string', 'description': 'Curta duração (expires_in segundos, 15 min). Envie em Authorization: Bearer.'},
        expires_in={'type': 'integer', 'example': 900},
        refresh_token={'type': 'string', 'description': 'Uso único. Guarde em armazenamento seguro; cada /auth/refresh devolve um novo.'},
        refresh_expires_in={'type': 'integer', 'example': 2592000}),
    'Sessao': _obj(usuario=_REF('Usuario'), tokens=_REF('Tokens')),
    'Paginacao': _obj(total=_INT, page=_INT, limit=_INT, total_pages=_INT),
    'Curso': _obj(id=_INT, nome=_STR, instituicao=_STR, faculdade_id={'type': 'integer', 'nullable': True},
                  modalidade=_STR, descricao=_STR_N, duracao=_STR_N, grau=_STR_N, area=_STR_N,
                  tipo_instituicao=_STR),
    'CursoResumo': _obj(id=_INT, nome=_STR, modalidade=_STR, grau=_STR_N, area=_STR_N),
    'Vestibular': _obj(id=_INT, nome=_STR, instituicao=_STR_N, faculdade_id={'type': 'integer', 'nullable': True},
                       tipo_instituicao=_STR, cidade=_STR_N, regiao=_STR_N, periodo_inscricao=_STR_N,
                       data_prova={'type': 'string', 'nullable': True, 'example': '2026-11-01'},
                       descricao=_STR_N, link_edital=_STR_N,
                       taxa_inscricao=_STR_N, cursos_oferecidos=_STR_N, requisitos=_STR_N,
                       status={'type': 'string', 'nullable': True,
                               'enum': ['ativo', 'encerrado', 'data_invalida', 'nao_validado']}),
    'VestibularResumo': _obj(id=_INT, nome=_STR, data_prova=_STR_N, periodo_inscricao=_STR_N, link_edital=_STR_N),
    'Faculdade': _obj(id=_INT, codigo_emec=_STR_N, nome=_STR, sigla=_STR_N, organizacao_academica=_STR_N,
                      tipo_instituicao=_STR, url=_STR_N, endereco=_STR_N, cidade=_STR_N, uf=_STR_N,
                      telefone=_STR_N, email=_STR_N, situacao=_STR_N, total_cursos=_INT),
    'FaculdadeDetalhe': {'allOf': [_REF('Faculdade'), _obj(
        cursos={'type': 'array', 'items': _REF('CursoResumo')},
        vestibulares={'type': 'array', 'items': _REF('VestibularResumo')})]},
    'Instituicao': _obj(codigo_emec=_STR, nome=_STR, sigla=_STR_N, organizacao_academica=_STR_N,
                        tipo_instituicao=_STR, situacao=_STR_N, cidade=_STR_N, uf=_STR_N, endereco=_STR_N,
                        telefone=_STR_N, email=_STR_N, url=_STR_N, total_cursos_cadastrados=_INT),
    'Favorito': _obj(tipo={'type': 'string', 'enum': ['curso', 'faculdade', 'vestibular']}, item_id=_INT,
                     nome_item=_STR, created_at=_STR,
                     item={'type': 'object', 'nullable': True,
                           'description': ('Resumo do item favoritado (campos conforme o tipo: curso, faculdade ou '
                                           'vestibular); null se o item foi removido. Presente em GET /favoritos e '
                                           'PUT /favoritos/{tipo}/{item_id}.')}),
    'UsuarioAdmin': _obj(id=_INT, nome_usuario=_STR, email=_STR, tipo={'type': 'string', 'enum': ['aluno', 'admin']}),
    'FaculdadeEntrada': _obj(**{c: _STR for c in ('codigo_emec', 'nome', 'sigla', 'organizacao_academica',
                                                 'tipo_instituicao', 'url', 'endereco', 'cidade', 'uf',
                                                 'telefone', 'email', 'situacao')}),
    'Usuario': _obj(id=_INT, nome_usuario=_STR, email=_STR, tipo={'type': 'string', 'enum': ['aluno', 'admin']},
                    avatar_url=_STR_N, auth_provider=_STR, created_at=_STR),
    'Questionario': _obj(secoes={'type': 'array', 'items': _obj(
        titulo=_STR, perguntas={'type': 'array', 'items': _obj(
            id={'type': 'string', 'example': 'q1'}, texto=_STR,
            opcoes={'type': 'array', 'items': _obj(id={'type': 'string', 'example': 'a'}, texto=_STR)})})}),
    'TesteResultado': _obj(
        resultado_id={'type': 'integer', 'nullable': True, 'description': 'Use em GET /teste-vocacional/recomendacoes?id=.'},
        scores={'type': 'object', 'additionalProperties': _INT},
        pontuacoes={'type': 'array', 'items': _obj(chave=_STR, nome=_STR, percentual=_INT)},
        perfis={'type': 'array', 'items': _obj(
            chave=_STR, nome=_STR, descricao=_STR, areas={'type': 'array', 'items': _STR},
            cursos_sugeridos={'type': 'array', 'items': _obj(id={'type': 'integer', 'description': 'Use em GET /cursos/{id}.'}, nome=_STR, instituicao=_STR)})},
        salvo={'type': 'boolean', 'description': 'true se o resultado foi gravado (sempre que há perfil).'}),
    'Recomendacoes': _obj(
        resultado_id=_INT, perfil=_STR, perfil_nome=_STR, perfil_descricao=_STR_N, created_at=_STR,
        cursos={'type': 'array', 'items': _obj(
            id=_INT, nome=_STR, area=_STR_N, grau=_STR_N, descricao=_STR_N,
            compatibilidade={'type': 'integer', 'minimum': 1, 'maximum': 100},
            perfis={'type': 'array', 'items': _STR},
            criterio={'type': 'string', 'enum': ['nome', 'area']}, total_instituicoes=_INT)},
        total_compativeis=_INT, sem_dados_suficientes=_INT, total_cursos_analisados=_INT),
    'TesteHistoricoItem': _obj(
        id=_INT, perfil=_STR, perfil_nome=_STR, created_at=_STR,
        pontuacoes={'type': 'array', 'items': _obj(chave=_STR, nome=_STR, percentual=_INT)}),
    'Dashboard': _obj(
        usuario=_REF('Usuario'),
        contagem_favoritos=_obj(cursos=_INT, faculdades=_INT, vestibulares=_INT),
        favoritos_recentes={'type': 'array', 'items': _REF('Favorito')},
        proximas_provas={'type': 'array', 'items': _obj(
            id=_INT, nome=_STR, instituicao=_STR_N, cidade=_STR_N, regiao=_STR_N, data_prova=_STR,
            periodo_inscricao=_STR_N, link_edital=_STR_N)},
        testes_vocacionais={'type': 'array', 'items': _REF('TesteHistoricoItem')},
        ultimo_teste={'allOf': [_REF('TesteHistoricoItem')], 'nullable': True}),
}

RESPOSTAS_ERRO = {
    'Erro409': {'description': 'Conflito (CONFLICT), ex.: e-mail ou nome de usuário já cadastrado.',
                'content': {'application/json': {'schema': _REF('Erro')}}},
    'Erro401': {'description': ('Não autenticado. error.code: UNAUTHENTICATED (sem token), TOKEN_EXPIRED (renove com '
                                '/auth/refresh), INVALID_TOKEN, INVALID_CREDENTIALS, INVALID_REFRESH_TOKEN, '
                                'REFRESH_TOKEN_EXPIRED ou REFRESH_TOKEN_REUSED (sessão revogada: faça login). '
                                'Traz o cabeçalho WWW-Authenticate: Bearer.'),
                'content': {'application/json': {'schema': _REF('Erro')}}},
    'Erro403': {'description': 'Sem permissão (FORBIDDEN), ex.: rota de administrador com conta de aluno.',
                'content': {'application/json': {'schema': _REF('Erro')}}},
    'Erro503': {'description': 'Serviço indisponível (ex.: GOOGLE_NOT_CONFIGURED).',
                'content': {'application/json': {'schema': _REF('Erro')}}},
    'Erro404': {'description': 'Recurso não encontrado (RESOURCE_NOT_FOUND).',
                'content': {'application/json': {'schema': _REF('Erro')}}},
    'Erro415': {'description': 'Corpo não é application/json (UNSUPPORTED_MEDIA_TYPE).',
                'content': {'application/json': {'schema': _REF('Erro')}}},
    'Erro422': {'description': 'Dados inválidos (VALIDATION_ERROR); veja error.details.',
                'content': {'application/json': {'schema': _REF('Erro')}}},
}


def _ref_resp(*codigos):
    return {str(c): {'$ref': f'#/components/responses/Erro{c}'} for c in codigos}


def _ok(schema, descricao='Sucesso.'):
    return {'description': descricao, 'content': {'application/json': {'schema': schema}}}


def _data(schema):
    return _obj(data=schema)


def _lista(schema):
    return _obj(data={'type': 'array', 'items': schema}, meta=_REF('Paginacao'))


def _p(nome, onde='query', tipo=None, descricao=''):
    return {'name': nome, 'in': onde, 'required': onde == 'path', 'description': descricao,
            'schema': tipo or _STR}


PAGINA = [_p('page', tipo={'type': 'integer', 'minimum': 1, 'default': 1}),
          _p('limit', tipo={'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 20})]
SEGURO = [{'bearerAuth': []}]


def _op(resumo, tag, resposta, params=(), erros=(), seguro=False, corpo=None, codigo='200', descricao=''):
    op = {'summary': resumo, 'tags': [tag], 'parameters': list(params),
          'responses': {codigo: resposta, **_ref_resp(*erros)}}
    if descricao:
        op['description'] = descricao
    if seguro:
        op['security'] = SEGURO
        op['responses'].update(_ref_resp(401))
    else:
        op['security'] = []
    if corpo:
        op['requestBody'] = {'required': True, 'content': {'application/json': {'schema': corpo}}}
    return op


TIPO_FAV = _p('tipo', 'path', {'type': 'string', 'enum': ['curso', 'faculdade', 'vestibular']})
ITEM_ID = _p('item_id', 'path', _INT)

PATHS = {
    '/auth/registrar': {'post': _op(
        'Cria a conta (e-mail + senha) e abre uma sessão', 'Autenticação', _ok(_data(_REF('Sessao'))),
        erros=(409, 415, 422), codigo='201',
        corpo=_obj(nome_usuario=_STR, email=_STR, password={'type': 'string', 'minLength': 6}),
        descricao='Conta criada como aluno. Senha com pelo menos 6 caracteres.')},
    '/auth/login': {'post': _op(
        'Login por e-mail e senha', 'Autenticação', _ok(_data(_REF('Sessao'))), erros=(401, 415, 422),
        corpo=_obj(email=_STR, password=_STR),
        descricao='Abre uma sessão nova (um dispositivo = uma sessão). A mesma resposta 401 INVALID_CREDENTIALS '
                  'vale para e-mail inexistente e senha errada.')},
    '/auth/google': {'post': _op(
        'Entra com Google (ID token)', 'Autenticação', _ok(_data(_REF('Sessao'))), erros=(403, 415, 422, 503),
        corpo=_obj(id_token={'type': 'string', 'description': 'ID token do Google Sign-In (audiência: um dos client IDs do projeto).'}),
        descricao='Valida assinatura, emissor, audiência e validade. 401 INVALID_GOOGLE_TOKEN se inválido; '
                  '403 EMAIL_NOT_VERIFIED se o e-mail de uma conta existente não for verificado; '
                  '503 GOOGLE_NOT_CONFIGURED sem client IDs no servidor.')},
    '/auth/refresh': {'post': _op(
        'Renova os tokens (rotação)', 'Autenticação', _ok(_data(_obj(tokens=_REF('Tokens')))),
        erros=(401, 415, 422), corpo=_obj(refresh_token=_STR),
        descricao='O refresh token é de uso único: a resposta traz um novo e o enviado deixa de valer. '
                  'Reapresentar um token já usado revoga a sessão inteira (REFRESH_TOKEN_REUSED).')},
    '/auth/logout': {'post': _op(
        'Encerra a sessão', 'Autenticação', {'description': 'Sessão encerrada (idempotente).'},
        erros=(415, 422), corpo=_obj(refresh_token=_STR), codigo='204')},
    '/cursos': {'get': _op('Lista cursos', 'Catálogo', _ok(_lista(_REF('Curso'))), [
        _p('area'), _p('busca', descricao='Texto livre (nome, instituição, descrição, área).'),
        _p('modalidade', tipo={'type': 'array', 'items': _STR}, descricao='Repetível.'),
        _p('tipo_instituicao', tipo={'type': 'array', 'items': _STR}, descricao='Repetível: Pública, Privada.'),
        *PAGINA])},
    '/cursos/{curso_id}': {'get': _op('Detalhe do curso', 'Catálogo', _ok(_data(_REF('Curso'))),
                                      [_p('curso_id', 'path', _INT)], erros=(404,))},
    '/faculdades': {'get': _op('Lista faculdades', 'Catálogo', _ok(_lista(_REF('Faculdade'))), [
        _p('tipo_instituicao'), _p('uf'), _p('cidade', descricao='Cidade, sigla de UF ou região.'),
        _p('curso'), _p('busca'), _p('modalidade', tipo={'type': 'array', 'items': _STR}), *PAGINA])},
    '/faculdades/{faculdade_id}': {'get': _op('Detalhe da faculdade (com cursos e vestibulares)', 'Catálogo',
                                              _ok(_data(_REF('FaculdadeDetalhe'))),
                                              [_p('faculdade_id', 'path', _INT)], erros=(404,))},
    '/vestibulares': {'get': _op('Lista vestibulares', 'Catálogo', _ok(_lista(_REF('Vestibular'))), [
        _p('tipo_instituicao'), _p('busca'), _p('curso'),
        _p('regiao', tipo={'type': 'array', 'items': {'type': 'string'}}, descricao='Região (repetível).'),
        _p('mes', tipo={'type': 'array', 'items': {'type': 'integer', 'minimum': 1, 'maximum': 12}},
           descricao='Mês da prova (repetível).'),
        _p('incluir_privados', tipo={'type': 'boolean', 'default': False},
           descricao='Por padrão só instituições públicas.'), *PAGINA])},
    '/vestibulares/{vestibular_id}': {'get': _op('Detalhe do vestibular', 'Catálogo',
                                                 _ok(_data(_REF('Vestibular'))),
                                                 [_p('vestibular_id', 'path', _INT)], erros=(404,))},
    '/busca/sugestoes': {'get': _op('Autocomplete de busca (locais, faculdades, cursos)', 'Busca', _ok(_obj(
        data=_obj(local={'type': 'array', 'items': {'type': 'object'}},
                  faculdade={'type': 'array', 'items': {'type': 'object'}},
                  curso={'type': 'array', 'items': {'type': 'object'}}),
        meta=_obj(termo=_STR, total=_INT))), [
        _p('q', descricao='Termo (mínimo 2 caracteres; ignora acentos e maiúsculas).'),
        _p('tipos', descricao='Lista separada por vírgula: local,faculdade,curso.'),
        _p('limite', tipo={'type': 'integer', 'maximum': 10}, descricao='Máximo por tipo.')])},
    '/instituicoes': {'get': _op('Instituições (por código e-MEC)', 'Instituições',
                                 _ok(_lista(_REF('Instituicao'))),
                                 [_p('uf'), _p('cidade'), _p('tipo_instituicao'), _p('busca'), *PAGINA])},
    '/instituicoes/{codigo_emec}': {'get': _op('Detalhe da instituição', 'Instituições',
                                               _ok(_data(_REF('Instituicao'))),
                                               [_p('codigo_emec', 'path')], erros=(404,))},
    '/instituicoes/{codigo_emec}/cursos': {'get': _op('Cursos da instituição', 'Instituições', _ok(_obj(
        data={'type': 'array', 'items': _REF('CursoResumo')},
        meta=_obj(total=_INT, instituicao=_STR))), [_p('codigo_emec', 'path')], erros=(404,))},
    '/teste-vocacional/perguntas': {'get': _op('Questionário do teste vocacional', 'Teste vocacional',
                                               _ok(_data(_REF('Questionario'))))},
    '/teste-vocacional/resultados': {
        'post': _op('Envia respostas e recebe o resultado', 'Teste vocacional', _ok(_data(_REF('TesteResultado')),
                    'Resultado calculado no servidor.'), erros=(415, 422), codigo='201',
                    corpo=_obj(respostas={'type': 'object', 'additionalProperties': _STR,
                                          'example': {f'q{i}': 'a' for i in range(1, 11)}}),
                    descricao='Autenticação opcional: com usuário logado o resultado entra no histórico dele.'),
        'get': _op('Histórico de resultados do usuário', 'Teste vocacional', _ok(_obj(
            data={'type': 'array', 'items': _REF('TesteHistoricoItem')}, meta=_obj(total=_INT))),
            [_p('limit', tipo={'type': 'integer', 'maximum': 50, 'default': 10})], seguro=True)},
    '/teste-vocacional/recomendacoes': {'get': _op(
        'Cursos recomendados por compatibilidade', 'Teste vocacional', _ok(_data(_REF('Recomendacoes'))),
        [_p('id', tipo={'type': 'integer'}, descricao='Resultado da própria conta (padrão: o mais recente).'),
         _p('limite', tipo={'type': 'integer', 'maximum': 200, 'default': 50})], erros=(404,), seguro=True)},
    '/favoritos': {'get': _op('Lista favoritos do usuário', 'Favoritos', _ok(_obj(
        data={'type': 'array', 'items': _REF('Favorito')}, meta=_obj(total=_INT))),
        [_p('tipo', tipo={'type': 'string', 'enum': ['curso', 'faculdade', 'vestibular']})],
        erros=(422,), seguro=True)},
    '/favoritos/{tipo}/{item_id}': {
        'put': _op('Favorita um item (idempotente)', 'Favoritos', _ok(_data(_REF('Favorito')),
                   'Já era favorito.'), [TIPO_FAV, ITEM_ID], erros=(404, 422), seguro=True,
                   descricao='201 se criou o favorito; 200 se já existia. O nome vem do banco.'),
        'delete': _op('Remove dos favoritos (idempotente)', 'Favoritos',
                      {'description': 'Removido (ou já não era favorito).'}, [TIPO_FAV, ITEM_ID],
                      erros=(422,), seguro=True, codigo='204')},
    '/me': {
        'get': _op('Perfil do usuário autenticado', 'Perfil', _ok(_data(_REF('Usuario'))), seguro=True),
        'patch': _op('Atualiza o próprio perfil', 'Perfil', _ok(_data(_REF('Usuario'))), erros=(415, 422),
                     seguro=True, corpo=_obj(nome_usuario=_STR, email=_STR, password=_STR, password_confirm=_STR),
                     descricao='Só estes campos; o tipo de acesso nunca é editável. Trocar a senha encerra '
                               'as outras sessões do app (a atual continua válida).')},
    '/me/dashboard': {'get': _op('Resumo do painel do usuário', 'Perfil', _ok(_data(_REF('Dashboard'))),
                                 seguro=True)},
    # ── Painel administrativo (contas admin; o papel é conferido no banco a cada requisição) ──
    '/admin/estatisticas': {'get': _op('Indicadores do painel', 'Admin', _ok(_data(_obj(
        stats={'type': 'object', 'additionalProperties': _INT},
        automacoes={'type': 'array', 'items': {'type': 'object'}}))), erros=(403,), seguro=True)},
    '/admin/usuarios': {
        'get': _op('Lista usuários', 'Admin', _ok(_obj(data={'type': 'array', 'items': _REF('UsuarioAdmin')},
                                                       meta=_obj(total=_INT))), erros=(403,), seguro=True),
        'post': _op('Cria usuário (aluno ou admin)', 'Admin', _ok(_data(_REF('UsuarioAdmin'))), erros=(403, 409, 415, 422),
                    seguro=True, codigo='201', corpo=_obj(nome_usuario=_STR, email=_STR, password=_STR,
                                                          tipo={'type': 'string', 'enum': ['aluno', 'admin']}))},
    '/admin/usuarios/{usuario_id}': {
        'patch': _op('Edita usuário', 'Admin', _ok(_data(_REF('UsuarioAdmin'))), [_p('usuario_id', 'path', _INT)],
                     erros=(403, 404, 409, 415, 422), seguro=True,
                     corpo=_obj(nome_usuario=_STR, email=_STR, password=_STR,
                                tipo={'type': 'string', 'enum': ['aluno', 'admin']}),
                     descricao='Ninguém remove o próprio acesso de admin.'),
        'delete': _op('Exclui usuário', 'Admin', {'description': 'Excluído.'}, [_p('usuario_id', 'path', _INT)],
                      erros=(403, 404), seguro=True, codigo='204', descricao='Ninguém exclui a própria conta.')},
    '/admin/faculdades': {'post': _op('Cadastra faculdade', 'Admin', _ok(_data(_REF('Faculdade'))),
                                      erros=(403, 409, 415, 422), seguro=True, codigo='201', corpo=_REF('FaculdadeEntrada'))},
    '/admin/faculdades/{faculdade_id}': {
        'patch': _op('Edita faculdade', 'Admin', _ok(_data(_REF('Faculdade'))), [_p('faculdade_id', 'path', _INT)],
                     erros=(403, 404, 415, 422), seguro=True, corpo=_REF('FaculdadeEntrada')),
        'delete': _op('Exclui faculdade', 'Admin', {'description': 'Excluída.'}, [_p('faculdade_id', 'path', _INT)],
                      erros=(403, 404), seguro=True, codigo='204')},
    '/admin/faculdades/importacoes': {'post': _op(
        'Importa faculdades do e-MEC', 'Admin', _ok(_data({'type': 'object'})), erros=(403, 415, 422), seguro=True,
        corpo=_obj(codigos={'type': 'array', 'items': _STR}, uf=_STR, brasil={'type': 'boolean'}),
        descricao='Um dos três: códigos e-MEC, uma UF ou o Brasil inteiro (demorado).')},
    '/admin/cursos': {'post': _op('Cadastra curso', 'Admin', _ok(_data(_REF('Curso'))), erros=(403, 415, 422),
                                  seguro=True, codigo='201', corpo=_obj(
                                      nome=_STR, instituicao=_STR, faculdade_id={'type': 'integer', 'nullable': True},
                                      modalidade=_STR, descricao=_STR, duracao=_STR, grau=_STR, area=_STR,
                                      tipo_instituicao=_STR))},
    '/admin/vestibulares': {'post': _op('Cadastra vestibular', 'Admin', _ok(_data(_REF('Vestibular'))),
                                        erros=(403, 409, 415, 422), seguro=True, codigo='201', corpo=_obj(
                                            nome=_STR, instituicao=_STR, tipo_instituicao=_STR, cidade=_STR,
                                            regiao=_STR, periodo_inscricao=_STR, data_prova=_STR, descricao=_STR,
                                            link_edital=_STR, taxa_inscricao=_STR, cursos_oferecidos=_STR,
                                            requisitos=_STR))},
    '/admin/vestibulares/validacao': {'post': _op(
        'Valida datas e vínculos dos vestibulares', 'Admin', _ok(_data({'type': 'object'})), erros=(403, 415),
        seguro=True, corpo=_obj(aplicar={'type': 'boolean', 'default': False}),
        descricao='aplicar=false só mostra o relatório; aplicar=true grava.')},
    '/openapi.json': {'get': _op('Esta especificação', 'Documentação', {'description': 'Documento OpenAPI 3.'})},
}

ESPECIFICACAO = {
    'openapi': '3.0.3',
    'info': {
        'title': 'SuaFacul API', 'version': '1.0.0',
        'description': ('API para o aplicativo Mobile e consumidores externos. Sucesso: {data, meta}. '
                        'Erro: {error: {code, message, request_id, details?}}. Todas as respostas trazem '
                        'o cabeçalho X-Request-ID (envie o seu para correlacionar). Corpos JSON exigem '
                        'Content-Type: application/json. Autenticação: Authorization: Bearer <access_token> '
                        '(15 min); renove com /auth/refresh (refresh token de 30 dias, uso único).'),
    },
    'servers': [{'url': '/api/v1'}],
    'paths': PATHS,
    'components': {
        'schemas': SCHEMAS,
        'responses': RESPOSTAS_ERRO,
        'securitySchemes': {'bearerAuth': {'type': 'http', 'scheme': 'bearer'}},
    },
}


@bp.get('/openapi.json')
@cache_publico
def openapi_json():
    return jsonify(ESPECIFICACAO)
