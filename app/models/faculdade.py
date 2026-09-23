import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.database import get_connection, normalizar
from app.services.busca_service import filtro_localizacao


def _like_contem(texto):
    """Padrão LIKE 'contém' já normalizado (sem acento/minúsculas) e com
    os curingas % e _ escapados — comparar com normalizar(coluna)."""
    texto = normalizar(texto.strip()).replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return f"%{texto}%"


class Faculdade:
    CAMPOS = ['codigo_emec', 'nome', 'sigla', 'organizacao_academica', 'tipo_instituicao',
              'url', 'endereco', 'cidade', 'uf', 'telefone', 'email', 'situacao', 'fonte']

    def _build_where(self, filtros, prefix='f.'):
        sql = " WHERE 1=1"
        params = []
        if filtros.get('tipo_instituicao'):
            sql += f" AND {prefix}tipo_instituicao=?"
            params.append(filtros['tipo_instituicao'])
        if filtros.get('uf'):
            sql += f" AND {prefix}uf=?"
            params.append(filtros['uf'])
        if filtros.get('cidade'):
            # Aceita cidade (parte do nome), sigla de UF ('SP') ou região
            # ('Sudeste') — os três tipos de localização sugeridos pela
            # busca dinâmica (ver app/services/busca_service.py).
            localizacao = filtro_localizacao(filtros['cidade'])
            if localizacao and localizacao[0] == 'uf':
                ufs = localizacao[1]
                sql += f" AND UPPER(TRIM({prefix}uf)) IN ({','.join('?' * len(ufs))})"
                params.extend(ufs)
            elif localizacao:
                sql += f" AND normalizar({prefix}cidade) LIKE ? ESCAPE '\\'"
                params.append(_like_contem(filtros['cidade']))
        if filtros.get('busca'):
            like = _like_contem(filtros['busca'])
            sql += (f" AND (normalizar({prefix}nome) LIKE ? ESCAPE '\\'"
                    f" OR normalizar({prefix}sigla) LIKE ? ESCAPE '\\'"
                    f" OR normalizar({prefix}cidade) LIKE ? ESCAPE '\\')")
            params.extend([like, like, like])
        if filtros.get('curso'):
            sql += (f" AND {prefix}id IN (SELECT faculdade_id FROM cursos WHERE faculdade_id IS NOT NULL"
                    f" AND normalizar(nome) LIKE ? ESCAPE '\\')")
            params.append(_like_contem(filtros['curso']))
        if filtros.get('modalidade'):
            mods = filtros['modalidade'] if isinstance(filtros['modalidade'], list) else [filtros['modalidade']]
            mods = [m for m in mods if m]
            if mods:
                placeholders = ','.join('?' * len(mods))
                sql += f" AND {prefix}id IN (SELECT faculdade_id FROM cursos WHERE faculdade_id IS NOT NULL AND modalidade IN ({placeholders}))"
                params.extend(mods)
        return sql, params

    def listar(self, filtros={}):
        try:
            conn = get_connection()
            c = conn.cursor()
            where, params = self._build_where(filtros)
            sql = ("SELECT f.*, (SELECT COUNT(*) FROM cursos c WHERE c.faculdade_id = f.id) as total_cursos "
                   "FROM faculdades f") + where + " ORDER BY f.nome ASC"
            if 'limit' in filtros and 'offset' in filtros:
                sql += " LIMIT ? OFFSET ?"
                params.extend([filtros['limit'], filtros['offset']])
            c.execute(sql, params)
            rows = [dict(r) for r in c.fetchall()]
            conn.close()
            return rows
        except Exception:
            return []

    def contar(self, filtros={}):
        try:
            conn = get_connection()
            c = conn.cursor()
            where, params = self._build_where(filtros)
            c.execute("SELECT COUNT(*) as total FROM faculdades f" + where, params)
            total = c.fetchone()['total']
            conn.close()
            return total
        except Exception:
            return 0

    def buscar_por_id(self, id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM faculdades WHERE id=?", (id,))
            row = c.fetchone()
            if not row:
                conn.close()
                return None
            faculdade = dict(row)
            c.execute("SELECT id, nome, modalidade, grau, area FROM cursos WHERE faculdade_id=? ORDER BY nome", (id,))
            faculdade['cursos'] = [dict(r) for r in c.fetchall()]
            c.execute("SELECT id, nome, data_prova, periodo_inscricao, link_edital FROM vestibulares WHERE faculdade_id=? ORDER BY data_prova", (id,))
            faculdade['vestibulares'] = [dict(r) for r in c.fetchall()]
            conn.close()
            return faculdade
        except Exception:
            return None

    def buscar_por_codigo_emec(self, codigo_emec):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM faculdades WHERE codigo_emec=?", (str(codigo_emec),))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def criar(self, dados):
        try:
            conn = get_connection()
            c = conn.cursor()
            if dados.get('codigo_emec'):
                c.execute("SELECT id FROM faculdades WHERE codigo_emec=?", (dados['codigo_emec'],))
                if c.fetchone():
                    conn.close()
                    return {'success': False, 'message': 'Já existe uma faculdade com esse código e-MEC.'}
            valores = [dados.get(campo) for campo in self.CAMPOS]
            c.execute(
                f"INSERT INTO faculdades ({','.join(self.CAMPOS)}) VALUES ({','.join('?' * len(self.CAMPOS))})",
                valores
            )
            id = c.lastrowid
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Faculdade cadastrada com sucesso!', 'id': id}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def atualizar(self, id, dados):
        try:
            conn = get_connection()
            c = conn.cursor()
            sets = ', '.join(f"{campo}=?" for campo in self.CAMPOS if campo in dados)
            valores = [dados[campo] for campo in self.CAMPOS if campo in dados]
            if not sets:
                conn.close()
                return {'success': False, 'message': 'Nenhum campo para atualizar.'}
            valores.append(id)
            c.execute(f"UPDATE faculdades SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=?", valores)
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Faculdade atualizada com sucesso!'}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def deletar(self, id):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM faculdades WHERE id=?", (id,))
            conn.commit()
            conn.close()
            return {'success': True, 'message': 'Faculdade removida com sucesso!'}
        except Exception as e:
            return {'success': False, 'message': f'Erro: {str(e)}'}

    def buscar_por_nome_exato(self, nome):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM faculdades WHERE nome=?", (nome,))
            row = c.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def buscar_por_nome_aproximado(self, nome, sigla=None):
        """Match fuzzy: normaliza (minúsculas, sem acento/pontuação) e compara
        por substring nos dois sentidos, ou por sigla exata. Usado para não
        duplicar faculdades já cadastradas manualmente quando o e-MEC retorna
        o nome oficial em formatação diferente (ex.: 'UNIVERSIDADE DE SAO
        PAULO' vs 'USP - Universidade de São Paulo')."""
        import unicodedata

        def normalizar(txt):
            if not txt:
                return ''
            txt = unicodedata.normalize('NFKD', txt).encode('ascii', 'ignore').decode('ascii')
            return ''.join(c for c in txt.lower() if c.isalnum() or c.isspace()).strip()

        alvo = normalizar(nome)
        if not alvo:
            return None
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM faculdades")
            candidatas = [dict(r) for r in c.fetchall()]
            conn.close()
            for f in candidatas:
                if sigla and f.get('sigla') and normalizar(f['sigla']) == normalizar(sigla):
                    return f
                nome_norm = normalizar(f['nome'])
                if nome_norm and (nome_norm in alvo or alvo in nome_norm):
                    return f
            return None
        except Exception:
            return None

    def upsert_por_codigo_emec(self, dados):
        """Cria ou atualiza uma faculdade a partir de um código e-MEC. Usado pela importação automática.
        Evita duplicidade em três camadas: por codigo_emec (import repetido),
        por nome exato, e por nome aproximado (caso a faculdade já exista
        cadastrada manualmente com nome popular, sem codigo_emec ainda —
        nesse caso o código e-MEC é anexado ao registro existente em vez de
        criar uma linha duplicada)."""
        existente = self.buscar_por_codigo_emec(dados.get('codigo_emec'))
        if not existente:
            existente = self.buscar_por_nome_exato(dados.get('nome'))
        if not existente:
            existente = self.buscar_por_nome_aproximado(dados.get('nome'), dados.get('sigla'))
        if existente:
            # Não sobrescreve campos já preenchidos manualmente (url/endereco/cidade/uf/
            # telefone/email/nome) com valores vazios ou "menos amigáveis" (ex.: nome
            # oficial em CAIXA ALTA do e-MEC) vindos da listagem em massa.
            dados_para_atualizar = dict(dados)
            dados_para_atualizar.pop('nome', None)  # preserva o nome já cadastrado
            for campo in ('url', 'endereco', 'cidade', 'uf', 'telefone', 'email', 'sigla'):
                if not dados_para_atualizar.get(campo) and existente.get(campo):
                    dados_para_atualizar.pop(campo, None)
            resultado = self.atualizar(existente['id'], dados_para_atualizar)
            resultado['id'] = existente['id']
            resultado['acao'] = 'atualizada'
            return resultado
        resultado = self.criar(dados)
        resultado['acao'] = 'criada'
        return resultado
