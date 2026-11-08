"""Resumo do painel do usuário (Web /dashboard e, futuramente, API do Mobile)."""
from app.models.favorito import Favorito
from app.models.usuario import Usuario
from app.services import teste_vocacional_service
from app.services.erros import NaoEncontradoError

LIMITE_FAVORITOS_RECENTES = 6
LIMITE_PROXIMAS_PROVAS = 4
LIMITE_TESTES = 10


def resumo(usuario_id):
    """Dados do dashboard do usuário. Levanta NaoEncontradoError se a conta
    não existir mais (ex.: removida enquanto a sessão ainda estava ativa)."""
    usuario = Usuario().buscar_por_id(usuario_id)
    if not usuario:
        raise NaoEncontradoError('Usuário não encontrado.')
    favoritos = Favorito()
    contagem = favoritos.contar_por_tipo(usuario_id)
    testes = teste_vocacional_service.historico(usuario_id, limite=LIMITE_TESTES)
    return {
        'usuario': usuario,
        'stats_favoritos': {
            'cursos': contagem['curso'],
            'faculdades': contagem['faculdade'],
            'vestibulares': contagem['vestibular'],
        },
        'favoritos_recentes': favoritos.listar_por_usuario(usuario_id)[:LIMITE_FAVORITOS_RECENTES],
        'proximas_provas': favoritos.proximos_vestibulares(usuario_id, limite=LIMITE_PROXIMAS_PROVAS),
        'testes_vocacionais': testes,
        'ultimo_teste': testes[0] if testes else None,
    }
