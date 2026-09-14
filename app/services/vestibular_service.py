"""
Serviço de validação/automação de vestibulares.

Faz duas coisas, conforme pedido:
  1. Valida a data do vestibular (se já passou, está próxima, ou é inválida)
     e marca um status_validacao ('ativo', 'encerrado', 'data_invalida').
  2. Verifica se a instituição do vestibular já está cadastrada na tabela
     `faculdades` (por nome aproximado) e, se achar, vincula faculdade_id
     e marca cadastrado_ok=1. Se não achar, cadastrado_ok=0 — sinal para o
     admin cadastrar a faculdade correspondente.
"""
import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection


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
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, nome, instituicao, data_prova, faculdade_id FROM vestibulares")
    vestibulares = [dict(r) for r in c.fetchall()]

    c.execute("SELECT id, nome FROM faculdades")
    faculdades = [dict(r) for r in c.fetchall()]

    hoje = date.today()
    relatorio = []

    for v in vestibulares:
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

        item = {
            'vestibular_id': v['id'],
            'nome': v['nome'],
            'instituicao': v.get('instituicao'),
            'status_validacao': status,
            'data_prova_valida': data_prova.isoformat() if data_prova else None,
            'cadastrado_ok': bool(faculdade_encontrada),
            'faculdade_id': faculdade_encontrada['id'] if faculdade_encontrada else None,
            'faculdade_nome': faculdade_encontrada['nome'] if faculdade_encontrada else None,
        }
        relatorio.append(item)

        if aplicar:
            c.execute(
                """UPDATE vestibulares
                   SET status_validacao=?, cadastrado_ok=?, faculdade_id=COALESCE(?, faculdade_id),
                       ultima_validacao=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (status, 1 if faculdade_encontrada else 0,
                 faculdade_encontrada['id'] if faculdade_encontrada else None, v['id'])
            )

    if aplicar:
        conn.commit()
    conn.close()

    resumo = {
        'total': len(relatorio),
        'ativos': sum(1 for r in relatorio if r['status_validacao'] == 'ativo'),
        'encerrados': sum(1 for r in relatorio if r['status_validacao'] == 'encerrado'),
        'data_invalida': sum(1 for r in relatorio if r['status_validacao'] == 'data_invalida'),
        'sem_faculdade_cadastrada': sum(1 for r in relatorio if not r['cadastrado_ok']),
        'aplicado': aplicar,
    }
    return {'success': True, 'resumo': resumo, 'itens': relatorio}
