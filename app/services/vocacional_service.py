"""Cálculo do Teste Vocacional no servidor e compatibilidade com os cursos.

Antes, a pontuação era feita só no navegador (public/js/testevocacional.js)
e o servidor apenas guardava o que recebia. Agora a mesma regra roda aqui,
a partir das respostas brutas, para que o resultado que libera as
recomendações não dependa de números enviados pelo cliente.

Regra de pontuação (idêntica à do front-end):
    cada alternativa marcada soma +1 em cada perfil listado no seu `value`
    (ex.: "tecnico,cientifico" soma 1 em técnico e 1 em científico).

Regra de compatibilidade de um curso (0–100%):
    1. Afinidade do usuário com cada perfil:
           afinidade[p] = pontos[p] / pontos_possiveis[p]
       onde pontos_possiveis[p] é em quantas perguntas existe ao menos uma
       alternativa que pontua p. Assim um perfil que aparece em menos
       perguntas (ex.: científico) não fica em desvantagem.
    2. Perfis do curso: primeiro pelo NOME do curso, usando as carreiras
       que o próprio teste já associa a cada perfil (`profilesInfo.areas`
       no JS — Psicologia → humano, Medicina → científico…). Se o nome não
       casar com nenhuma, usa a ÁREA do curso cadastrada no banco (mesma
       tabela `profileAreasMap` do JS, estendida às áreas gerais CINE que
       vêm da importação do Censo INEP). Os perfis encontrados dividem o
       peso igualmente.
    3. compatibilidade = Σ peso[p] × afinidade[p]  (arredondado em %).

Cursos sem nome reconhecido e com área ausente/não mapeada NÃO recebem
percentual — ficam fora das recomendações e são contados como
"sem dados suficientes". Cursos com 0% também não são recomendados.
"""
import json
import re

from config.database import get_connection, normalizar

PERFIS = ('tecnico', 'criativo', 'humano', 'gestao', 'cientifico', 'pratico')

# Descrição de cada perfil (antes ficava em `profilesInfo` no JS do teste).
DESCRICOES = {
    'tecnico': 'Você gosta de lógica, tecnologia e resolução de problemas. Prefere atividades estruturadas e analíticas.',
    'criativo': 'Você se destaca pela criatividade, comunicação e expressão. Gosta de ambientes dinâmicos e flexíveis.',
    'humano': 'Você tem empatia, gosta de ajudar pessoas e trabalhar em grupo. Valoriza impacto social.',
    'gestao': 'Você gosta de organizar, planejar, liderar e entender como as coisas funcionam em empresas.',
    'cientifico': 'Você é curioso(a), gosta de pesquisa, experimentos e se aprofunda em temas complexos.',
    'pratico': 'Você aprende fazendo, gosta de atividades manuais ou aplicadas e prefere menos teoria.',
}

# Alternativas válidas de cada pergunta (os `value` dos radios em
# app/templates/testevocacional.html). Respostas fora disso são rejeitadas.
QUESTOES = {
    'q1': ['tecnico,cientifico', 'criativo', 'humano', 'gestao', 'pratico'],
    'q2': ['humano', 'gestao,tecnico', 'tecnico,pratico', 'criativo'],
    'q3': ['tecnico,cientifico', 'criativo', 'humano', 'gestao'],
    'q4': ['humano', 'criativo', 'tecnico', 'gestao', 'pratico'],
    'q5': ['tecnico,pratico', 'humano,gestao,criativo'],
    'q6': ['criativo,gestao,pratico', 'tecnico,cientifico,humano'],
    'q7': ['gestao', 'humano', 'criativo', 'tecnico,cientifico', 'pratico'],
    'q8': ['cientifico,tecnico', 'pratico,gestao'],
    'q9': ['gestao,tecnico', 'criativo,tecnico,pratico', 'humano,cientifico', 'gestao,criativo'],
    'q10': ['tecnico', 'criativo', 'humano', 'gestao', 'cientifico', 'pratico'],
}


def _tags(valor):
    return [t.strip() for t in str(valor).split(',') if t.strip() in PERFIS]


