"""API legada do teste vocacional (Web, sessão por cookie).

Regras em services/teste_vocacional_service.py (questionário e pontuação) e
services/vocacional_service.py (compatibilidade com os cursos); as perguntas
vêm de services/teste_vocacional_dados.py.
"""
import json

from flask import Blueprint, current_app, jsonify, request, session, url_for

from app.models.teste_vocacional import TesteVocacional
from app.services import teste_vocacional_service, vocacional_service
from app.services.erros import NaoEncontradoError
from app.services.teste_vocacional_dados import PERFIS

bp = Blueprint('api_teste_vocacional', __name__, url_prefix='/api/teste_vocacional')


@bp.route('/perguntas', methods=['GET'])
def perguntas():
    """Questionário (sem os pesos das opções)."""
    return jsonify({'success': True, **teste_vocacional_service.questionario()})


@bp.route('/responder', methods=['POST'])
def responder():
    """Recebe as respostas ({q1: 'a', ...}), pontua NO SERVIDOR, salva o
    resultado (do usuário logado ou anônimo) e devolve perfis + cursos sugeridos."""
    respostas = {k: v for k, v in request.form.items()}
    resultado = teste_vocacional_service.submeter(respostas, usuario_id=session.get('user_id'))
    return jsonify({'success': True, **resultado})


def _perfil_legado():
    """Clientes antigos enviam o perfil já calculado: valida antes de aceitar.
    Devolve (perfil_principal, perfis_json) ou (None, mensagem de erro)."""
    perfil_principal = request.form.get('perfil_principal', '')
    perfis_json = request.form.get('perfis_json', '{}')
    if not perfil_principal:
        return None, 'Perfil principal não informado.'
    if perfil_principal not in PERFIS:
        return None, 'Perfil principal inválido.'
    try:
        scores = (json.loads(perfis_json) or {}).get('scores', {})
        if not isinstance(scores, dict) or any(k not in PERFIS or not isinstance(v, int) or v < 0
                                               for k, v in scores.items()):
            raise ValueError
    except (ValueError, AttributeError):
        return None, 'Pontuação inválida.'
    return perfil_principal, perfis_json


@bp.route('/salvar', methods=['POST'])
def salvar():
    """Fluxo atual da página: recebe as respostas brutas (respostas_json, com
    os perfis de cada alternativa) e recalcula a pontuação no servidor — os
    scores enviados pelo navegador são ignorados. Sem login, guarda o id do
    resultado no cookie de sessão até a pessoa entrar ou se cadastrar."""
    respostas_json = request.form.get('respostas_json')
    usuario_id = session.get('user_id')

    if respostas_json:
        try:
            respostas = vocacional_service.validar_respostas(json.loads(respostas_json))
        except (ValueError, TypeError) as e:
            msg = str(e) if isinstance(e, vocacional_service.RespostasInvalidas) else 'Respostas em formato inválido.'
            return jsonify({'success': False, 'message': msg}), 400
        scores, melhores = vocacional_service.calcular_pontuacao(respostas)
        if not melhores:
            return jsonify({'success': False, 'message': 'Não foi possível identificar um perfil.'}), 400
        perfil_principal = melhores[0]
        perfis_json = json.dumps({'scores': scores, 'bestProfiles': melhores})
        respostas_json = json.dumps(respostas)
    else:
        # Compatibilidade com clientes que enviam o perfil já calculado.
        perfil_principal, perfis_json = _perfil_legado()
        if perfil_principal is None:
            return jsonify({'success': False, 'message': perfis_json})

    resultado = TesteVocacional().salvar_resultado({
        'usuario_id': usuario_id,
        'perfil_principal': perfil_principal,
        'perfis_json': perfis_json,
        'respostas_json': respostas_json,
    })
    if not resultado.get('success'):
        return jsonify(resultado), 500
    if not usuario_id:
        # Guarda só o id no cookie de sessão (assinado) até o login/cadastro.
        session.permanent = True
        session['teste_pendente_id'] = resultado['id']
    resultado.update({'autenticado': bool(usuario_id),
                      'redirect': url_for('pages.testevocacional_resultado')})
    return jsonify(resultado)


def _resultado_atual():
    """Resultado que a sessão atual pode ver: o mais recente da conta
    logada, ou o teste pendente feito sem login neste navegador."""
    model = TesteVocacional()
    if 'user_id' in session:
        return model.ultimo_do_usuario(session['user_id'])
    pendente = session.get('teste_pendente_id')
    if pendente:
        r = model.buscar_por_id(pendente)
        if r and r['usuario_id'] is None:
            return r
        session.pop('teste_pendente_id', None)
    return None


@bp.route('/resultado', methods=['GET'])
def resultado():
    """Prévia pública: perfil e quantos cursos combinam — sem a lista."""
    r = _resultado_atual()
    if not r:
        return jsonify({'success': False, 'motivo': 'sem_resultado',
                        'message': 'Nenhum teste vocacional encontrado. Faça o teste para ver seus resultados.'}), 404
    scores = vocacional_service.ler_scores(r['perfis_json'])
    try:
        rec = vocacional_service.recomendar_cursos(scores, limite=0)
    except Exception:
        current_app.logger.exception("[vocacional] Falha ao calcular compatibilidade")
        rec = None
    return jsonify({
        'success': True,
        'autenticado': 'user_id' in session,
        'resultado': {
            'id': r['id'],
            'perfil': r['perfil_principal'],
            'perfil_nome': teste_vocacional_service.nome_perfil(r['perfil_principal']),
            'perfil_descricao': vocacional_service.DESCRICOES.get(r['perfil_principal']),
            'created_at': r['created_at'],
            'pontuacoes': teste_vocacional_service.pontuacoes(scores),
        },
        'total_compativeis': rec['total_compativeis'] if rec else None,
    })


@bp.route('/recomendacoes', methods=['GET'])
def recomendacoes():
    """Lista completa de cursos recomendados — só para usuário autenticado
    e só para resultados da própria conta."""
    if 'user_id' not in session:
        return jsonify({'success': False, 'motivo': 'nao_autenticado',
                        'message': 'Entre na sua conta para ver os cursos recomendados.'}), 401
    try:
        limite = max(1, min(int(request.args.get('limite', 50)), 200))
    except ValueError:
        limite = 50
    try:
        rec = teste_vocacional_service.recomendacoes(
            session['user_id'], resultado_id=request.args.get('id', type=int), limite=limite)
    except NaoEncontradoError as e:
        return jsonify({'success': False, 'motivo': 'sem_resultado', 'message': str(e)}), 404
    except Exception:
        current_app.logger.exception("[vocacional] Falha ao calcular recomendações")
        return jsonify({'success': False, 'motivo': 'erro_interno',
                        'message': 'Não foi possível calcular suas recomendações agora.'}), 500
    rec['success'] = True
    return jsonify(rec)
