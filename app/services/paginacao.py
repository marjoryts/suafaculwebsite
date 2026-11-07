"""Paginação de listagens (antes copiada em 4 rotas)."""
import math


def inteiro(valor, padrao, minimo=1):
    """Converte para int; valor ausente/inválido vira `padrao` (nunca levanta
    — antes um `?page=abc` gerava erro 500)."""
    try:
        return max(minimo, int(valor))
    except (TypeError, ValueError):
        return padrao


def paginar(repositorio, filtros, page=1, limit=10, chave='itens', limite_maximo=None):
    """Aplica limit/offset e devolve {chave: [...], total, page, limit, total_pages}.

    `repositorio` precisa de listar(filtros) e contar(filtros) (os models).
    `limite_maximo` (opcional) limita o tamanho da página (usado pela API v1).
    """
    page = inteiro(page, 1)
    limit = inteiro(limit, 10)
    if limite_maximo:
        limit = min(limit, limite_maximo)
    filtros = dict(filtros)
    filtros['limit'] = limit
    filtros['offset'] = (page - 1) * limit
    itens = repositorio.listar(filtros)
    total = repositorio.contar(filtros)
    return {chave: itens, 'total': total, 'page': page, 'limit': limit,
            'total_pages': math.ceil(total / limit)}
