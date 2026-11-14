"""Regras do Teste Vocacional: questionário, pontuação, persistência e histórico.

Compartilhado por Web e Mobile e FONTE ÚNICA da regra de pontuação
(`pontuar`/`calcular`): a página web (/api/teste_vocacional/salvar), a rota
/api/teste_vocacional/responder e a API v1 chamam todas `calcular()`. O
cliente só exibe as perguntas e envia as alternativas escolhidas
({'q1': 'a', ...} ou, na página web, {'q1': 'tecnico,cientifico', ...});
a pontuação é sempre calculada aqui (o servidor não confia em resultado
calculado pelo cliente). A compatibilidade com os cursos fica em
vocacional_service.py.
"""
import json

from app.models.curso import Curso
from app.models.teste_vocacional import TesteVocacional
from app.services import vocacional_service
from app.services.erros import NaoEncontradoError, ValidacaoError
from app.services.teste_vocacional_dados import ORDEM_PERFIS, PERFIS, SECOES

LIMITE_CURSOS_SUGERIDOS = 3


def _perguntas():
    return [p for secao in SECOES for p in secao['perguntas']]


def questionario():
    """Estrutura pública do teste (sem os pesos das opções)."""
    return {'secoes': [
        {'titulo': secao['titulo'],
         'perguntas': [{'id': p['id'], 'texto': p['texto'],
                        'opcoes': [{'id': o['id'], 'texto': o['texto']} for o in p['opcoes']]}
                       for p in secao['perguntas']]}
        for secao in SECOES
    ]}


def perguntas_formulario():
    """Perguntas para o formulário da página web: numeradas, com a categoria
    e o `valor` de cada opção = perfis que ela pontua ("tecnico,cientifico"),
    o formato que /api/teste_vocacional/salvar recebe e recalcula."""
    numero = 0
    perguntas = []
    for secao in SECOES:
        for p in secao['perguntas']:
            numero += 1
            perguntas.append({
                'numero': numero, 'id': p['id'], 'categoria': secao['titulo'], 'texto': p['texto'],
                'opcoes': [{'valor': ','.join(o['perfis']), 'texto': o['texto']} for o in p['opcoes']],
            })
    return perguntas


# Formatos aceitos para identificar a alternativa escolhida em cada pergunta:
#   'id'    → letra da opção ("a", "b"...): API v1 (Mobile) e /responder.
#   'valor' → perfis da opção unidos por vírgula ("tecnico,cientifico"): o
#             `value` dos radios da página web, enviado por /salvar.
# Em cada pergunta os dois identificadores são únicos (um mapeia no outro),
# então os dois formatos levam exatamente à mesma alternativa — e daí à
# mesma pontuação, calculada por `pontuar()`.
FORMATOS_RESPOSTA = ('id', 'valor')


def valor_da_opcao(opcao):
    """Identificador da opção no formato 'valor' ("tecnico,cientifico")."""
    return ','.join(opcao['perfis'])


def _localizar_opcao(pergunta, escolhida, formato):
    escolhida = str(escolhida)
    if formato == 'valor':
        return next((o for o in pergunta['opcoes'] if valor_da_opcao(o) == escolhida), None)
    return next((o for o in pergunta['opcoes'] if o['id'] == escolhida), None)


def resolver_respostas(respostas, formato='id'):
    """Converte as respostas recebidas (em qualquer formato aceito) nas
    alternativas do questionário, na ordem das perguntas. Levanta
    ValidacaoError se faltar pergunta ou se houver opção inexistente;
    chaves desconhecidas são ignoradas.

    Devolve [(pergunta, opcao), ...]."""
    if formato not in FORMATOS_RESPOSTA:
        raise ValueError(f'Formato de resposta desconhecido: {formato!r}')
    if not isinstance(respostas, dict):
        raise ValidacaoError('Respostas em formato inválido.')
    escolhidas, faltando, invalidas = [], [], []
    for pergunta in _perguntas():
        valor = respostas.get(pergunta['id'])
        if valor is None or str(valor) == '':
            faltando.append(pergunta['id'])
            continue
        opcao = _localizar_opcao(pergunta, valor, formato)
        if opcao is None:
            invalidas.append(pergunta['id'])
            continue
        escolhidas.append((pergunta, opcao))

    if faltando or invalidas:
        raise ValidacaoError(
            'Responda todas as perguntas para ver seu resultado.',
            details={'perguntas_sem_resposta': faltando, 'respostas_invalidas': invalidas},
        )
    return escolhidas


def pontuar(opcoes):
    """REGRA OFICIAL de pontuação do Teste Vocacional (única no sistema).

    Cada alternativa escolhida soma +1 em cada perfil que ela lista
    (ex.: "tecnico,cientifico" soma 1 em técnico e 1 em científico).
    Perfis principais = os de maior pontuação (> 0), na ordem padrão
    ORDEM_PERFIS (empates devolvem todos).

    Devolve {'scores': {perfil: pontos}, 'perfis_principais': [...]}."""
    scores = {chave: 0 for chave in ORDEM_PERFIS}
    for opcao in opcoes:
        for perfil in opcao['perfis']:
            if perfil in scores:
                scores[perfil] += 1
    maior = max(scores.values())
    principais = [chave for chave in ORDEM_PERFIS if scores[chave] == maior and maior > 0]
    return {'scores': scores, 'perfis_principais': principais}


