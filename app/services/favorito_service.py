"""Regras de negócio dos favoritos (curso, faculdade, vestibular)."""
from app.models.curso import Curso
from app.models.faculdade import Faculdade
from app.models.favorito import Favorito
from app.models.vestibular import Vestibular
from app.services.erros import NaoEncontradoError, ValidacaoError

TIPOS_VALIDOS = ('curso', 'vestibular', 'faculdade')


def _tipo_valido(tipo):
    if tipo not in TIPOS_VALIDOS:
        raise ValidacaoError('Tipo inválido.', details={'campo': 'tipo'})
    return tipo


def validar_tipo(tipo):
    """Levanta ValidacaoError se `tipo` não for curso/faculdade/vestibular."""
    return _tipo_valido(tipo)


def _item_id_valido(item_id):
    try:
        valor = int(item_id)
    except (TypeError, ValueError):
        valor = 0
    if valor <= 0:
        raise ValidacaoError('Dados incompletos.', details={'campo': 'item_id'})
    return valor


def adicionar(usuario_id, tipo, item_id, nome_item):
    if not tipo or not nome_item:
        raise ValidacaoError('Dados incompletos.')
    item_id = _item_id_valido(item_id)
    return Favorito().adicionar(usuario_id, _tipo_valido(tipo), item_id, nome_item)


def remover(usuario_id, tipo, item_id):
    if not tipo:
        raise ValidacaoError('Dados incompletos.')
    item_id = _item_id_valido(item_id)
    return Favorito().remover(usuario_id, _tipo_valido(tipo), item_id)


def listar(usuario_id, tipo=None):
    return Favorito().listar_por_usuario(usuario_id, tipo)


def verificar(usuario_id, tipo, item_id):
    if not tipo:
        raise ValidacaoError('Dados incompletos.')
    item_id = _item_id_valido(item_id)
    return Favorito().verificar_favorito(usuario_id, tipo, item_id)


def listar_ids(usuario_id, tipo):
    return Favorito().listar_ids_favoritos(usuario_id, _tipo_valido(tipo))


# ── Versão "recurso" (API v1): idempotente, nome derivado do banco ──────

_NOME_DO_ITEM = {
    'curso': lambda id: Curso().nome_por_id(id),
    'faculdade': lambda id: Faculdade().nome_por_id(id),
    'vestibular': lambda id: Vestibular().nome_por_id(id),
}


def favoritar(usuario_id, tipo, item_id):
    """Marca o item como favorito (idempotente).

    Diferente de adicionar(): o item precisa existir e o nome é lido do banco
    (não confiamos em nome enviado pelo cliente).
    Devolve (favorito, criado): criado=False se já era favorito.
    """
    tipo = _tipo_valido(tipo)
    item_id = _item_id_valido(item_id)
    nome = _NOME_DO_ITEM[tipo](item_id)
    if nome is None:
        raise NaoEncontradoError('Item não encontrado.', details={'tipo': tipo, 'item_id': item_id})
    criado = bool(Favorito().adicionar(usuario_id, tipo, item_id, nome).get('success'))
    favorito = next(f for f in Favorito().listar_por_usuario(usuario_id, tipo) if f['item_id'] == item_id)
    return _anexar_itens([favorito])[0], criado


def desfavoritar(usuario_id, tipo, item_id):
    """Remove dos favoritos (idempotente: remover quem não é favorito não é erro)."""
    Favorito().remover(usuario_id, _tipo_valido(tipo), _item_id_valido(item_id))


_RESUMOS = {
    'curso': lambda ids: Curso().resumos_por_ids(ids),
    'faculdade': lambda ids: Faculdade().resumos_por_ids(ids),
    'vestibular': lambda ids: Vestibular().resumos_por_ids(ids),
}


def _anexar_itens(favoritos):
    """Acrescenta a cada favorito a chave 'item' (resumo do curso/faculdade/vestibular,
    ou None se o item foi removido). Uma consulta por TIPO, não por favorito (sem N+1)."""
    ids_por_tipo = {}
    for f in favoritos:
        ids_por_tipo.setdefault(f['tipo'], set()).add(f['item_id'])
    resumos = {tipo: _RESUMOS[tipo](ids) for tipo, ids in ids_por_tipo.items()}
    return [{**f, 'item': resumos[f['tipo']].get(f['item_id'])} for f in favoritos]


def listar_com_itens(usuario_id, tipo=None):
    """Favoritos do usuário já com o resumo de cada item (para montar os cards de Salvos)."""
    return _anexar_itens(listar(usuario_id, tipo))
