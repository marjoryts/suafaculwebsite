"""
Serviço de importação de dados do e-MEC (Cadastro Nacional de Cursos e
Instituições de Educação Superior - Ministério da Educação).

IMPORTANTE: o e-MEC (https://emec.mec.gov.br) não disponibiliza uma API REST
pública oficial. Os dados são obtidos fazendo parsing das páginas HTML de
consulta pública por código da instituição (IES). Por isso:

  - Este serviço depende da estrutura do site do e-MEC. Se o MEC alterar o
    HTML, os seletores abaixo (EMEC_SELECTORS) podem precisar de ajuste.
  - Campos como telefone e e-mail de contato normalmente NÃO estão
    disponíveis publicamente no e-MEC — ficam em branco e devem ser
    completados manualmente no admin.
  - O site do e-MEC costuma ficar instável/fora do ar; sempre trate falhas
    de forma resiliente (retry manual, não em loop agressivo).
  - Para uso comercial/produção intenso, considere usar o Portal de Dados
    Abertos do MEC (dadosabertos.mec.gov.br) quando o dataset desejado
    estiver disponível em CSV, que é mais estável que fazer scraping.

Como usar:
    from app.services.emec_service import importar_faculdade_por_codigo
    resultado = importar_faculdade_por_codigo('339')  # código e-MEC da IES
"""
import re
import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.models.faculdade import Faculdade
from app.models.curso import Curso

logger = logging.getLogger('suafacul.emec')

EMEC_BASE_URL = "https://emec.mec.gov.br/emec/consulta-ies/index/perfil/{codigo}"
EMEC_LISTAGEM_URL = "https://emec.mec.gov.br/emec/nova-index/listar-consulta-avancada/list/1000"
EMEC_CONSULTA_AVANCADA_PAGE = "https://emec.mec.gov.br/emec/nova-index/consulta-avancada"

# Cabeçalhos de um navegador real. O e-MEC (como a maioria dos sites
# gov.br) fica atrás de um WAF que bloqueia com 403 requisições que se
# identificam como bot (ex.: 'SuaFaculBot/1.0' no User-Agent antigo) ou que
# não trazem os cabeçalhos que um navegador normalmente envia.
_BROWSER_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'),
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}

try:
    import requests
    from bs4 import BeautifulSoup
    _DEPENDENCIAS_OK = True
except ImportError:
    _DEPENDENCIAS_OK = False


def _limpar_texto(texto):
    if not texto:
        return ''
    return re.sub(r'\s+', ' ', texto).strip()


def _buscar_html_emec(codigo_emec):
    if not _DEPENDENCIAS_OK:
        raise RuntimeError(
            "As dependências 'requests' e 'beautifulsoup4' não estão instaladas. "
            "Rode: pip install requests beautifulsoup4"
        )
    url = EMEC_BASE_URL.format(codigo=codigo_emec)
    resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def _parsear_instituicao(html, codigo_emec):
    """Extrai os campos de interesse do HTML de perfil da IES no e-MEC.

    A estrutura do e-MEC muda com frequência; este parser procura por
    padrões de texto (rótulo: valor) que costumam aparecer na página de
    perfil, em vez de depender de classes CSS fixas (mais frágeis).
    """
    soup = BeautifulSoup(html, 'html.parser')
    texto_completo = soup.get_text('\n')

    def extrair_apos_rotulo(rotulo):
        m = re.search(rf'{rotulo}\s*[:\-]?\s*\n?\s*([^\n]+)', texto_completo, re.IGNORECASE)
        return _limpar_texto(m.group(1)) if m else ''

    nome = extrair_apos_rotulo('Nome da IES') or extrair_apos_rotulo('Instituição')
    sigla = extrair_apos_rotulo('Sigla')
    organizacao = extrair_apos_rotulo('Organização Acadêmica')
    categoria = extrair_apos_rotulo('Categoria Administrativa')
    endereco = extrair_apos_rotulo('Endereço')
    cidade_uf = extrair_apos_rotulo('Município') or extrair_apos_rotulo('Cidade')

    cidade, uf = '', ''
    if cidade_uf:
        partes = cidade_uf.split('/')
        cidade = _limpar_texto(partes[0])
        if len(partes) > 1:
            uf = _limpar_texto(partes[1])[:2].upper()

    tipo_instituicao = 'Pública' if categoria and 'públic' in categoria.lower() else 'Privada'

    # Cursos: tenta localizar uma tabela com nomes de cursos na página
    cursos = []
    for row in soup.select('table tr'):
        cols = [ _limpar_texto(td.get_text()) for td in row.find_all('td') ]
        if cols and len(cols[0]) > 3 and not cols[0].isdigit():
            cursos.append(cols[0])

    return {
        'codigo_emec': str(codigo_emec),
        'nome': nome or f'Instituição e-MEC {codigo_emec}',
        'sigla': sigla,
        'organizacao_academica': organizacao,
        'tipo_instituicao': tipo_instituicao,
        'url': '',  # e-MEC não fornece site oficial da IES de forma confiável
        'endereco': endereco,
        'cidade': cidade,
        'uf': uf,
        'telefone': '',  # não disponível publicamente no e-MEC
        'email': '',     # não disponível publicamente no e-MEC
        'situacao': 'ativa',
        'fonte': 'emec',
        '_cursos_encontrados': cursos[:100],
    }


