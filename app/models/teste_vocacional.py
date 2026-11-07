"""Persistência dos resultados do Teste Vocacional. As regras ficam em
app/services/teste_vocacional_service.py (pontuação) e vocacional_service.py
(compatibilidade com os cursos); os nomes dos perfis em teste_vocacional_dados.py."""
from config.database import get_connection, inserir

class TesteVocacional:
    def salvar_resultado(self, dados):
        try:
            conn = get_connection()
            c = conn.cursor()
            usuario_id = dados.get('usuario_id') or None
            id = inserir(
                c,
                "INSERT INTO teste_vocacional_resultados (usuario_id, perfil_principal, perfis_json, respostas_json) VALUES (?,?,?,?)",
                (usuario_id, dados['perfil_principal'], dados.get('perfis_json', '{}'), dados.get('respostas_json'))
            )
            conn.commit()
            conn.close()
            return {'success': True, 'id': id}
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
        """Linhas cruas do usuário, da mais recente para a mais antiga."""
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
            return rows
        except Exception:
            return []
