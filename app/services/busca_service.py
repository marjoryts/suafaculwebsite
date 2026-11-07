"""Busca dinâmica (sugestões enquanto o usuário digita) por localizações,
faculdades e cursos — usada pelo card de busca da home e de /faculdades
(ver public/js/busca-sugestoes.js e a rota /api/busca/sugestoes).

Tudo vem do banco:
  - cursos       → tabela cursos (nomes distintos)
  - faculdades   → tabela faculdades (nome e sigla)
  - localizações → cidades/UFs da tabela faculdades, agrupadas também por
                   estado e por região

A comparação ignora acentos e maiúsculas (ver sql_norm() em
config/database.py; o SQL fica em app/models/busca.py) e aceita qualquer parte do nome; os resultados que
começam com o termo vêm primeiro, depois os que têm uma palavra começando
com ele, depois os que só o contêm no meio.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.models.busca import BuscaRepository
from config.database import normalizar

TAMANHO_MINIMO = 2
LIMITE_PADRAO = 5
TIPOS = ('local', 'faculdade', 'curso')

# Referência geográfica fixa (nomes oficiais das UFs e suas regiões). Não é
# dado de conteúdo: só estados/regiões que têm faculdades cadastradas no
# banco aparecem nas sugestões.
UFS = {
    'AC': ('Acre', 'Norte'), 'AL': ('Alagoas', 'Nordeste'), 'AP': ('Amapá', 'Norte'),
    'AM': ('Amazonas', 'Norte'), 'BA': ('Bahia', 'Nordeste'), 'CE': ('Ceará', 'Nordeste'),
    'DF': ('Distrito Federal', 'Centro-Oeste'), 'ES': ('Espírito Santo', 'Sudeste'),
    'GO': ('Goiás', 'Centro-Oeste'), 'MA': ('Maranhão', 'Nordeste'),
    'MT': ('Mato Grosso', 'Centro-Oeste'), 'MS': ('Mato Grosso do Sul', 'Centro-Oeste'),
    'MG': ('Minas Gerais', 'Sudeste'), 'PA': ('Pará', 'Norte'), 'PB': ('Paraíba', 'Nordeste'),
    'PR': ('Paraná', 'Sul'), 'PE': ('Pernambuco', 'Nordeste'), 'PI': ('Piauí', 'Nordeste'),
    'RJ': ('Rio de Janeiro', 'Sudeste'), 'RN': ('Rio Grande do Norte', 'Nordeste'),
    'RS': ('Rio Grande do Sul', 'Sul'), 'RO': ('Rondônia', 'Norte'), 'RR': ('Roraima', 'Norte'),
    'SC': ('Santa Catarina', 'Sul'), 'SP': ('São Paulo', 'Sudeste'), 'SE': ('Sergipe', 'Nordeste'),
    'TO': ('Tocantins', 'Norte'),
}
REGIOES = ('Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul')


def _escapar_like(termo):
    return termo.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _rank(texto, termo_norm):
    """0 = começa com o termo, 1 = alguma palavra começa com ele,
    2 = contém no meio, None = não casa."""
    t = normalizar(texto or '')
    if not t or termo_norm not in t:
        return None
    if t.startswith(termo_norm):
        return 0
    for sep in (' ', '-', '/', '(', '.'):
        if (sep + termo_norm) in t:
            return 1
    return 2


def _plural(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def _params_like(termo_norm, limite):
    e = _escapar_like(termo_norm)
    return {'contem': f'%{e}%', 'prefixo': f'{e}%', 'palavra': f'% {e}%',
            'palavra_hifen': f'%-{e}%', 'limite': limite}


def _sugestoes_cursos(repo, termo_norm, limite):
    itens = []
    for r in repo.cursos(_params_like(termo_norm, limite)):
        detalhe = [r['area']] if r['area'] else []
        detalhe.append(_plural(r['total'], 'instituição', 'instituições'))
        itens.append({
            'tipo': 'curso', 'campo': 'curso',
            'valor': r['nome'], 'rotulo': r['nome'],
            'detalhe': ' · '.join(detalhe),
        })
    return itens


def _sugestoes_faculdades(repo, termo_norm, limite):
    itens = []
    for r in repo.faculdades(_params_like(termo_norm, limite)):
        local = '/'.join(p for p in (r['cidade'], r['uf']) if p)
        detalhe = ' · '.join(p for p in (local, r['tipo_instituicao']) if p)
        itens.append({
            'tipo': 'faculdade', 'campo': 'faculdade', 'id': r['id'],
            'valor': r['nome'], 'rotulo': r['nome'], 'detalhe': detalhe,
        })
    return itens


def _sugestoes_localizacoes(repo, termo_norm, limite):
    candidatos = []  # (rank, ordem_do_subtipo, -total, rotulo, item)

    # Cidades: agrupadas no banco, com quantas faculdades existem em cada uma.
    for r in repo.cidades(_params_like(termo_norm, limite)):
        candidatos.append((r['rank'], 0, -r['total'], r['cidade'], {
            'tipo': 'local', 'subtipo': 'cidade', 'campo': 'cidade',
            'valor': r['cidade'], 'rotulo': r['cidade'],
            'detalhe': ' · '.join(p for p in (r['uf'], _plural(r['total'], 'faculdade', 'faculdades')) if p),
        }))

    # Estados e regiões: derivados das UFs que existem na tabela faculdades.
    por_uf = {r['uf']: r['total'] for r in repo.contagem_por_uf() if r['uf'] in UFS}

    por_regiao = {}
    for uf, total in por_uf.items():
        nome, regiao = UFS[uf]
        rank_uf = 0 if termo_norm == uf.lower() else _rank(nome, termo_norm)
        if rank_uf is not None:
            candidatos.append((rank_uf, 1, -total, nome, {
                'tipo': 'local', 'subtipo': 'estado', 'campo': 'cidade',
                'valor': uf, 'rotulo': nome,
                'detalhe': f"Estado ({uf}) · {_plural(total, 'faculdade', 'faculdades')}",
            }))
        por_regiao[regiao] = por_regiao.get(regiao, 0) + total

    for regiao, total in por_regiao.items():
        rank_regiao = _rank(regiao, termo_norm)
        if rank_regiao is not None:
            candidatos.append((rank_regiao, 2, -total, regiao, {
                'tipo': 'local', 'subtipo': 'regiao', 'campo': 'cidade',
                'valor': regiao, 'rotulo': regiao,
                'detalhe': f"Região · {_plural(total, 'faculdade', 'faculdades')}",
            }))

    candidatos.sort(key=lambda x: (x[0], x[1], x[2], normalizar(x[3])))
    return [item for *_, item in candidatos[:limite]]


def sugestoes(termo, tipos=TIPOS, limite=LIMITE_PADRAO):
    """Sugestões agrupadas por tipo para o termo digitado.

    Retorna {'local': [...], 'faculdade': [...], 'curso': [...]} (só os
    tipos pedidos). Cada item tem: tipo, campo (qual campo do formulário
    de busca ele preenche), valor (o texto aplicado no filtro), rotulo e
    detalhe (texto exibido na lista)."""
    termo_norm = normalizar((termo or '').strip())
    tipos = [t for t in tipos if t in TIPOS] or list(TIPOS)
    resultado = {t: [] for t in tipos}
    if len(termo_norm) < TAMANHO_MINIMO:
        return resultado
    limite = max(1, min(int(limite), 10))
    try:
        repo = BuscaRepository()
        if 'local' in resultado:
            resultado['local'] = _sugestoes_localizacoes(repo, termo_norm, limite)
        if 'faculdade' in resultado:
            resultado['faculdade'] = _sugestoes_faculdades(repo, termo_norm, limite)
        if 'curso' in resultado:
            resultado['curso'] = _sugestoes_cursos(repo, termo_norm, limite)
    except Exception:
        return {t: [] for t in tipos}
    return resultado


def filtro_localizacao(valor):
    """Interpreta o texto do campo de localização da busca de faculdades.

    'SP' (sigla de UF)          → ('uf', ['SP'])
    'Sudeste' (nome de região)  → ('uf', [UFs da região])
    qualquer outro texto        → ('cidade', 'texto normalizado') — casa
                                  com parte do nome da cidade.
    """
    texto = normalizar((valor or '').strip())
    if not texto:
        return None
    if len(texto) == 2 and texto.upper() in UFS:
        return ('uf', [texto.upper()])
    for regiao in REGIOES:
        if texto == normalizar(regiao):
            return ('uf', sorted(uf for uf, (_, r) in UFS.items() if r == regiao))
    return ('cidade', texto)