def _pontos_possiveis():
    possiveis = {p: 0 for p in PERFIS}
    for opcoes in QUESTOES.values():
        presentes = {t for v in opcoes for t in _tags(v)}
        for p in presentes:
            possiveis[p] += 1
    return possiveis


PONTOS_POSSIVEIS = _pontos_possiveis()

# Carreiras por perfil (de `profilesInfo.areas` no JS), como expressões
# sobre o nome normalizado (minúsculas, sem acento). Limites de palavra
# evitam falsos positivos como "Educação Física" casar com "Física".
CARREIRAS_POR_PERFIL = {
    'tecnico': [r'\bengenharia\b', r'\bsoftware\b', r'\bsistemas de informacao\b',
                r'\bdesenvolvimento de sistemas\b', r'\bciencia da computacao\b',
                r'\banalise de dados\b', r'\bciencia de dados\b', r'\barquitetura\b'],
    'criativo': [r'\bdesign\b', r'\bpublicidade\b', r'\bmarketing\b', r'\barquitetura\b',
                 r'\bmoda\b', r'\baudiovisual\b'],
    'humano': [r'\bpsicologia\b', r'\bpedagogia\b', r'\brecursos humanos\b',
               r'\bservico social\b', r'\benfermagem\b', r'\bfisioterapia\b'],
    'gestao': [r'\badministracao\b', r'\bgestao comercial\b', r'\beconomia\b',
               r'\bciencias economicas\b', r'\blogistica\b', r'\bfinancas\b',
               r'\bgestao financeira\b', r'\bempreendedorismo\b'],
    'cientifico': [r'^medicina\b', r'\bbiomedicina\b', r'\bbiologia\b',
                   r'\bciencias biologicas\b', r'\bquimica\b', r'^fisica\b'],
    'pratico': [r'\bmecatronica\b', r'\bseguranca do trabalho\b', r'\bproducao industrial\b',
                r'\bmanutencao\b', r'\bmecanica\b'],
}
_CARREIRAS_RE = {p: [re.compile(e) for e in exprs] for p, exprs in CARREIRAS_POR_PERFIL.items()}

# Área do curso (normalizada) → perfis. As 7 primeiras são as áreas do
# cadastro manual/seed (mesmas de `profileAreasMap` no JS, invertidas);
# as demais são as áreas gerais CINE gravadas pela importação do Censo.
AREAS_POR_PERFIL = {
    'tecnologia': ['tecnico', 'pratico'],
    'engenharias': ['tecnico', 'pratico'],
    'artes e design': ['criativo'],
    'comunicacao': ['criativo'],
    'saude': ['humano', 'cientifico'],
    'negocios': ['gestao'],
    'direito': ['humano', 'gestao'],
    'educacao': ['humano'],
    'artes e humanidades': ['criativo', 'humano'],
    'ciencias sociais, comunicacao e informacao': ['criativo', 'humano'],
    'negocios, administracao e direito': ['gestao'],
    'ciencias naturais, matematica e estatistica': ['cientifico', 'tecnico'],
    'computacao e tecnologias da informacao e comunicacao (tic)': ['tecnico', 'pratico'],
    'engenharia, producao e construcao': ['tecnico', 'pratico'],
    'agricultura, silvicultura, pesca e veterinaria': ['cientifico', 'pratico'],
    'saude e bem-estar': ['humano', 'cientifico'],
    'servicos': ['pratico'],
}


class RespostasInvalidas(ValueError):
    pass


def validar_respostas(respostas):
    """Confere que todas as perguntas foram respondidas com alternativas
    existentes. Devolve só as chaves conhecidas (descarta extras)."""
    if not isinstance(respostas, dict):
        raise RespostasInvalidas('Respostas em formato inválido.')
    limpas = {}
    for q, opcoes in QUESTOES.items():
        valor = respostas.get(q)
        if valor is None or str(valor) == '':
            raise RespostasInvalidas('Responda todas as perguntas do teste.')
        if str(valor) not in opcoes:
            raise RespostasInvalidas(f'Resposta inválida na pergunta {q[1:]}.')
        limpas[q] = str(valor)
    return limpas


def calcular_pontuacao(respostas):
    """Mesma regra do front-end: +1 por perfil em cada alternativa."""
    scores = {p: 0 for p in PERFIS}
    for valor in respostas.values():
        for t in _tags(valor):
            scores[t] += 1
    maximo = max(scores.values())
    melhores = [p for p, s in scores.items() if s == maximo and s > 0]
    return scores, melhores


