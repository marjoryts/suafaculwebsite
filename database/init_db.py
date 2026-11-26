"""Inicialização do banco PostgreSQL (Supabase): esquema + dados de referência.

1. Esquema: aplica as migrations de `supabase/migrations/` que ainda não
   constam em `public.suafacul_migracoes`. Precisa de um papel com DDL
   (o `postgres` do Supabase, ou o CLI `supabase db push`). Com o papel da
   aplicação (`suafacul_backend`, sem DDL) as migrations já devem ter sido
   aplicadas — se faltar alguma, o erro diz o que fazer.
2. Dados de referência reais e documentados (catálogo de cursos e
   instituições, vestibulares de fontes oficiais), sem duplicar nem
   sobrescrever o que o admin editou; e o primeiro admin a partir de
   SUAFACUL_ADMIN_PASSWORD (nunca há credencial padrão no código).

Tudo numa única transação protegida por `pg_advisory_xact_lock`: várias
instâncias subindo juntas (Vercel, gunicorn) esperam a primeira terminar
e encontram o seed pronto. Idempotente: rodar de novo não duplica nada.

Bancos SQLite antigos são copiados por scripts/migrar_sqlite_para_postgres.py.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import psycopg  # noqa: E402

from config.database import conexao_direta, descrever_destino, get_connection, inserir, sql_norm  # noqa: E402

PASTA_MIGRACOES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'supabase', 'migrations')
# Chave arbitrária e fixa da trava de inicialização (pg_advisory_xact_lock).
_CHAVE_TRAVA_INIT = 7_402_196_001


def arquivos_de_migracao():
    """[(versao, caminho)] em ordem. A versão é o prefixo numérico do nome."""
    arquivos = sorted(glob.glob(os.path.join(PASTA_MIGRACOES, '*.sql')))
    return [(os.path.basename(a).split('_', 1)[0], a) for a in arquivos]


def migracoes_pendentes(conn):
    c = conn.cursor()
    c.execute("SELECT to_regclass('public.suafacul_migracoes') IS NOT NULL")
    aplicadas = set()
    if c.fetchone()[0]:
        c.execute("SELECT versao FROM public.suafacul_migracoes")
        aplicadas = {r[0] for r in c.fetchall()}
    return [(v, a) for v, a in arquivos_de_migracao() if v not in aplicadas]


def aplicar_migracoes(conn):
    """Aplica as migrations pendentes (na transação de `conn`). Devolve as versões."""
    aplicadas = []
    for versao, caminho in migracoes_pendentes(conn):
        with open(caminho, encoding='utf-8') as f:
            sql = f.read()
        try:
            conn.executar_script(sql)
        except psycopg.errors.InsufficientPrivilege as e:
            raise RuntimeError(
                f"A migration {os.path.basename(caminho)} ainda não foi aplicada e o usuário da "
                f"DATABASE_URL não tem permissão de DDL ({e.diag.message_primary}). Aplique as "
                "migrations de supabase/migrations/ com o papel postgres (SQL Editor do Supabase "
                "ou `supabase db push`) e rode o init-db de novo.") from e
        aplicadas.append(versao)
        print(f"[init_db] Migration {os.path.basename(caminho)} aplicada.")
    return aplicadas


class _SemCommit:
    """Encaminha tudo para a conexão, exceto commit(): os passos do seed
    rodam dentro da transação (e da trava) de init_db."""

    def __init__(self, conn):
        self._conn = conn

    def commit(self):
        pass

    def __getattr__(self, nome):
        return getattr(self._conn, nome)


def init_db():
    """Cria o esquema (se faltar) e os dados de referência. Idempotente.

    Com DATABASE_URL_ADMIN definida (papel postgres; só em máquina de
    desenvolvimento/CI, nunca no deploy) usa essa conexão, que pode aplicar
    migrations. Sem ela, usa a DATABASE_URL da aplicação."""
    url_admin = os.environ.get('DATABASE_URL_ADMIN', '').strip()
    conn = conexao_direta(url_admin) if url_admin else get_connection()
    try:
        conn.execute("SELECT pg_advisory_xact_lock(?)", (_CHAVE_TRAVA_INIT,))
        aplicar_migracoes(conn)
        _semear(_SemCommit(conn))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(f"Banco de dados inicializado em: {descrever_destino()}")


def _semear(conn):
    c = conn.cursor()

    # Bootstrap do primeiro admin: só acontece se NENHUM admin existir E a senha
    # for fornecida explicitamente via SUAFACUL_ADMIN_PASSWORD (nunca há
    # credencial padrão no código). Também não promove mais "o primeiro usuário
    # cadastrado" — em um deploy novo isso daria admin a quem se registrasse
    # primeiro.
    c.execute("SELECT COUNT(*) FROM usuarios WHERE tipo='admin'")
    if c.fetchone()[0] == 0:
        senha_admin = os.environ.get('SUAFACUL_ADMIN_PASSWORD', '')
        if senha_admin:
            from werkzeug.security import generate_password_hash
            usuario_admin = os.environ.get('SUAFACUL_ADMIN_USER', '').strip() or 'admin'
            email_admin = os.environ.get('SUAFACUL_ADMIN_EMAIL', '').strip() or 'admin@suafacul.local'
            c.execute(
                "INSERT INTO usuarios (nome_usuario, email, senha, tipo) VALUES (?,?,?,?) ON CONFLICT DO NOTHING",
                (usuario_admin, email_admin, generate_password_hash(senha_admin), 'admin')
            )
            conn.commit()
            print(f"[init_db] Usuário admin '{usuario_admin}' criado a partir de SUAFACUL_ADMIN_PASSWORD.")
        else:
            print("[init_db] AVISO: nenhum usuário admin existe. Defina SUAFACUL_ADMIN_PASSWORD "
                  "(e opcionalmente SUAFACUL_ADMIN_USER/SUAFACUL_ADMIN_EMAIL) para criar o primeiro.")

    # Alerta (somente leitura, não altera nada): admin ainda com a senha padrão
    # antiga do projeto. Troque-a em Dashboard → Editar Perfil.
    from werkzeug.security import check_password_hash
    c.execute("SELECT nome_usuario, senha FROM usuarios WHERE tipo='admin'")
    for nome_admin, hash_senha in c.fetchall():
        if check_password_hash(hash_senha, 'admin123'):
            print(f"[init_db] ALERTA DE SEGURANÇA: o admin '{nome_admin}' ainda usa a senha padrão 'admin123'. Troque-a imediatamente.")

    # Seed cursos if empty
    c.execute("SELECT COUNT(*) FROM cursos")
    if c.fetchone()[0] == 0:
        cursos = [
            ('Engenharia de Software', 'UFSCAR - Universidade Federal de São Carlos', 'presencial',
             'Curso focado no desenvolvimento de sistemas complexos e aplicações de software de alta qualidade.',
             '4 anos', 'Bacharelado', 'Tecnologia', 'Pública'),
            ('Medicina', 'UNIFESP - Universidade Federal de São Paulo', 'presencial',
             'Formação de médicos generalistas com sólida base científica, técnica e humanística.',
             '6 anos', 'Bacharelado', 'Saúde', 'Pública'),
            ('Psicologia', 'PUC-SP - Pontifícia Universidade Católica de São Paulo', 'presencial',
             'Estudo do comportamento humano e processos mentais, preparando para atuação clínica e organizacional.',
             '5 anos', 'Bacharelado', 'Saúde', 'Privada'),
            ('Direito', 'USP - Universidade de São Paulo', 'presencial',
             'Desenvolve o raciocínio jurídico para atuação em diversas áreas do direito.',
             '5 anos', 'Bacharelado', 'Direito', 'Pública'),
            ('Administração', 'UFBA - Universidade Federal da Bahia', 'presencial',
             'Prepara líderes e gestores para os desafios do mercado corporativo.',
             '4 anos', 'Bacharelado', 'Negócios', 'Pública'),
            ('Ciência da Computação', 'UFMG - Universidade Federal de Minas Gerais', 'presencial',
             'Estudo aprofundado de algoritmos, estruturas de dados e inteligência artificial.',
             '4 anos', 'Bacharelado', 'Tecnologia', 'Pública'),
            ('Nutrição', 'UNIFESP - Universidade Federal de São Paulo', 'semipresencial',
             'Foca na relação entre alimentação, saúde e qualidade de vida.',
             '4 anos', 'Bacharelado', 'Saúde', 'Pública'),
            ('Engenharia Civil', 'USP - Universidade de São Paulo', 'presencial',
             'Projetos e construção de infraestruturas como edifícios, pontes e estradas.',
             '5 anos', 'Bacharelado', 'Engenharias', 'Pública'),
            ('Jornalismo', 'PUC-SP - Pontifícia Universidade Católica de São Paulo', 'presencial',
             'Forma comunicadores para produzir e disseminar informações em diversas plataformas.',
             '4 anos', 'Bacharelado', 'Comunicação', 'Privada'),
            ('Arquitetura e Urbanismo', 'UFF - Universidade Federal Fluminense', 'presencial',
             'Planejamento e concepção de espaços urbanos e edificações.',
             '5 anos', 'Bacharelado', 'Artes e Design', 'Pública'),
            ('Análise e Desenvolvimento de Sistemas', 'FATEC - Faculdade de Tecnologia do Estado de São Paulo', 'presencial',
             'Curso tecnólogo focado em desenvolvimento de software, banco de dados, engenharia de sistemas e metodologias ágeis para o mercado de trabalho.',
             '3 anos', 'Tecnólogo', 'Tecnologia', 'Pública'),
        ]
        c.executemany(
            "INSERT INTO cursos (nome, instituicao, modalidade, descricao, duracao, grau, area, tipo_instituicao) VALUES (?,?,?,?,?,?,?,?)",
            cursos
        )

    # ── Migração: garante que cursos reais adicionados depois do seed
    # inicial existam também em bancos já populados (sem duplicar se já existir).
    c.execute("SELECT COUNT(*) FROM cursos WHERE nome=? AND instituicao=?",
              ('Análise e Desenvolvimento de Sistemas', 'FATEC - Faculdade de Tecnologia do Estado de São Paulo'))
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO cursos (nome, instituicao, modalidade, descricao, duracao, grau, area, tipo_instituicao) VALUES (?,?,?,?,?,?,?,?)",
            ('Análise e Desenvolvimento de Sistemas', 'FATEC - Faculdade de Tecnologia do Estado de São Paulo', 'presencial',
             'Curso tecnólogo focado em desenvolvimento de software, banco de dados, engenharia de sistemas e metodologias ágeis para o mercado de trabalho.',
             '3 anos', 'Tecnólogo', 'Tecnologia', 'Pública')
        )
        conn.commit()
        # Linka à faculdade FATEC se ela já existir cadastrada
        c.execute("SELECT id FROM faculdades WHERE nome=?", ('FATEC - Faculdade de Tecnologia do Estado de São Paulo',))
        fatec = c.fetchone()
        if fatec:
            c.execute(
                "UPDATE cursos SET faculdade_id=? WHERE nome=? AND instituicao=? AND faculdade_id IS NULL",
                (fatec[0], 'Análise e Desenvolvimento de Sistemas', 'FATEC - Faculdade de Tecnologia do Estado de São Paulo')
            )
            conn.commit()

    # Seed faculdades if empty — instituições reais já referenciadas em
    # cursos/vestibulares (fonte: conhecimento público sobre as próprias
    # universidades). Endereço/cidade/UF/site são dados públicos estáveis;
    # telefone/e-mail ficam em branco pois o e-MEC não os disponibiliza e
    # não devem ser inventados — completáveis depois via admin ou import e-MEC.
    c.execute("SELECT COUNT(*) FROM faculdades")
    if c.fetchone()[0] == 0:
        faculdades = [
            # nome, sigla, organizacao_academica, tipo_instituicao, url, endereco, cidade, uf
            ('USP - Universidade de São Paulo', 'USP', 'Universidade', 'Pública',
             'https://www5.usp.br', 'Rua da Reitoria, 374 - Cidade Universitária', 'São Paulo', 'SP'),
            ('UNICAMP - Universidade Estadual de Campinas', 'UNICAMP', 'Universidade', 'Pública',
             'https://www.unicamp.br', 'Cidade Universitária Zeferino Vaz', 'Campinas', 'SP'),
            ('UNESP - Universidade Estadual Paulista', 'UNESP', 'Universidade', 'Pública',
             'https://www2.unesp.br', 'Rua Quirino de Andrade, 215', 'São Paulo', 'SP'),
            ('UNIFESP - Universidade Federal de São Paulo', 'UNIFESP', 'Universidade', 'Pública',
             'https://www.unifesp.br', 'Rua Sena Madureira, 1500', 'São Paulo', 'SP'),
            ('PUC-SP - Pontifícia Universidade Católica de São Paulo', 'PUC-SP', 'Universidade', 'Privada',
             'https://www.pucsp.br', 'Rua Ministro Godói, 969', 'São Paulo', 'SP'),
            ('UFBA - Universidade Federal da Bahia', 'UFBA', 'Universidade', 'Pública',
             'https://www.ufba.br', 'Rua Barão de Jeremoabo, s/n - Ondina', 'Salvador', 'BA'),
            ('UFMG - Universidade Federal de Minas Gerais', 'UFMG', 'Universidade', 'Pública',
             'https://www.ufmg.br', 'Av. Antônio Carlos, 6627 - Pampulha', 'Belo Horizonte', 'MG'),
            ('UFF - Universidade Federal Fluminense', 'UFF', 'Universidade', 'Pública',
             'https://www.uff.br', 'Rua Miguel de Frias, 9 - Icaraí', 'Niterói', 'RJ'),
            ('UFSCAR - Universidade Federal de São Carlos', 'UFSCar', 'Universidade', 'Pública',
             'https://www.ufscar.br', 'Rod. Washington Luís, km 235', 'São Carlos', 'SP'),
            ('UFRJ - Universidade Federal do Rio de Janeiro', 'UFRJ', 'Universidade', 'Pública',
             'https://ufrj.br', 'Av. Pedro Calmon, 550 - Cidade Universitária', 'Rio de Janeiro', 'RJ'),
            ('UFSC - Universidade Federal de Santa Catarina', 'UFSC', 'Universidade', 'Pública',
             'https://ufsc.br', 'Campus Universitário Reitor João David Ferreira Lima - Trindade', 'Florianópolis', 'SC'),
            ('UFRGS - Universidade Federal do Rio Grande do Sul', 'UFRGS', 'Universidade', 'Pública',
             'https://www.ufrgs.br', 'Av. Paulo Gama, 110 - Farroupilha', 'Porto Alegre', 'RS'),
            ('UnB - Universidade de Brasília', 'UnB', 'Universidade', 'Pública',
             'https://www.unb.br', 'Campus Universitário Darcy Ribeiro', 'Brasília', 'DF'),
            ('FATEC - Faculdade de Tecnologia do Estado de São Paulo', 'FATEC', 'Centro Universitário', 'Pública',
             'https://www.cps.sp.gov.br/fatec', 'Rua dos Andradas, 140', 'São Paulo', 'SP'),
        ]
        for nome, sigla, org, tipo, url, endereco, cidade, uf in faculdades:
            c.execute(
                """INSERT INTO faculdades
                   (nome, sigla, organizacao_academica, tipo_instituicao, url, endereco, cidade, uf, situacao, fonte)
                   VALUES (?,?,?,?,?,?,?,?, 'ativa', 'manual')""",
                (nome, sigla, org, tipo, url, endereco, cidade, uf)
            )
        conn.commit()

        # Vincula cursos e vestibulares já semeados às faculdades recém-criadas,
        # casando pelo texto de instituição já usado nas outras tabelas.
        c.execute("SELECT id, nome FROM faculdades")
        mapa_faculdades = {nome: id for id, nome in c.fetchall()}
        c.execute("SELECT id, instituicao FROM cursos WHERE faculdade_id IS NULL")
        for curso_id, instituicao in c.fetchall():
            if instituicao in mapa_faculdades:
                c.execute("UPDATE cursos SET faculdade_id=? WHERE id=?", (mapa_faculdades[instituicao], curso_id))
        conn.commit()

    # Vestibulares: catálogo pesquisado em fontes oficiais (ver
    # database/vestibulares_dados.py). Insere os que faltam e atualiza os
    # registros semeados em versões anteriores — sem duplicar e sem apagar
    # nada (IDs e favoritos são preservados).
    sincronizar_vestibulares(conn)

    # Catálogo ampliado de cursos e instituições (database/catalogo_dados.py).
    sincronizar_catalogo(conn)

    conn.commit()

    # ── Migração: o tipo de instituição do curso segue o da faculdade a que
    # ele está vinculado. Corrige bancos semeados com a lista antiga, que
    # marcava como "Privada" cursos da USP, UFBA, UFF e UNIFESP.
    c.execute("""
        UPDATE cursos
           SET tipo_instituicao = (SELECT f.tipo_instituicao FROM faculdades f WHERE f.id = cursos.faculdade_id)
         WHERE faculdade_id IS NOT NULL
           AND tipo_instituicao <> (SELECT f.tipo_instituicao FROM faculdades f WHERE f.id = cursos.faculdade_id)
    """)
    if c.rowcount:
        print(f"[init_db] Tipo de instituição corrigido em {c.rowcount} curso(s).")
    conn.commit()



_CAMPOS_VESTIBULAR = ('nome', 'instituicao', 'tipo_instituicao', 'cidade', 'regiao',
                      'periodo_inscricao', 'data_prova', 'descricao', 'link_edital',
                      'taxa_inscricao', 'cursos_oferecidos', 'requisitos', 'fonte')


def sincronizar_vestibulares(conn):
    """Garante que todos os vestibulares do catálogo existam no banco.

    - Procura cada item pelo nome atual ou por um dos `nomes_anteriores`
      (comparação sem diferenciar maiúsculas) para nunca duplicar.
    - Se não existe: insere.
    - Se existe e foi gerado por uma versão anterior do catálogo
      (seed_versao < SEED_VERSAO): atualiza os campos e reabre a validação.
      Registros já na versão atual não são tocados, então edições feitas
      depois não são sobrescritas a cada inicialização.
    - Vincula à faculdade cadastrada com o mesmo nome de instituição.
    Retorna {'inseridos': n, 'atualizados': n}.
    """
    from database.vestibulares_dados import VESTIBULARES, SEED_VERSAO

    c = conn.cursor()
    inseridos = atualizados = 0
    for item in VESTIBULARES:
        nomes = [item['nome']] + list(item.get('nomes_anteriores', []))
        row = None
        for nome in nomes:
            c.execute("SELECT id, seed_versao FROM vestibulares WHERE lower(nome)=lower(?) ORDER BY id LIMIT 1", (nome,))
            row = c.fetchone()
            if row:
                break
        valores = [item.get(campo) for campo in _CAMPOS_VESTIBULAR]
        if row is None:
            c.execute(
                f"INSERT INTO vestibulares ({', '.join(_CAMPOS_VESTIBULAR)}, seed_versao) "
                f"VALUES ({', '.join('?' * len(_CAMPOS_VESTIBULAR))}, ?)",
                valores + [SEED_VERSAO]
            )
            inseridos += 1
        elif (row[1] or 0) < SEED_VERSAO:
            c.execute(
                f"UPDATE vestibulares SET {', '.join(f'{campo}=?' for campo in _CAMPOS_VESTIBULAR)}, "
                "seed_versao=?, status_validacao='nao_validado', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                valores + [SEED_VERSAO, row[0]]
            )
            atualizados += 1

    c.execute("SELECT id, nome FROM faculdades")
    mapa_faculdades = {nome: id for id, nome in c.fetchall()}
    c.execute("SELECT id, instituicao FROM vestibulares WHERE faculdade_id IS NULL")
    for vest_id, instituicao in c.fetchall():
        if instituicao in mapa_faculdades:
            c.execute("UPDATE vestibulares SET faculdade_id=? WHERE id=?", (mapa_faculdades[instituicao], vest_id))
    conn.commit()
    return {'inseridos': inseridos, 'atualizados': atualizados}


def _norm(texto):
    from config.database import normalizar
    return ' '.join((normalizar(texto or '') or '').split())


def _localizar_faculdade(c, sigla, dados):
    """Faculdade já cadastrada que corresponde à sigla do catálogo: mesma
    sigla e UF, ou mesmo nome (sem acento/caixa) — com ou sem o prefixo
    'SIGLA - ' usado pelo seed manual (registros do e-MEC vêm sem ele)."""
    nome, _org, _tipo, _url, _end, _cidade, uf = dados
    c.execute("SELECT id, nome, tipo_instituicao FROM faculdades "
              "WHERE UPPER(TRIM(sigla)) = UPPER(?) AND UPPER(TRIM(COALESCE(uf, ''))) = ? ORDER BY id LIMIT 1",
              (sigla, uf.upper()))
    row = c.fetchone()
    if row:
        return row
    nomes = {_norm(nome), _norm(nome.split(' - ', 1)[-1])}
    c.execute(f"SELECT id, nome, tipo_instituicao FROM faculdades WHERE {sql_norm('nome')} IN (?, ?) ORDER BY id LIMIT 1",
              tuple(nomes) if len(nomes) == 2 else (next(iter(nomes)),) * 2)
    return c.fetchone()


def sincronizar_catalogo(conn):
    """Garante o catálogo ampliado de cursos e instituições (ver
    database/catalogo_dados.py), sem duplicar e sem apagar nada:

    - cursos_catalogo: insere a formação que falta; atualiza a que veio de
      uma versão anterior do catálogo (seed_versao < CATALOGO_VERSAO).
    - faculdades: todas as de INSTITUICOES; reaproveita a já cadastrada (manual ou e-MEC);
      insere só as que não existem.
    - cursos: insere a oferta (curso + instituição) que ainda não existe —
      mesmo nome de curso (sem acento/caixa) na mesma faculdade.

    Quando o catálogo da versão atual já foi aplicado, não faz nada: assim
    o init (que roda a cada inicialização, inclusive na Vercel) fica leve e
    o que o admin excluir depois não volta sozinho.
    Retorna {'catalogo': n, 'faculdades': n, 'cursos': n} (itens inseridos)."""
    from config.database import normalizar
    from database.catalogo_dados import CATALOGO_VERSAO, CURSOS, INSTITUICOES, NOMES_ANTIGOS

    c = conn.cursor()
    resumo = {'catalogo': 0, 'faculdades': 0, 'cursos': 0}

    c.execute("SELECT COUNT(*) FROM cursos_catalogo WHERE seed_versao >= ?", (CATALOGO_VERSAO,))
    if c.fetchone()[0] >= len(CURSOS):
        return resumo

    # 1) Formações do catálogo
    for ordem, curso in enumerate(CURSOS):
        valores = (curso['area'], curso['grau'], curso['duracao'], curso['descricao'], curso['imagem'], ordem)
        c.execute("SELECT id, seed_versao FROM cursos_catalogo WHERE nome = ?", (curso['nome'],))
        row = c.fetchone()
        if row is None:
            c.execute("INSERT INTO cursos_catalogo (area, grau, duracao, descricao, imagem_url, ordem, nome, seed_versao) "
                      "VALUES (?,?,?,?,?,?,?,?)", valores + (curso['nome'], CATALOGO_VERSAO))
            resumo['catalogo'] += 1
        elif (row[1] or 0) < CATALOGO_VERSAO:
            c.execute("UPDATE cursos_catalogo SET area=?, grau=?, duracao=?, descricao=?, imagem_url=?, ordem=?, "
                      "seed_versao=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                      valores + (CATALOGO_VERSAO, row[0]))

    # 2) Instituições do catálogo — todas, mesmo as que ainda não têm
    #    oferta de curso (aparecem na busca/listagem de faculdades).
    faculdades = {}
    for sigla in INSTITUICOES:
        dados = INSTITUICOES[sigla]
        row = _localizar_faculdade(c, sigla, dados)
        if row is None:
            nome, org, tipo, url, endereco, cidade, uf = dados
            novo_id = inserir(c, """INSERT INTO faculdades
                         (nome, sigla, organizacao_academica, tipo_instituicao, url, endereco, cidade, uf, situacao, fonte)
                         VALUES (?,?,?,?,?,?,?,?, 'ativa', 'manual')""",
                              (nome, sigla, org, tipo, url, endereco, cidade, uf))
            row = (novo_id, nome, tipo)
            resumo['faculdades'] += 1
        else:
            # Já cadastrada: completa só o que está vazio (não sobrescreve o
            # que o admin editou) e aplica renomeações oficiais conhecidas.
            nome, org, _tipo, _url, endereco, _cidade, _uf = dados
            c.execute("UPDATE faculdades SET endereco = ?, updated_at = CURRENT_TIMESTAMP "
                      "WHERE id = ? AND COALESCE(TRIM(endereco), '') = '' AND CAST(? AS TEXT) IS NOT NULL",
                      (endereco, row[0], endereco))
            c.execute("UPDATE faculdades SET organizacao_academica = ? "
                      "WHERE id = ? AND COALESCE(TRIM(organizacao_academica), '') = '' AND CAST(? AS TEXT) IS NOT NULL",
                      (org, row[0], org))
            if row[1] in NOMES_ANTIGOS and NOMES_ANTIGOS[row[1]] == nome:
                c.execute("UPDATE faculdades SET nome = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                          (nome, row[0]))
                row = (row[0], nome, row[2])
        faculdades[sigla] = row

    # 3) Ofertas (uma linha em cursos por curso em cada instituição).
    #    Carrega as ofertas existentes de uma vez (são milhares no catálogo).
    c.execute("SELECT nome, faculdade_id, instituicao FROM cursos")
    existentes_id, existentes_inst = set(), set()
    novas_ofertas = []
    for nome_c, fac_c, inst_c in c.fetchall():
        nn = _norm(nome_c)
        if fac_c is not None:
            existentes_id.add((nn, fac_c))
        existentes_inst.add((nn, inst_c))
    for curso in CURSOS:
        nome_norm = _norm(curso['nome'])
        for oferta in curso['ofertas']:
            sigla, modalidade = oferta[0], oferta[1]
            grau = oferta[2] if len(oferta) > 2 else curso['grau']
            fac_id, fac_nome, fac_tipo = faculdades[sigla]
            if (nome_norm, fac_id) in existentes_id or (nome_norm, fac_nome) in existentes_inst:
                continue
            existentes_id.add((nome_norm, fac_id))
            novas_ofertas.append((curso['nome'], fac_nome, fac_id, modalidade, curso['descricao'], curso['duracao'],
                                  grau, curso['area'], fac_tipo))
    if novas_ofertas:
        # Em lote: o psycopg envia tudo em pipeline (milhares de linhas, uma ida ao banco).
        c.executemany("""INSERT INTO cursos (nome, instituicao, faculdade_id, modalidade, descricao, duracao,
                                             grau, area, tipo_instituicao)
                         VALUES (?,?,?,?,?,?,?,?,?)""", novas_ofertas)
        resumo['cursos'] = len(novas_ofertas)

    conn.commit()
    if any(resumo.values()):
        print(f"[init_db] Catálogo v{CATALOGO_VERSAO}: {resumo['catalogo']} formação(ões), "
              f"{resumo['faculdades']} instituição(ões) e {resumo['cursos']} oferta(s) de curso inseridas.")
    return resumo


if __name__ == '__main__':
    init_db()
