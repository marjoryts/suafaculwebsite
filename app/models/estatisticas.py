"""Contagens agregadas para o painel administrativo (somente leitura)."""
from config.database import agora_utc_str, get_connection


class Estatisticas:
    def resumo_admin(self):
        """Dicionário com os totais exibidos no painel /admin."""
        consultas = {
            'total_usuarios': ("SELECT COUNT(*) FROM usuarios", ()),
            'total_admins': ("SELECT COUNT(*) FROM usuarios WHERE tipo='admin'", ()),
            'total_cursos': ("SELECT COUNT(*) FROM cursos", ()),
            'total_faculdades': ("SELECT COUNT(*) FROM faculdades", ()),
            'faculdades_importadas_emec': ("SELECT COUNT(*) FROM faculdades WHERE fonte='emec'", ()),
            'total_vestibulares': ("SELECT COUNT(*) FROM vestibulares", ()),
            'vestibulares_ativos': ("SELECT COUNT(*) FROM vestibulares WHERE status_validacao='ativo'", ()),
            'vestibulares_sem_faculdade': ("SELECT COUNT(*) FROM vestibulares WHERE cadastrado_ok=0", ()),
            'vestibulares_encerrados': ("SELECT COUNT(*) FROM vestibulares WHERE status_validacao='encerrado'", ()),
            'total_alunos': ("SELECT COUNT(*) FROM usuarios WHERE tipo='aluno'", ()),
            'novos_usuarios_30d': ("SELECT COUNT(*) FROM usuarios WHERE created_at >= ?", (agora_utc_str(30),)),
            'total_favoritos': ("SELECT COUNT(*) FROM favoritos", ()),
            'total_testes_vocacionais': ("SELECT COUNT(*) FROM teste_vocacional_resultados", ()),
            'faculdades_com_cursos': ("SELECT COUNT(DISTINCT faculdade_id) FROM cursos WHERE faculdade_id IS NOT NULL", ()),
        }
        conn = get_connection()
        try:
            c = conn.cursor()
            resultado = {}
            for chave, (sql, params) in consultas.items():
                c.execute(sql, params)
                resultado[chave] = c.fetchone()[0]
            return resultado
        finally:
            conn.close()