def calcular(respostas, formato='id'):
    """Valida e pontua as respostas. Ponto de entrada usado por TODOS os
    fluxos (Web /salvar, /responder e API v1). Levanta ValidacaoError se
    faltar pergunta ou se houver opção inexistente.

    Devolve {'scores': {perfil: pontos}, 'perfis_principais': [perfis com a
    maior pontuação (>0), na ordem padrão]}."""
    escolhidas = resolver_respostas(respostas, formato)
    return pontuar(opcao for _pergunta, opcao in escolhidas)


def _cursos_sugeridos(chave_perfil):
    areas = PERFIS[chave_perfil]['areas_cursos']
    if not areas:
        return []
    cursos = Curso().listar({'area': areas[0], 'limit': LIMITE_CURSOS_SUGERIDOS, 'offset': 0})
    return [{'id': c['id'], 'nome': c['nome'], 'instituicao': c['instituicao']} for c in cursos]


def submeter(respostas, usuario_id=None):
    """Calcula, salva o resultado (anônimo ou do usuário) e monta a resposta
    com os perfis e cursos sugeridos."""
    calculo = calcular(respostas)
    principais = calculo['perfis_principais']

    salvo, resultado_id = False, None
    if principais:
        resultado = TesteVocacional().salvar_resultado({
            'usuario_id': usuario_id,
            'perfil_principal': principais[0],
            'perfis_json': json.dumps({'scores': calculo['scores'], 'bestProfiles': principais}),
            'respostas_json': json.dumps({k: respostas[k] for k in (p['id'] for p in _perguntas())}),
        })
        salvo = bool(resultado.get('success'))
        resultado_id = resultado.get('id') if salvo else None

    return {
        'resultado_id': resultado_id,
        'scores': calculo['scores'],
        'pontuacoes': pontuacoes(calculo['scores']),
        'perfis': [{
            'chave': chave,
            'nome': PERFIS[chave]['nome'],
            'descricao': PERFIS[chave]['descricao'],
            'areas': PERFIS[chave]['areas'],
            'cursos_sugeridos': _cursos_sugeridos(chave),
        } for chave in principais],
        'salvo': salvo,
    }


def historico(usuario_id, limite=10):
    """Resultados anteriores do usuário (mais recente primeiro), com o nome do
    perfil e a pontuação de cada perfil em porcentagem (0–100)."""
    resultados = []
    for r in TesteVocacional().listar_por_usuario(usuario_id, limite=limite):
        try:
            scores = (json.loads(r.get('perfis_json') or '{}') or {}).get('scores') or {}
        except (ValueError, AttributeError):
            scores = {}
        resultados.append({
            'id': r['id'],
            'perfil': r['perfil_principal'],
            'perfil_nome': PERFIS.get(r['perfil_principal'], {}).get('nome', r['perfil_principal']),
            'created_at': r['created_at'],
            'pontuacoes': pontuacoes(scores),
        })
    return resultados


def nome_perfil(chave):
    return PERFIS.get(chave, {}).get('nome', chave)


def pontuacoes(scores):
    """Porcentagem de cada perfil no total de pontos, do maior para o menor
    (o que a página de resultado e o histórico exibem)."""
    validos = {k: v for k, v in (scores or {}).items() if isinstance(v, (int, float))}
    total = sum(validos.values()) or 0
    return sorted(({'chave': k, 'nome': nome_perfil(k),
                    'percentual': round(100 * v / total) if total else 0}
                   for k, v in validos.items()), key=lambda p: p['percentual'], reverse=True)


def recomendacoes(usuario_id, resultado_id=None, limite=50):
    """Cursos por compatibilidade com um resultado DA PRÓPRIA CONTA (o mais
    recente, se `resultado_id` não vier). NaoEncontradoError se não houver."""
    model = TesteVocacional()
    if resultado_id:
        r = model.buscar_por_id(resultado_id)
        if not r or r['usuario_id'] != usuario_id:
            r = None
    else:
        r = model.ultimo_do_usuario(usuario_id)
    if not r:
        raise NaoEncontradoError('Nenhum teste vocacional encontrado na sua conta.')
    rec = vocacional_service.recomendar_cursos(vocacional_service.ler_scores(r['perfis_json']), limite=limite)
    rec.update({'resultado_id': r['id'], 'perfil': r['perfil_principal'],
                'perfil_nome': nome_perfil(r['perfil_principal']),
                'perfil_descricao': PERFIS.get(r['perfil_principal'], {}).get('descricao'),
                'created_at': r['created_at']})
    return rec
