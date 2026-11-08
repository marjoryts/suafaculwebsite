"""Painel administrativo no app: as mesmas operações do painel Web (/admin),
pelos mesmos serviços (app/services/admin_service.py). Toda rota exige Bearer
de uma conta admin, conferida no banco a cada requisição.

Listagens usam as rotas públicas do catálogo (/cursos, /faculdades,
/vestibulares?incluir_privados=true), que já têm busca e paginação. As
importações por arquivo CSV (MEC e Censo INEP) ficam só na Web: são arquivos
de centenas de MB, acima do limite de corpo da hospedagem.
"""
from flask import g, jsonify

from app.api.v1 import bp
from app.api.v1.auth import requer_admin
from app.api.v1.http import campo_texto, corpo_json
from app.api.v1.serializers import curso_dto, faculdade_dto, vestibular_dto
from app.models.curso import Curso
from app.models.faculdade import Faculdade
from app.models.vestibular import Vestibular
from app.services import admin_service, emec_service, vestibular_service
from app.services.erros import ValidacaoError


def _usuario_admin_dto(u):
    return {'id': u['id'], 'nome_usuario': u['nome_usuario'], 'email': u['email'], 'tipo': u['tipo']}


def _textos(dados, campos):
    """Só os campos de texto enviados (para criar/editar sem apagar o resto)."""
    return {c: campo_texto(dados, c) for c in campos if c in dados}


# ── Visão geral ─────────────────────────────────────────────────────────

@bp.get('/admin/estatisticas')
@requer_admin
def admin_estatisticas():
    return jsonify({'data': admin_service.estatisticas()})


# ── Usuários ────────────────────────────────────────────────────────────

@bp.get('/admin/usuarios')
@requer_admin
def admin_usuarios():
    usuarios = [_usuario_admin_dto(u) for u in admin_service.listar_usuarios()]
    return jsonify({'data': usuarios, 'meta': {'total': len(usuarios)}})


@bp.post('/admin/usuarios')
@requer_admin
def admin_criar_usuario():
    dados = corpo_json()
    novo = admin_service.criar_usuario(
        campo_texto(dados, 'nome_usuario'), campo_texto(dados, 'email'),
        campo_texto(dados, 'password'), campo_texto(dados, 'tipo') or 'aluno')
    return jsonify({'data': _usuario_admin_dto(novo)}), 201


@bp.patch('/admin/usuarios/<int:usuario_id>')
@requer_admin
def admin_atualizar_usuario(usuario_id):
    """Corpo: nome_usuario e email (obrigatórios, como no painel Web), password e tipo opcionais."""
    dados = corpo_json()
    atualizado = admin_service.atualizar_usuario(
        g.usuario['id'], usuario_id, campo_texto(dados, 'nome_usuario'), campo_texto(dados, 'email'),
        campo_texto(dados, 'password') or None, campo_texto(dados, 'tipo') or None)
    return jsonify({'data': _usuario_admin_dto(atualizado)})


@bp.delete('/admin/usuarios/<int:usuario_id>')
@requer_admin
def admin_excluir_usuario(usuario_id):
    admin_service.excluir_usuario(g.usuario['id'], usuario_id)
    return '', 204


# ── Faculdades ──────────────────────────────────────────────────────────

@bp.post('/admin/faculdades')
@requer_admin
def admin_criar_faculdade():
    criada = admin_service.criar_faculdade(_textos(corpo_json(), Faculdade.CAMPOS))
    return jsonify({'data': faculdade_dto(Faculdade().buscar_por_id(criada['id']))}), 201


@bp.patch('/admin/faculdades/<int:faculdade_id>')
@requer_admin
def admin_atualizar_faculdade(faculdade_id):
    admin_service.atualizar_faculdade(faculdade_id, _textos(corpo_json(), Faculdade.CAMPOS))
    return jsonify({'data': faculdade_dto(Faculdade().buscar_por_id(faculdade_id))})


@bp.delete('/admin/faculdades/<int:faculdade_id>')
@requer_admin
def admin_excluir_faculdade(faculdade_id):
    admin_service.excluir_faculdade(faculdade_id)
    return '', 204


@bp.post('/admin/faculdades/importacoes')
@requer_admin
def admin_importar_faculdades():
    """Importa do e-MEC, como o painel Web. Corpo: {"codigos": ["339", ...]},
    {"uf": "SP"} ou {"brasil": true} (todas as 27 UFs — demorado)."""
    dados = corpo_json()
    codigos = dados.get('codigos')
    if codigos:
        if not isinstance(codigos, list) or not all(isinstance(c, (str, int)) for c in codigos):
            raise ValidacaoError('Informe "codigos" como uma lista de códigos e-MEC.')
        codigos = [str(c).strip() for c in codigos if str(c).strip()]
        if len(codigos) == 1:
            return jsonify({'data': emec_service.importar_faculdade_por_codigo(codigos[0])})
        return jsonify({'data': {'success': True, 'relatorio': emec_service.importar_faculdades_em_lote(codigos)}})
    uf = campo_texto(dados, 'uf').upper()
    if uf:
        if uf not in emec_service.UFS_BRASIL:
            raise ValidacaoError(f'UF inválida: {uf}')
        return jsonify({'data': emec_service.importar_todas_faculdades_por_uf(uf)})
    if dados.get('brasil') is True:
        return jsonify({'data': emec_service.importar_todas_faculdades_brasil()})
    raise ValidacaoError('Informe "codigos", "uf" ou "brasil": true.')


# ── Cursos e vestibulares ───────────────────────────────────────────────

@bp.post('/admin/cursos')
@requer_admin
def admin_criar_curso():
    dados = corpo_json()
    campos = _textos(dados, admin_service.CAMPOS_CURSO)
    campos['faculdade_id'] = dados.get('faculdade_id')
    criado = admin_service.criar_curso(campos)
    return jsonify({'data': curso_dto(Curso().buscar_por_id(criado['id']))}), 201


@bp.post('/admin/vestibulares')
@requer_admin
def admin_criar_vestibular():
    criado = admin_service.criar_vestibular(_textos(corpo_json(), admin_service.CAMPOS_VESTIBULAR))
    return jsonify({'data': vestibular_dto(Vestibular().buscar_por_id(criado['id']))}), 201


@bp.post('/admin/vestibulares/validacao')
@requer_admin
def admin_validar_vestibulares():
    """Validação automática das datas e vínculos. {"aplicar": false} só mostra o
    relatório (pré-visualizar); {"aplicar": true} grava, como no painel Web."""
    aplicar = corpo_json().get('aplicar') is True
    return jsonify({'data': vestibular_service.validar_vestibulares(aplicar=aplicar)})