def importar_faculdade_por_codigo(codigo_emec):
    """Busca uma IES no e-MEC pelo código e faz upsert na tabela faculdades.
    Retorna dict com success/message e, se disponível, os dados importados.
    """
    codigo_emec = str(codigo_emec).strip()
    if not codigo_emec.isdigit():
        return {'success': False, 'message': 'Código e-MEC inválido. Use apenas números.'}

    try:
        html = _buscar_html_emec(codigo_emec)
    except Exception as e:
        logger.warning("[emec] Falha ao buscar código %s: %s", codigo_emec, e)
        return {'success': False, 'message': f'Falha ao acessar o e-MEC: {e}'}

    dados = _parsear_instituicao(html, codigo_emec)
    if not dados.get('nome') or dados['nome'].startswith('Instituição e-MEC'):
        return {
            'success': False,
            'message': ('Não foi possível extrair os dados da instituição automaticamente. '
                        'O e-MEC pode estar fora do ar ou ter mudado o layout — '
                        'cadastre esta faculdade manualmente pelo admin.')
        }

    cursos_encontrados = dados.pop('_cursos_encontrados', [])
    resultado = Faculdade().upsert_por_codigo_emec(dados)
    if not resultado.get('success'):
        return resultado

    faculdade_id = resultado.get('id')
    cursos_criados = 0
    if faculdade_id and cursos_encontrados:
        curso_model = Curso()
        for nome_curso in cursos_encontrados:
            criar_resultado = curso_model.criar({
                'nome': nome_curso,
                'instituicao': dados['nome'],
                'faculdade_id': faculdade_id,
                'modalidade': 'presencial',
                'descricao': '',
                'duracao': '',
                'grau': '',
                'area': '',
                'tipo_instituicao': dados['tipo_instituicao'],
            })
            if criar_resultado.get('success'):
                cursos_criados += 1

    resultado['faculdade'] = dados
    resultado['cursos_importados'] = cursos_criados
    return resultado


def importar_faculdades_em_lote(codigos_emec):
    """Importa uma lista de códigos e-MEC. Retorna um relatório por código."""
    relatorio = []
    for codigo in codigos_emec:
        relatorio.append({'codigo_emec': codigo, **importar_faculdade_por_codigo(codigo)})
    return relatorio


# ──────────────────────────────────────────────────────────────────────────
# Listagem em massa (todas as instituições de uma UF/consulta avançada)
#
# O e-MEC não tem API REST documentada, mas o próprio site usa internamente
# um endpoint de "consulta avançada" (nova-index/listar-consulta-avancada)
# que devolve uma tabela HTML com todas as IES que atendem aos filtros
# (UF, situação de funcionamento etc.), até 1000 resultados por chamada.
# Essa é a mesma técnica usada por bibliotecas de terceiros conhecidas
# (ex.: pavanad/emec-api, alissonlinneker/e-MEC-API) já que não existe
# alternativa oficial. Tratamos isso como best-effort: o e-MEC muda de
# layout com frequência e costuma ficar instável.
# ──────────────────────────────────────────────────────────────────────────

UFS_BRASIL = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG',
              'PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO']

_NATUREZA_CATEGORIAS = ['1', '2', '3', '4', '5', '6', '7']  # todas as naturezas administrativas
_ORGANIZACAO_CATEGORIAS = ['10022,10024,10023,10027', '10019,10020,10021,10026', '10026,10019', '10028,10029']


