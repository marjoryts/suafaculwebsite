import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import json
from config.database import get_connection

# Nomes exibidos para cada chave de perfil salva em perfil_principal.
# A pontuação e a compatibilidade com cursos ficam em
# app/services/vocacional_service.py.
PERFIS = {
    'tecnico': 'Perfil Técnico / Exato',
    'criativo': 'Perfil Criativo / Comunicativo',
    'humano': 'Perfil Humano / Social',
    'gestao': 'Perfil Gestão / Negócios',
    'cientifico': 'Perfil Científico / Investigativo',
    'pratico': 'Perfil Prático / Operacional',
}

class TesteVocacional:
    def salvar_resultado(self, dados):
        try:
            conn = get_connection()
            c = conn.cursor()
            usuario_id = dados.get('usuario_id')
            if not usuario_id:
                usuario_id = None
            c.execute(
                "INSERT INTO teste_vocacional_resultados (usuario_id, perfil_principal, perfis_json, respostas_json) VALUES (?,?,?,?)",
                (usuario_id, dados['perfil_principal'], dados.get('perfis_json', '{}'), dados.get('respostas_json'))
            )
            novo_id = c.lastrowid
            conn.commit()
            conn.close()
            return {'success': True, 'id': novo_id}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def buscar_por_id(self, resultado_id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "SELECT id, usuario_id, perfil_principal, perfis_json, created_at "
                "FROM teste_vocacional_resultados WHERE id=?", (resultado_id,)
            )
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def ultimo_do_usuario(self, usuario_id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "SELECT id, usuario_id, perfil_principal, perfis_json, created_at "
                "FROM teste_vocacional_resultados WHERE usuario_id=? "
                "ORDER BY created_at DESC, id DESC LIMIT 1", (usuario_id,)
            )
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def vincular_a_usuario(self, resultado_id, usuario_id):
        """Associa um resultado feito sem login à conta que acabou de se
        autenticar. Só vincula resultados ainda sem dono (usuario_id NULL),
        então nunca transfere o teste de uma conta para outra."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "UPDATE teste_vocacional_resultados SET usuario_id=? "
                "WHERE id=? AND usuario_id IS NULL", (usuario_id, resultado_id)
            )
            alterado = c.rowcount > 0
            conn.commit()
            conn.close()
            return alterado
        except Exception:
            return False

    def listar_por_usuario(self, usuario_id, limite=10):
        """Resultados do usuário, do mais recente para o mais antigo, com o
        nome do perfil e a pontuação de cada perfil (0–100%) prontos para
        exibir no dashboard."""
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "SELECT id, perfil_principal, perfis_json, created_at FROM teste_vocacional_resultados "
                "WHERE usuario_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
                (usuario_id, limite)
            )
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
        except Exception:
            return []
        resultados = []
        for r in rows:
            try:
                scores = (json.loads(r.get('perfis_json') or '{}') or {}).get('scores') or {}
            except (ValueError, AttributeError):
                scores = {}
            total = sum(v for v in scores.values() if isinstance(v, (int, float))) or 0
            pontuacoes = sorted(
                ({'chave': k, 'nome': PERFIS.get(k, k),
                  'percentual': round(100 * v / total) if total else 0}
                 for k, v in scores.items() if isinstance(v, (int, float))),
                key=lambda p: p['percentual'], reverse=True
            )
            resultados.append({
                'id': r['id'],
                'perfil': r['perfil_principal'],
                'perfil_nome': PERFIS.get(r['perfil_principal'], r['perfil_principal']),
                'created_at': r['created_at'],
                'pontuacoes': pontuacoes,
            })
        return resultados
