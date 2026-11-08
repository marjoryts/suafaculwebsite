"""DTOs da API v1: formato de saída estável, sem colunas internas do banco
(codigo_inep_curso, fonte, cadastrado_ok, ultima_validacao, updated_at...)."""


def _pegar(origem, *campos):
    return {c: origem.get(c) for c in campos}


def curso_dto(c):
    return _pegar(c, 'id', 'nome', 'instituicao', 'faculdade_id', 'modalidade', 'descricao',
                  'duracao', 'grau', 'area', 'tipo_instituicao')


def curso_resumo_dto(c):
    return _pegar(c, 'id', 'nome', 'modalidade', 'grau', 'area')


def vestibular_dto(v):
    dto = _pegar(v, 'id', 'nome', 'instituicao', 'faculdade_id', 'tipo_instituicao', 'cidade', 'regiao',
                 'periodo_inscricao', 'data_prova', 'descricao', 'link_edital',
                 'taxa_inscricao', 'cursos_oferecidos', 'requisitos')
    dto['status'] = v.get('status_validacao')  # ativo | encerrado | data_invalida | nao_validado
    return dto


def vestibular_resumo_dto(v):
    return _pegar(v, 'id', 'nome', 'data_prova', 'periodo_inscricao', 'link_edital')


def proxima_prova_dto(v):
    return _pegar(v, 'id', 'nome', 'instituicao', 'cidade', 'regiao', 'data_prova',
                  'periodo_inscricao', 'link_edital')


def faculdade_dto(f):
    dto = _pegar(f, 'id', 'codigo_emec', 'nome', 'sigla', 'organizacao_academica', 'tipo_instituicao',
                 'url', 'endereco', 'cidade', 'uf', 'telefone', 'email', 'situacao')
    dto['total_cursos'] = f.get('total_cursos', 0)
    return dto


def faculdade_detalhe_dto(f):
    dto = faculdade_dto(f)
    dto['total_cursos'] = len(f.get('cursos', []))
    dto['cursos'] = [curso_resumo_dto(c) for c in f.get('cursos', [])]
    dto['vestibulares'] = [vestibular_resumo_dto(v) for v in f.get('vestibulares', [])]
    return dto


def instituicao_dto(f):
    """API pública por código e-MEC (sem id interno nem 'fonte')."""
    dto = _pegar(f, 'codigo_emec', 'nome', 'sigla', 'organizacao_academica', 'tipo_instituicao',
                 'situacao', 'cidade', 'uf')
    for campo in ('endereco', 'telefone', 'email', 'url'):
        dto[campo] = f.get(campo) or None
    dto['total_cursos_cadastrados'] = f.get('total_cursos', 0)
    return dto


_CAMPOS_ITEM = {
    'curso': ('id', 'nome', 'instituicao', 'area', 'modalidade', 'grau', 'duracao'),
    'faculdade': ('id', 'nome', 'sigla', 'cidade', 'uf', 'tipo_instituicao'),
    'vestibular': ('id', 'nome', 'instituicao', 'cidade', 'data_prova', 'periodo_inscricao'),
}


def _item_dto(tipo, item):
    if item is None:  # o item foi removido do catálogo depois de favoritado
        return None
    dto = _pegar(item, *_CAMPOS_ITEM[tipo])
    if tipo == 'vestibular':
        dto['status'] = item.get('status_validacao')
    return dto


def favorito_dto(f):
    dto = _pegar(f, 'tipo', 'item_id', 'nome_item', 'created_at')
    if 'item' in f:  # presente na lista e no PUT; o dashboard usa a versão simples
        dto['item'] = _item_dto(f['tipo'], f['item'])
    return dto


def usuario_dto(u):
    return {
        'id': u['id'], 'nome_usuario': u['nome_usuario'], 'email': u['email'], 'tipo': u['tipo'],
        'avatar_url': u.get('avatar_url'), 'auth_provider': u.get('auth_provider'),
        'created_at': u.get('created_at'),
    }


def dashboard_dto(d):
    return {
        'usuario': usuario_dto(d['usuario']),
        'contagem_favoritos': d['stats_favoritos'],
        'favoritos_recentes': [favorito_dto(f) for f in d['favoritos_recentes']],
        'proximas_provas': [proxima_prova_dto(v) for v in d['proximas_provas']],
        'testes_vocacionais': d['testes_vocacionais'],
        'ultimo_teste': d['ultimo_teste'],
    }