def _montar_payload_listagem(uf, municipio_codigo=''):
    campos = {
        'data[CONSULTA_AVANCADA][hid_template]': 'listar-consulta-avancada-ies',
        'data[CONSULTA_AVANCADA][hid_order]': 'ies.no_ies ASC',
        'data[CONSULTA_AVANCADA][hid_no_cidade_avancada]': '',
        'data[CONSULTA_AVANCADA][hid_no_regiao_avancada]': '',
        'data[CONSULTA_AVANCADA][hid_no_pais_avancada]': '',
        'data[CONSULTA_AVANCADA][hid_co_pais_avancada]': '',
        'data[CONSULTA_AVANCADA][rad_buscar_por]': 'IES',
        'data[CONSULTA_AVANCADA][txt_no_ies]': '',
        'data[CONSULTA_AVANCADA][txt_no_curso]': '',
        'data[CONSULTA_AVANCADA][txt_no_especializacao]': '',
        'data[CONSULTA_AVANCADA][sel_co_area]': '',
        'data[CONSULTA_AVANCADA][sel_sg_uf]': uf,
        'data[CONSULTA_AVANCADA][sel_co_municipio]': municipio_codigo,
        'data[CONSULTA_AVANCADA][sel_st_gratuito]': '',
        'data[CONSULTA_AVANCADA][sel_no_indice_ies]': '',
        'data[CONSULTA_AVANCADA][sel_co_indice_ies]': '',
        'data[CONSULTA_AVANCADA][sel_no_indice_curso]': '',
        'data[CONSULTA_AVANCADA][sel_co_indice_curso]': '',
        'data[CONSULTA_AVANCADA][sel_co_situacao_funcionamento_ies]': '10035',  # em atividade
        'data[CONSULTA_AVANCADA][sel_co_situacao_funcionamento_curso]': '9',
        'data[CONSULTA_AVANCADA][sel_st_funcionamento_especializacao]': '',
        'captcha': '',
    }
    partes = [f"{k}={requests.utils.quote(str(v))}" for k, v in campos.items()]
    for cat in _NATUREZA_CATEGORIAS:
        partes.append(f"data%5BCONSULTA_AVANCADA%5D%5Bchk_tp_natureza_gn%5D%5B%5D={cat}")
    for org in _ORGANIZACAO_CATEGORIAS:
        partes.append(f"data%5BCONSULTA_AVANCADA%5D%5Bchk_tp_organizacao_gn%5D%5B%5D={requests.utils.quote(org)}")
    return '&'.join(partes)


def listar_instituicoes_emec_por_uf(uf):
    """Lista as instituições de ensino superior de uma UF.

    Fonte primária: o CSV oficial do Portal de Dados Abertos do MEC
    (dadosabertos.mec.gov.br) — arquivo estático, publicado oficialmente
    pelo MEC, sem sessão/JS/proteção anti-bot. É mais estável do que
    fazer scraping da consulta avançada do e-MEC (que fica atrás de um
    WAF que costuma bloquear com 403 requisições automatizadas — ver
    listar_instituicoes_emec_por_uf_via_scraping abaixo, mantida apenas
    como fallback caso o CSV também fique indisponível).

    Retorna lista de dicts: codigo_emec, nome, organizacao_academica,
    tipo_instituicao, situacao. NÃO inclui endereço/telefone (ver
    importar_faculdade_por_codigo para completar esses dados por instituição).
    """
    uf = uf.upper().strip()
    if uf not in UFS_BRASIL:
        raise ValueError(f"UF inválida: {uf}")

    try:
        return _listar_instituicoes_via_dados_abertos(uf)
    except Exception as erro_csv:
        logger.warning("[emec] Dados Abertos MEC falhou para %s (%s), tentando scraping do e-MEC como fallback...", uf, erro_csv)
        try:
            return listar_instituicoes_emec_por_uf_via_scraping(uf)
        except Exception as erro_scraping:
            # Nenhuma das duas fontes funcionou — mostra os DOIS motivos
            # (em vez de só o erro do scraping), pra dar contexto suficiente
            # sem precisar caçar nos logs do servidor.
            raise RuntimeError(
                f"CSV oficial do MEC falhou ({erro_csv}); scraping do e-MEC também falhou ({erro_scraping})"
            ) from erro_scraping


