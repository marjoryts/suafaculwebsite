"""
Serviço de validação/automação de vestibulares.

Faz duas coisas, conforme pedido:
  1. Valida a data do vestibular (se já passou, está próxima, ou é inválida)
     e marca um status_validacao ('ativo', 'encerrado', 'data_invalida').
  2. Verifica se a instituição do vestibular já está cadastrada na tabela
     `faculdades` (por nome aproximado) e, se achar, vincula faculdade_id
     e marca cadastrado_ok=1. Se não achar, cadastrado_ok=0 — sinal para o
     admin cadastrar a faculdade correspondente.

Regra de negócio pura: o acesso ao banco fica nos models (Vestibular, Faculdade).
"""
from datetime import date, datetime

from app.models.faculdade import Faculdade
from app.models.vestibular import Vestibular


def _parsear_data(data_str):
    if not data_str:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(data_str.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _normalizar(texto):
    return ''.join(c for c in (texto or '').lower().strip() if c.isalnum() or c.isspace())


def validar_vestibulares(aplicar=False):
    """Roda a validação em todos os vestibulares cadastrados.

    aplicar=False -> só gera o relatório (dry-run), não grava nada no banco.
    aplicar=True  -> grava status_validacao, cadastrado_ok e faculdade_id.
    """
    vestibulares = Vestibular().listar_para_validacao()
    faculdades = Faculdade().listar_id_nome()

    hoje = date.today()
    relatorio = []
    falhas = []

    for v in vestibulares:
        # Cada vestibular é processado isoladamente: um registro com dado
        # inesperado (ex.: instituição nula, data corrompida) não pode
        # interromper a validação dos demais.
        try:
            data_prova = _parsear_data(v.get('data_prova'))
            if data_prova is None:
                status = 'data_invalida'
            elif data_prova >= hoje:
                status = 'ativo'
            else:
                status = 'encerrado'

            faculdade_encontrada = None
            instituicao_norm = _normalizar(v.get('instituicao'))
            if instituicao_norm:
                for f in faculdades:
                    nome_norm = _normalizar(f['nome'])
                    if nome_norm and (nome_norm in instituicao_norm or instituicao_norm in nome_norm):
                        faculdade_encontrada = f
                        break

            relatorio.append({
                'vestibular_id': v['id'],
                'nome': v['nome'],
                'instituicao': v.get('instituicao'),
                'status_validacao': status,
                'data_prova_valida': data_prova.isoformat() if data_prova else None,
                'cadastrado_ok': bool(faculdade_encontrada),
                'faculdade_id': faculdade_encontrada['id'] if faculdade_encontrada else None,
                'faculdade_nome': faculdade_encontrada['nome'] if faculdade_encontrada else None,
            })
        except Exception as e:
            falhas.append({'vestibular_id': v.get('id'), 'nome': v.get('nome'), 'erro': str(e)})
            continue

    if aplicar:
        Vestibular().aplicar_validacoes(relatorio)

    resumo = {
        'total': len(relatorio),
        'ativos': sum(1 for r in relatorio if r['status_validacao'] == 'ativo'),
        'encerrados': sum(1 for r in relatorio if r['status_validacao'] == 'encerrado'),
        'data_invalida': sum(1 for r in relatorio if r['status_validacao'] == 'data_invalida'),
        'sem_faculdade_cadastrada': sum(1 for r in relatorio if not r['cadastrado_ok']),
        'falhas': len(falhas),
        'aplicado': aplicar,
    }
    return {'success': True, 'resumo': resumo, 'itens': relatorio, 'falhas': falhas}
