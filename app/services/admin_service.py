"""Operações do painel administrativo, compartilhadas pelo painel Web (/api/*)
e pelo app (/api/v1/admin/*). Quem chama já conferiu que o usuário é admin
(app/security.py na Web, app/api/v1/auth.py no app) — o papel vem sempre do banco.

As regras de cada cadastro (campos obrigatórios, valores padrão) ficam aqui;
os models só gravam. Falhas viram ErroDeNegocio, que cada interface traduz
para o seu formato (app/errors.py).
"""
from app.models.curso import Curso
from app.models.estatisticas import Estatisticas
from app.models.automacao_log import AutomacaoLog
from app.models.faculdade import Faculdade
from app.models.usuario import Usuario
from app.models.vestibular import Vestibular
from app.services import usuario_service
from app.services.erros import ConflitoError, NaoEncontradoError, ValidacaoError

CAMPOS_CURSO = ['nome', 'instituicao', 'modalidade', 'descricao', 'duracao', 'grau', 'area', 'tipo_instituicao']
CAMPOS_VESTIBULAR = ['nome', 'instituicao', 'tipo_instituicao', 'cidade', 'regiao', 'periodo_inscricao',
                     'data_prova', 'descricao', 'link_edital', 'taxa_inscricao', 'cursos_oferecidos', 'requisitos']
TIPOS_USUARIO = ('aluno', 'admin')
TIPOS_INSTITUICAO = ('Pública', 'Privada')


def _exigir_tipo_instituicao(dados):
    """O banco só aceita 'Pública' ou 'Privada' (o formulário Web sempre envia um dos dois)."""
    if 'tipo_instituicao' in dados and dados['tipo_instituicao'] not in TIPOS_INSTITUICAO:
        raise ValidacaoError("Tipo de instituição inválido. Use 'Pública' ou 'Privada'.")


def _exigir_sucesso(resultado, erro=ValidacaoError):
    """Models devolvem {'success', 'message'}: falha vira exceção (duplicado, erro de banco...)."""
    if not resultado.get('success'):
        raise erro(resultado.get('message') or 'Não foi possível concluir a operação.')
    return resultado


def _texto(dados, campo):
    return str(dados.get(campo) or '').strip()


# ── Visão geral ─────────────────────────────────────────────────────────

def estatisticas():
    return {'stats': Estatisticas().resumo_admin(), 'automacoes': AutomacaoLog().ultimos(5)}


# ── Usuários ────────────────────────────────────────────────────────────

def listar_usuarios():
    return Usuario().listar()


def criar_usuario(nome_usuario, email, password, tipo='aluno'):
    """Mesmo fluxo do painel Web: cadastra (com as validações do cadastro
    comum) e, se pedido, promove a admin."""
    if tipo not in TIPOS_USUARIO:
        raise ValidacaoError("Tipo inválido. Use 'aluno' ou 'admin'.")
    _exigir_sucesso(usuario_service.registrar(nome_usuario, email, password), ConflitoError)
    novo = Usuario().buscar_por_email((email or '').strip())
    if tipo == 'admin':
        _exigir_sucesso(Usuario().definir_tipo(novo['id'], 'admin'))
        novo = Usuario().buscar_por_id(novo['id'])
    return novo


def atualizar_usuario(ator_id, usuario_id, nome_usuario, email, password=None, tipo=None):
    if not Usuario().buscar_por_id(usuario_id):
        raise NaoEncontradoError('Usuário não encontrado.')
    if Usuario().existe_conflito((nome_usuario or '').strip(), (email or '').strip(), ignorar_id=usuario_id):
        raise ConflitoError('Esse nome de usuário ou e-mail já está em uso.')
    _exigir_sucesso(usuario_service.atualizar_por_admin(usuario_id, nome_usuario, email, password))
    if tipo:
        _exigir_sucesso(usuario_service.definir_tipo(ator_id, usuario_id, tipo))
    return Usuario().buscar_por_id(usuario_id)


def excluir_usuario(ator_id, usuario_id):
    if not Usuario().buscar_por_id(usuario_id):
        raise NaoEncontradoError('Usuário não encontrado.')
    return _exigir_sucesso(usuario_service.excluir(ator_id, usuario_id))


# ── Faculdades ──────────────────────────────────────────────────────────

def criar_faculdade(dados):
    dados = {k: _texto(dados, k) for k in Faculdade.CAMPOS}
    if not dados['nome']:
        raise ValidacaoError('Nome da faculdade é obrigatório.')
    dados['tipo_instituicao'] = dados['tipo_instituicao'] or 'Pública'  # padrão da tabela
    _exigir_tipo_instituicao(dados)
    dados['fonte'] = dados.get('fonte') or 'manual'
    dados['codigo_emec'] = dados.get('codigo_emec') or None
    return _exigir_sucesso(Faculdade().criar(dados), ConflitoError)


def atualizar_faculdade(faculdade_id, dados):
    if not Faculdade().buscar_por_id(faculdade_id):
        raise NaoEncontradoError('Faculdade não encontrada.')
    campos = {k: _texto(dados, k) for k in Faculdade.CAMPOS if k in dados}
    if 'nome' in campos and not campos['nome']:
        raise ValidacaoError('Nome da faculdade é obrigatório.')
    _exigir_tipo_instituicao(campos)
    return _exigir_sucesso(Faculdade().atualizar(faculdade_id, campos))


def excluir_faculdade(faculdade_id):
    if not Faculdade().buscar_por_id(faculdade_id):
        raise NaoEncontradoError('Faculdade não encontrada.')
    return _exigir_sucesso(Faculdade().deletar(faculdade_id))


# ── Cursos e vestibulares ───────────────────────────────────────────────

def criar_curso(dados):
    curso = {k: _texto(dados, k) for k in CAMPOS_CURSO}
    faculdade_id = str(dados.get('faculdade_id') or '').strip()
    try:
        curso['faculdade_id'] = int(faculdade_id) if faculdade_id else None
    except ValueError:
        raise ValidacaoError('Faculdade inválida.')
    if not curso['nome'] or not curso['instituicao']:
        raise ValidacaoError('Nome e instituição são obrigatórios.')
    return _exigir_sucesso(Curso().criar(curso))


def criar_vestibular(dados):
    vestibular = {k: _texto(dados, k) for k in CAMPOS_VESTIBULAR}
    if not vestibular['nome'] or not vestibular['instituicao']:
        raise ValidacaoError('Nome e instituição são obrigatórios.')
    return _exigir_sucesso(Vestibular().criar(vestibular), ConflitoError)