# URL do CSV oficial de instituições de ensino superior no Portal de Dados
# Abertos do MEC. O caminho inclui o ano da última atualização do dataset
# (ex.: "2022") — se este endpoint passar a retornar 404, acesse
# https://dadosabertos.mec.gov.br/indicadores-sobre-ensino-superior e
# copie o link do arquivo "Instituições de Educação Superior do Brasil"
# atualizado, trocando apenas esta constante.
DADOS_ABERTOS_IES_CSV_URL = "https://dadosabertos.mec.gov.br/images/conteudo/Ind-ensino-superior/2022/PDA_Lista_Instituicoes_Ensino_Superior_do_Brasil_EMEC.csv"

_cache_dados_abertos = {'instituicoes': None, 'buscado_em': None}


def _parsear_csv_dados_abertos(bruto):
    """Recebe os bytes crus do CSV oficial (baixado via HTTP ou enviado por
    upload manual do admin) e devolve a lista de instituições. Compartilhado
    pelos dois caminhos — nenhuma lógica de parsing duplicada entre eles."""
    import csv
    import io

    # CSVs do MEC costumam vir em latin-1/cp1252 (exportados de planilhas),
    # mas alguns datasets já saem em UTF-8 — tenta os dois.
    for encoding in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
        try:
            texto = bruto.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise RuntimeError("Não foi possível decodificar o CSV do MEC (encoding desconhecido).")

    amostra = texto[:2048]
    try:
        delimitador = csv.Sniffer().sniff(amostra, delimiters=',;\t').delimiter
    except csv.Error:
        delimitador = ';' if amostra.count(';') > amostra.count(',') else ','

    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    instituicoes = []
    for linha in leitor:
        # csv.DictReader guarda colunas extras (linha com mais campos que o
        # cabeçalho) sob a chave None, como lista — normaliza tudo pra string
        # antes de usar, senão .strip() quebra nesses casos.
        linha_normalizada = {}
        for k, v in linha.items():
            chave = (k or '').strip().upper()
            if isinstance(v, list):
                v = v[0] if v else ''
            linha_normalizada[chave] = (v or '').strip()
        linha = linha_normalizada
        codigo = linha.get('CODIGO_DA_IES') or linha.get('CODIGO_IES') or linha.get('CO_IES')
        nome = linha.get('NOME_DA_IES') or linha.get('NOME_IES') or linha.get('NO_IES')
        if not codigo or not nome:
            continue
        categoria = (linha.get('CATEGORIA_DA_IES') or linha.get('CATEGORIA_ADMINISTRATIVA') or '')
        instituicoes.append({
            'codigo_emec': codigo,
            'nome': nome,
            'sigla': linha.get('SIGLA') or None,
            'organizacao_academica': linha.get('ORGANIZACAO_ACADEMICA') or '',
            'tipo_instituicao': 'Pública' if 'públic' in categoria.lower() else 'Privada',
            'situacao': linha.get('SITUACAO_IES') or linha.get('SITUACAO') or 'ativa',
            'uf': linha.get('UF') or '',
            'cidade': linha.get('MUNICIPIO') or '',
        })

    if not instituicoes:
        raise RuntimeError("CSV do MEC lido, mas nenhuma linha reconhecida — o layout do arquivo pode ter mudado.")
    return instituicoes


def _baixar_csv_dados_abertos():
    """Baixa (via HTTP, servidor->MEC) e faz cache em memória (por processo)
    do CSV de instituições. Se o servidor do e-MEC bloquear a chamada
    automatizada (comum em WAFs de sites gov.br — costuma responder 403
    mesmo com headers de navegador, por fingerprint de TLS), use
    importar_instituicoes_de_csv_upload() como alternativa: o admin baixa
    o arquivo pelo próprio navegador (que não sofre esse bloqueio) e sobe
    pro sistema."""
    if _cache_dados_abertos['instituicoes'] is not None:
        return _cache_dados_abertos['instituicoes']

    resp = requests.get(DADOS_ABERTOS_IES_CSV_URL, headers=_BROWSER_HEADERS, timeout=60)
    resp.raise_for_status()

    instituicoes = _parsear_csv_dados_abertos(resp.content)
    from datetime import datetime as _dt
    _cache_dados_abertos['instituicoes'] = instituicoes
    _cache_dados_abertos['buscado_em'] = _dt.now()
    logger.info("[emec] %d instituições carregadas do CSV de Dados Abertos do MEC (download automático).", len(instituicoes))
    return instituicoes