def afinidades(scores):
    """Afinidade 0–1 com cada perfil (pontos / pontos possíveis)."""
    resultado = {}
    for p in PERFIS:
        possivel = PONTOS_POSSIVEIS.get(p) or 0
        valor = scores.get(p, 0) if isinstance(scores, dict) else 0
        valor = valor if isinstance(valor, (int, float)) else 0
        resultado[p] = min(1.0, max(0.0, valor / possivel)) if possivel else 0.0
    return resultado


def perfis_do_curso(nome, area):
    """(perfis, origem) — origem é 'nome' ou 'area'; ([], None) sem dados."""
    nome_n = normalizar(nome or '') or ''
    pelo_nome = [p for p, exprs in _CARREIRAS_RE.items() if any(e.search(nome_n) for e in exprs)]
    if pelo_nome:
        return pelo_nome, 'nome'
    pela_area = AREAS_POR_PERFIL.get((normalizar(area or '') or '').strip())
    if pela_area:
        return list(pela_area), 'area'
    return [], None


def compatibilidade(perfis, afin):
    if not perfis:
        return None
    peso = 1.0 / len(perfis)
    return round(100 * sum(peso * afin.get(p, 0.0) for p in perfis))


def recomendar_cursos(scores, limite=50):
    """Cursos cadastrados ordenados por compatibilidade (maior → menor).

    Agrupa pelo nome normalizado (o Censo traz o mesmo curso em várias
    instituições) e informa quantas instituições oferecem cada um. Empates
    de percentual são desempatados por oferta e depois por nome."""
    afin = afinidades(scores)
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT nome, area, COUNT(*) AS total, MIN(id) AS id, "
            "MAX(COALESCE(descricao, '')) AS descricao, MAX(COALESCE(grau, '')) AS grau "
            "FROM cursos GROUP BY nome, area"
        )
        linhas = [dict(r) for r in c.fetchall()]
    finally:
        conn.close()

    grupos = {}
    for r in linhas:
        chave = normalizar(r['nome']).strip()
        g = grupos.get(chave)
        if not g:
            g = grupos[chave] = {'nome': r['nome'], 'areas': {}, 'total': 0, 'id': r['id'],
                                 'descricao': '', 'grau': ''}
        g['total'] += r['total']
        g['areas'][r['area']] = g['areas'].get(r['area'], 0) + r['total']
        g['id'] = min(g['id'], r['id'])
        if r['descricao'] and len(r['descricao']) > len(g['descricao']):
            g['descricao'] = r['descricao']
        if r['grau'] and not g['grau']:
            g['grau'] = r['grau']

    recomendados, sem_dados = [], 0
    for g in grupos.values():
        area = max(g['areas'].items(), key=lambda kv: kv[1])[0] if g['areas'] else None
        perfis, origem = perfis_do_curso(g['nome'], area)
        pct = compatibilidade(perfis, afin)
        if pct is None:
            sem_dados += 1
            continue
        if pct <= 0:
            continue
        descricao = g['descricao'] or ''
        recomendados.append({
            'id': g['id'],
            'nome': g['nome'],
            'area': area,
            'grau': g['grau'] or None,
            'descricao': (descricao[:220].rstrip() + '…') if len(descricao) > 220 else (descricao or None),
            'compatibilidade': pct,
            'perfis': perfis,
            'criterio': origem,
            'total_instituicoes': g['total'],
        })

    recomendados.sort(key=lambda x: (-x['compatibilidade'], -x['total_instituicoes'], normalizar(x['nome'])))
    return {
        'cursos': recomendados[:limite],
        'total_compativeis': len(recomendados),
        'sem_dados_suficientes': sem_dados,
        'total_cursos_analisados': len(grupos),
    }


def ler_scores(perfis_json):
    try:
        dados = json.loads(perfis_json or '{}') or {}
        scores = dados.get('scores') or {}
        return {k: v for k, v in scores.items() if k in PERFIS and isinstance(v, (int, float))}
    except (ValueError, AttributeError, TypeError):
        return {}
