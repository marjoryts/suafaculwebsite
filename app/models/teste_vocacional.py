import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection

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
            conn.commit()
            conn.close()
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}