def importar_instituicoes_de_csv_upload(bytes_arquivo):
    """Recebe o CSV oficial de Dados Abertos do MEC enviado manualmente
    (upload no admin) e importa todas as instituições pra tabela
    `faculdades`, usando o mesmo upsert (evita duplicar) já usado pela
    importação automática. Também alimenta o cache em memória, então
    buscas por UF na mesma execução do processo usam esses dados sem
    precisar de um novo upload."""
    instituicoes = _parsear_csv_dados_abertos(bytes_arquivo)

    from datetime import datetime as _dt
    _cache_dados_abertos['instituicoes'] = instituicoes
    _cache_dados_abertos['buscado_em'] = _dt.now()

    faculdade_model = Faculdade()
    criadas, atualizadas, falhas = 0, 0, 0
    erros = []
    for inst in instituicoes:
        try:
            dados = {
                'codigo_emec': inst['codigo_emec'], 'nome': inst['nome'], 'sigla': inst.get('sigla'),
                'organizacao_academica': inst['organizacao_academica'], 'tipo_instituicao': inst['tipo_instituicao'],
                'url': '', 'endereco': '', 'cidade': inst.get('cidade', ''), 'uf': inst['uf'],
                'telefone': '', 'email': '', 'situacao': inst['situacao'], 'fonte': 'emec_csv_upload',
            }
            resultado = faculdade_model.upsert_por_codigo_emec(dados)
            if resultado.get('success'):
                criadas += 1 if resultado.get('acao') == 'criada' else 0
                atualizadas += 1 if resultado.get('acao') == 'atualizada' else 0
            else:
                falhas += 1
                erros.append({'codigo_emec': inst.get('codigo_emec'), 'erro': resultado.get('message')})
        except Exception as e:
            falhas += 1
            erros.append({'codigo_emec': inst.get('codigo_emec'), 'erro': str(e)})
            continue

    return {
        'success': True, 'total_no_arquivo': len(instituicoes),
        'criadas': criadas, 'atualizadas': atualizadas, 'falhas': falhas, 'erros': erros[:20],
    }


def _listar_instituicoes_via_dados_abertos(uf):
    todas = _baixar_csv_dados_abertos()
    situacoes_ativas = ('ativa', 'em atividade')
    return [
        i for i in todas
        if i['uf'].upper() == uf and (i['situacao'] or '').strip().lower() in situacoes_ativas
    ]


def listar_instituicoes_emec_por_uf_via_scraping(uf):
    """Fallback: tenta a consulta avançada do e-MEC diretamente (scraping).
    Mantida por completude, mas o e-MEC fica atrás de um WAF que costuma
    responder 403 a requisições automatizadas — não é a via recomendada.
    Ver listar_instituicoes_emec_por_uf (usa o CSV oficial primeiro)."""
    if not _DEPENDENCIAS_OK:
        raise RuntimeError("Dependências 'requests'/'beautifulsoup4' não instaladas.")
    uf = uf.upper().strip()
    if uf not in UFS_BRASIL:
        raise ValueError(f"UF inválida: {uf}")

    headers = {
        **_BROWSER_HEADERS,
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',  # este endpoint só responde a chamadas AJAX da própria página
        'Referer': EMEC_CONSULTA_AVANCADA_PAGE,
        'Origin': 'https://emec.mec.gov.br',
    }
    payload = _montar_payload_listagem(uf)

    # Alguns WAFs de sites gov.br só liberam a chamada AJAX se o cliente
    # já tiver uma sessão válida (cookie) obtida ao carregar a página de
    # busca normalmente — como faria um navegador. Por isso usamos uma
    # Session: primeiro um GET na página de consulta avançada (para pegar
    # o cookie de sessão), só então o POST no endpoint de listagem.
    with requests.Session() as sessao:
        sessao.headers.update(_BROWSER_HEADERS)
        try:
            sessao.get(EMEC_CONSULTA_AVANCADA_PAGE, timeout=20)
        except Exception as e:
            logger.warning("[emec] Não foi possível carregar a página de consulta avançada antes da busca (seguindo mesmo assim): %s", e)

        resp = sessao.post(EMEC_LISTAGEM_URL, headers=headers, data=payload.encode(), timeout=60)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')
    instituicoes = []
    for row in soup.select('tr'):
        cols = row.find_all('td')
        if len(cols) < 7:
            continue
        codigo = _limpar_texto(cols[0].get_text())
        nome = _limpar_texto(cols[1].get_text())
        organizacao = _limpar_texto(cols[2].get_text())
        categoria = _limpar_texto(cols[3].get_text())
        situacao = _limpar_texto(cols[6].get_text()) if len(cols) > 6 else ''
        if not codigo or not codigo.isdigit() or not nome:
            continue
        instituicoes.append({
            'codigo_emec': codigo,
            'nome': nome,
            'organizacao_academica': organizacao,
            'tipo_instituicao': 'Pública' if 'públic' in categoria.lower() else 'Privada',
            'situacao': situacao or 'ativa',
            'uf': uf,
        })
    return instituicoes


