"""
Importação de cursos de graduação a partir do Censo da Educação Superior
(INEP) — fonte oficial, baixada manualmente pelo admin em
https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior
(arquivo "MICRODADOS_CADASTRO_CURSOS_<ano>.CSV", dentro do ZIP do Censo).

Por que upload manual (igual ao CSV de instituições): o e-MEC/MEC ficam
atrás de um WAF que bloqueia download automatizado a partir do servidor
(ver README) — o navegador do admin não sofre esse bloqueio.

Sobre o arquivo: ~700 mil linhas, mas a granularidade real não é "um
curso" — é "um curso, por local de oferta" (TP_DIMENSAO): cursos de EAD
aparecem repetidos uma vez por polo (cidade onde são ofertados a
distância), então o mesmo CO_CURSO pode aparecer centenas de vezes. Para
o catálogo de cursos por faculdade, deduplicamos por CO_CURSO, preferindo
nessa ordem: TP_DIMENSAO=3 (linha consolidada do curso, sem polo
específico) > TP_DIMENSAO=1 (sede/presencial) > qualquer outra linha
(fallback para os poucos cursos sem uma linha consolidada).
"""
import csv
import io
import logging

logger = logging.getLogger('suafacul.censo')

NIVEL_ACADEMICO_GRADUACAO = '1'  # ignora "2" (sequencial de formação específica)

_GRAU_ACADEMICO = {'1': 'Bacharelado', '2': 'Licenciatura', '3': 'Tecnológico'}
_MODALIDADE_ENSINO = {'1': 'presencial', '2': 'ead'}

# Prioridade de TP_DIMENSAO ao deduplicar por CO_CURSO — menor valor vence.
# Valores fora deste dict (ex.: "2" = polo específico, "4" = outro) ficam
# por último (prioridade 99), usados só se não houver linha melhor.
_PRIORIDADE_DIMENSAO = {'3': 0, '1': 1}


def _prioridade_dimensao(tp_dimensao):
    return _PRIORIDADE_DIMENSAO.get(tp_dimensao, 99)


def _deduplicar_por_curso(linhas_iteraveis):
    """Recebe um iterável de dicts (uma linha do CSV cada) e devolve só a
    melhor linha por CO_CURSO — sem materializar as ~700 mil linhas
    inteiras em memória, só o resultado deduplicado (~46 mil)."""
    melhores = {}
    prioridades = {}
    total_lido = 0
    ignorados_sequencial = 0

    for linha in linhas_iteraveis:
        total_lido += 1
        if (linha.get('TP_NIVEL_ACADEMICO') or '').strip() != NIVEL_ACADEMICO_GRADUACAO:
            ignorados_sequencial += 1
            continue
        co_curso = (linha.get('CO_CURSO') or '').strip()
        if not co_curso:
            continue
        prioridade = _prioridade_dimensao((linha.get('TP_DIMENSAO') or '').strip())
        if co_curso not in melhores or prioridade < prioridades[co_curso]:
            melhores[co_curso] = linha
            prioridades[co_curso] = prioridade

    logger.info(
        "[censo] %d linhas lidas, %d ignoradas (sequencial), %d cursos únicos após deduplicação.",
        total_lido, ignorados_sequencial, len(melhores)
    )
    return list(melhores.values())


def _linha_para_curso(linha, faculdades_por_codigo_emec):
    co_ies = (linha.get('CO_IES') or '').strip()
    faculdade = faculdades_por_codigo_emec.get(co_ies)
    if not faculdade:
        return None  # instituição não está cadastrada na base local — pula (ver contagem 'sem_faculdade_local')

    nome = (linha.get('NO_CURSO') or '').strip()
    if not nome:
        return None

    grau = _GRAU_ACADEMICO.get((linha.get('TP_GRAU_ACADEMICO') or '').strip())
    modalidade = _MODALIDADE_ENSINO.get((linha.get('TP_MODALIDADE_ENSINO') or '').strip(), 'presencial')
    area = (linha.get('NO_CINE_AREA_GERAL') or '').strip() or None

    return {
        'codigo_inep_curso': (linha.get('CO_CURSO') or '').strip(),
        'nome': nome,
        'instituicao': faculdade['nome'],
        'faculdade_id': faculdade['id'],
        'modalidade': modalidade,
        'grau': grau,
        'area': area,
        'tipo_instituicao': faculdade.get('tipo_instituicao') or 'Pública',
    }


def importar_cursos_de_csv_upload(stream_arquivo):
    """Recebe um arquivo-like (ex.: FileStorage.stream do Flask) do CSV
    oficial MICRODADOS_CADASTRO_CURSOS_<ano>.CSV e importa os cursos de
    graduação vinculados a instituições já cadastradas na base local.

    Processa em streaming (não carrega os ~450MB inteiros como uma string
    em memória) — só o resultado deduplicado (~46 mil linhas) fica em
    memória antes de ir pro banco."""
    # csv.DictReader precisa de um iterável de texto; o arquivo vem em
    # latin-1 (padrão dos microdados do INEP/MEC), delimitado por ';'.
    texto = io.TextIOWrapper(stream_arquivo, encoding='latin-1', newline='')
    leitor = csv.DictReader(texto, delimiter=';')

    if not leitor.fieldnames or 'CO_CURSO' not in leitor.fieldnames:
        raise RuntimeError(
            "Colunas esperadas (CO_CURSO, CO_IES, NO_CURSO...) não encontradas — "
            "confirme que o arquivo é o MICRODADOS_CADASTRO_CURSOS do Censo da Educação Superior."
        )

    cursos_deduplicados = _deduplicar_por_curso(leitor)

    # Carrega o mapa código e-MEC -> faculdade local uma única vez (evita
    # 46 mil SELECTs individuais).
    from app.models.faculdade import Faculdade
    from app.models.curso import Curso
    todas_faculdades = Faculdade().listar({})
    faculdades_por_codigo = {f['codigo_emec']: f for f in todas_faculdades if f.get('codigo_emec')}

    a_importar = []
    sem_faculdade_local = 0
    for linha in cursos_deduplicados:
        curso = _linha_para_curso(linha, faculdades_por_codigo)
        if curso is None:
            sem_faculdade_local += 1
            continue
        a_importar.append(curso)

    resultado_upsert = Curso().upsert_por_codigo_inep_lote(a_importar)

    return {
        'success': True,
        'cursos_no_arquivo': len(cursos_deduplicados),
        'importados': len(a_importar),
        'criados': resultado_upsert['criados'],
        'atualizados': resultado_upsert['atualizados'],
        'sem_faculdade_local': sem_faculdade_local,
    }