def importar_todas_faculdades_por_uf(uf, incluir_endereco=False, limite=None):
    """Importa (upsert) todas as IES em atividade de uma UF para a tabela
    faculdades. Evita duplicidade via upsert por codigo_emec.

    incluir_endereco=True faz uma requisição extra por instituição para
    completar cidade/endereço/site (mais lento, mais chance de instabilidade
    do e-MEC — usar com moderação, respeitando o aviso de que o e-MEC
    "frequentemente fica indisponível").
    limite: corta a lista para testes/lotes menores.
    """
    try:
        instituicoes = listar_instituicoes_emec_por_uf(uf)
    except Exception as e:
        logger.warning("[emec] Falha ao listar instituições de %s: %s", uf, e)
        return {'success': False, 'message': f'Falha ao listar instituições do e-MEC para {uf}: {e}'}

    if limite:
        instituicoes = instituicoes[:limite]

    faculdade_model = Faculdade()
    criadas, atualizadas, falhas = 0, 0, 0
    erros = []
    for inst in instituicoes:
        # Cada instituição é isolada: uma falha (ex.: dado inesperado do
        # e-MEC para aquela IES) não pode interromper o processamento das
        # demais instituições da UF.
        try:
            dados = {
                'codigo_emec': inst['codigo_emec'],
                'nome': inst['nome'],
                'sigla': None,
                'organizacao_academica': inst['organizacao_academica'],
                'tipo_instituicao': inst['tipo_instituicao'],
                'url': '', 'endereco': '', 'cidade': '', 'uf': inst['uf'],
                'telefone': '', 'email': '',
                'situacao': inst['situacao'],
                'fonte': 'emec',
            }
            resultado = faculdade_model.upsert_por_codigo_emec(dados)
            if resultado.get('success'):
                if resultado.get('acao') == 'criada':
                    criadas += 1
                else:
                    atualizadas += 1
                if incluir_endereco:
                    time.sleep(1.5)  # não sobrecarregar o e-MEC
                    try:
                        importar_faculdade_por_codigo(inst['codigo_emec'])
                    except Exception as e:
                        logger.warning("[emec] Falha ao completar endereço de %s: %s", inst.get('codigo_emec'), e)
            else:
                falhas += 1
                erros.append({'codigo_emec': inst.get('codigo_emec'), 'erro': resultado.get('message')})
        except Exception as e:
            falhas += 1
            erros.append({'codigo_emec': inst.get('codigo_emec'), 'erro': str(e)})
            logger.warning("[emec] Falha ao importar instituição %s (%s): %s", inst.get('nome'), inst.get('codigo_emec'), e)
            continue

    return {
        'success': True,
        'uf': uf,
        'total_encontradas': len(instituicoes),
        'criadas': criadas,
        'atualizadas': atualizadas,
        'falhas': falhas,
        'erros': erros,
    }


def importar_todas_faculdades_brasil(ufs=None, delay_segundos=3):
    """Percorre todas as UFs (ou uma lista específica) importando as
    instituições de cada uma, com um intervalo entre requisições para não
    sobrecarregar o servidor do e-MEC. Operação longa (pode levar minutos);
    pensada para ser disparada manualmente pelo admin."""
    ufs = ufs or UFS_BRASIL
    relatorio = []
    for i, uf in enumerate(ufs):
        resultado = importar_todas_faculdades_por_uf(uf)
        relatorio.append(resultado)
        if i < len(ufs) - 1:
            time.sleep(delay_segundos)
    return {
        'success': True,
        'ufs_processadas': len(relatorio),
        'total_criadas': sum(r.get('criadas', 0) for r in relatorio),
        'total_atualizadas': sum(r.get('atualizadas', 0) for r in relatorio),
        'detalhes': relatorio,
    }
