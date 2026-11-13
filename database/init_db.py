"""Initialize SQLite database with tables and seed data."""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.database import get_db_path, get_connection

def init_db():
    """Cria tabelas e dados iniciais. Serializado por uma trava de arquivo:
    quando vários processos sobem juntos com o banco ainda vazio (vários
    workers do gunicorn, instâncias concorrentes na Vercel), o padrão
    "conferir e depois inserir" do seed abaixo fazia dois processos
    criarem o admin padrão ao mesmo tempo — um deles quebrava com
    "UNIQUE constraint failed: usuarios.email" e o worker não subia.
    Com a trava, o segundo processo espera e encontra o seed já feito."""
    caminho_db = get_db_path()
    os.makedirs(os.path.dirname(caminho_db), exist_ok=True)
    try:
        import fcntl  # Linux/macOS (Vercel, gunicorn)
    except ImportError:  # Windows: sem fcntl; dev local roda 1 processo só
        return _init_db_sem_trava()
    with open(caminho_db + '.init.lock', 'w') as trava:
        fcntl.flock(trava, fcntl.LOCK_EX)
        try:
            return _init_db_sem_trava()
        finally:
            fcntl.flock(trava, fcntl.LOCK_UN)


def _init_db_sem_trava():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_usuario TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        senha TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'aluno' CHECK(tipo IN ('aluno','admin')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS faculdades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_emec TEXT UNIQUE,
        nome TEXT NOT NULL,
        sigla TEXT,
        organizacao_academica TEXT,
        tipo_instituicao TEXT NOT NULL DEFAULT 'Pública' CHECK(tipo_instituicao IN ('Pública','Privada')),
        url TEXT,
        endereco TEXT,
        cidade TEXT,
        uf TEXT,
        telefone TEXT,
        email TEXT,
        situacao TEXT DEFAULT 'ativa',
        fonte TEXT DEFAULT 'manual',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS cursos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        instituicao TEXT NOT NULL DEFAULT 'Instituição não informada',
        faculdade_id INTEGER,
        modalidade TEXT NOT NULL DEFAULT 'presencial',
        descricao TEXT,
        duracao TEXT,
        grau TEXT,
        area TEXT,
        tipo_instituicao TEXT NOT NULL DEFAULT 'Pública',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (faculdade_id) REFERENCES faculdades(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS vestibulares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        instituicao TEXT,
        faculdade_id INTEGER,
        tipo_instituicao TEXT NOT NULL DEFAULT 'Pública',
        cidade TEXT,
        regiao TEXT,
        periodo_inscricao TEXT,
        data_prova TEXT,
        descricao TEXT,
        link_edital TEXT,
        taxa_inscricao TEXT,
        cursos_oferecidos TEXT,
        requisitos TEXT,
        fonte TEXT,
        seed_versao INTEGER DEFAULT 0,
        status_validacao TEXT DEFAULT 'nao_validado',
        cadastrado_ok INTEGER DEFAULT 0,
        ultima_validacao TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (faculdade_id) REFERENCES faculdades(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS vestibular_inscricoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        vestibular_id INTEGER NOT NULL,
        resultado TEXT NOT NULL DEFAULT 'pendente' CHECK(resultado IN ('pendente','aprovado','reprovado','lista_espera')),
        observacao TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(usuario_id, vestibular_id),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        FOREIGN KEY (vestibular_id) REFERENCES vestibulares(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS teste_vocacional_resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NULL,
        perfil_principal TEXT NOT NULL,
        perfis_json TEXT NOT NULL,
        respostas_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    );

    CREATE TABLE IF NOT EXISTS favoritos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('curso','vestibular','faculdade')),
        item_id INTEGER NOT NULL,
        nome_item TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(usuario_id, tipo, item_id),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
    );
    """)

    # ── Migração segura para bancos já existentes (não apaga dados) ──
    def _add_column_if_missing(table, column, ddl):
        c.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in c.fetchall()]
        if column not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    _add_column_if_missing('usuarios', 'tipo', "tipo TEXT NOT NULL DEFAULT 'aluno'")
    _add_column_if_missing('cursos', 'faculdade_id', "faculdade_id INTEGER")
    _add_column_if_missing('vestibulares', 'faculdade_id', "faculdade_id INTEGER")
    _add_column_if_missing('vestibulares', 'status_validacao', "status_validacao TEXT DEFAULT 'nao_validado'")
    _add_column_if_missing('vestibulares', 'cadastrado_ok', "cadastrado_ok INTEGER DEFAULT 0")
    _add_column_if_missing('vestibulares', 'ultima_validacao', "ultima_validacao TIMESTAMP")
    # Detalhes do processo seletivo (taxa, cursos, requisitos e fonte da informação)
    _add_column_if_missing('vestibulares', 'taxa_inscricao', "taxa_inscricao TEXT")
    _add_column_if_missing('vestibulares', 'cursos_oferecidos', "cursos_oferecidos TEXT")
    _add_column_if_missing('vestibulares', 'requisitos', "requisitos TEXT")
    _add_column_if_missing('vestibulares', 'fonte', "fonte TEXT")
    # Versão do catálogo que gerou/atualizou o registro (0 = cadastrado pelo admin)
    _add_column_if_missing('vestibulares', 'seed_versao', "seed_versao INTEGER DEFAULT 0")
    c.execute("CREATE INDEX IF NOT EXISTS idx_vestibulares_nome ON vestibulares(nome COLLATE NOCASE)")

    # ── Importação de cursos via Censo da Educação Superior (INEP) ──
    _add_column_if_missing('cursos', 'codigo_inep_curso', "codigo_inep_curso TEXT")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cursos_codigo_inep ON cursos(codigo_inep_curso) WHERE codigo_inep_curso IS NOT NULL")

    # ── Autocomplete de nomes de curso (busca por prefixo) ──
    c.execute("CREATE INDEX IF NOT EXISTS idx_cursos_nome ON cursos(nome COLLATE NOCASE)")

    # ── Login com Google (OIDC) ──
    # google_id fica NULL para contas locais; auth_provider indica a origem.
    # senha continua NOT NULL na tabela (não alteramos a constraint em SQLite
    # para não exigir reconstrução da tabela) — contas criadas via Google
    # recebem um hash aleatório inutilizável em vez de senha real.
    _add_column_if_missing('usuarios', 'google_id', "google_id TEXT")
    _add_column_if_missing('usuarios', 'auth_provider', "auth_provider TEXT NOT NULL DEFAULT 'local'")
    _add_column_if_missing('usuarios', 'avatar_url', "avatar_url TEXT")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_google_id ON usuarios(google_id) WHERE google_id IS NOT NULL")

    # ── Logs da automação diária (vestibulares, importação e-MEC, etc.) ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS automacao_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL,
        executado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sucesso INTEGER NOT NULL DEFAULT 1,
        resumo TEXT,
        erro TEXT
    )
    """)
    # ── Execuções de automações (Cron/CLI): identificação, estado e trava ──
    # status: executando | sucesso | falha | ignorada. O índice único parcial abaixo
    # garante NO MÁXIMO uma execução 'executando' por tipo (trava contra execução
    # concorrente/duplicada, sem precisar de Redis).
    for coluna, ddl in (('execucao_id', 'execucao_id TEXT'), ('status', 'status TEXT'),
                        ('origem', 'origem TEXT'), ('iniciado_em', 'iniciado_em TIMESTAMP'),
                        ('finalizado_em', 'finalizado_em TIMESTAMP'), ('duracao_ms', 'duracao_ms INTEGER')):
        _add_column_if_missing('automacao_logs', coluna, ddl)
    c.execute("UPDATE automacao_logs SET status = CASE WHEN sucesso=1 THEN 'sucesso' ELSE 'falha' END "
              "WHERE status IS NULL")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_automacao_em_execucao ON automacao_logs(tipo) "
              "WHERE status='executando'")
    c.execute("CREATE INDEX IF NOT EXISTS idx_automacao_tipo_status ON automacao_logs(tipo, status, finalizado_em)")

    # ── Refresh tokens da API v1 (Mobile) ──
    # Uma "família" = uma sessão de dispositivo. Cada uso do refresh token gera
    # outro da mesma família (rotação); reapresentar um já usado revoga a
    # família inteira. Só o hash SHA-256 do token é guardado — nunca o token.
    c.execute("""
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        familia_id TEXT NOT NULL,
        usuario_id INTEGER NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        dispositivo TEXT,
        expira_em TIMESTAMP NOT NULL,
        usado_em TIMESTAMP,
        revogado_em TIMESTAMP,
        motivo_revogacao TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_familia ON refresh_tokens(familia_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_usuario ON refresh_tokens(usuario_id)")

    # ── Catálogo de cursos da página inicial (um registro por formação) ──
    # Guarda o que não muda de instituição para instituição: área, grau e
    # duração típicos, descrição e a imagem do card. As ofertas continuam
    # na tabela cursos (uma linha por curso em cada instituição).
    c.execute("""
    CREATE TABLE IF NOT EXISTS cursos_catalogo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
        area TEXT,
        grau TEXT,
        duracao TEXT,
        descricao TEXT,
        imagem_url TEXT,
        ordem INTEGER DEFAULT 0,
        seed_versao INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_cursos_faculdade ON cursos(faculdade_id)")
    conn.commit()

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
    # nada (IDs, favoritos e inscrições são preservados).
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

    conn.commit()
    conn.close()
    print(f"Banco de dados inicializado em: {get_db_path()}")

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
    c.execute("SELECT id, nome, tipo_instituicao FROM faculdades WHERE normalizar(nome) IN (?, ?) ORDER BY id LIMIT 1",
              tuple(nomes) if len(nomes) == 2 else (next(iter(nomes)),) * 2)
    return c.fetchone()


def sincronizar_catalogo(conn):
    """Garante o catálogo ampliado de cursos e instituições (ver
    database/catalogo_dados.py), sem duplicar e sem apagar nada:

    - cursos_catalogo: insere a formação que falta; atualiza a que veio de
      uma versão anterior do catálogo (seed_versao < CATALOGO_VERSAO).
    - faculdades: reaproveita a instituição já cadastrada (manual ou e-MEC);
      insere só as que não existem.
    - cursos: insere a oferta (curso + instituição) que ainda não existe —
      mesmo nome de curso (sem acento/caixa) na mesma faculdade.

    Quando o catálogo da versão atual já foi aplicado, não faz nada: assim
    o init (que roda a cada inicialização, inclusive na Vercel) fica leve e
    o que o admin excluir depois não volta sozinho.
    Retorna {'catalogo': n, 'faculdades': n, 'cursos': n} (itens inseridos)."""
    from config.database import normalizar
    from database.catalogo_dados import CATALOGO_VERSAO, CURSOS, INSTITUICOES

    conn.create_function('normalizar', 1, normalizar, deterministic=True)
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

    # 2) Instituições usadas nas ofertas
    faculdades = {}
    siglas_usadas = {oferta[0] for curso in CURSOS for oferta in curso['ofertas']}
    for sigla in sorted(siglas_usadas):
        dados = INSTITUICOES[sigla]
        row = _localizar_faculdade(c, sigla, dados)
        if row is None:
            nome, org, tipo, url, endereco, cidade, uf = dados
            c.execute("""INSERT INTO faculdades
                         (nome, sigla, organizacao_academica, tipo_instituicao, url, endereco, cidade, uf, situacao, fonte)
                         VALUES (?,?,?,?,?,?,?,?, 'ativa', 'manual')""",
                      (nome, sigla, org, tipo, url, endereco, cidade, uf))
            row = (c.lastrowid, nome, tipo)
            resumo['faculdades'] += 1
        faculdades[sigla] = row

    # 3) Ofertas (uma linha em cursos por curso em cada instituição)
    for curso in CURSOS:
        nome_norm = _norm(curso['nome'])
        for oferta in curso['ofertas']:
            sigla, modalidade = oferta[0], oferta[1]
            grau = oferta[2] if len(oferta) > 2 else curso['grau']
            fac_id, fac_nome, fac_tipo = faculdades[sigla]
            c.execute("SELECT 1 FROM cursos WHERE normalizar(nome) = ? AND (faculdade_id = ? OR instituicao = ?) LIMIT 1",
                      (nome_norm, fac_id, fac_nome))
            if c.fetchone():
                continue
            c.execute("""INSERT INTO cursos (nome, instituicao, faculdade_id, modalidade, descricao, duracao,
                                             grau, area, tipo_instituicao)
                         VALUES (?,?,?,?,?,?,?,?,?)""",
                      (curso['nome'], fac_nome, fac_id, modalidade, curso['descricao'], curso['duracao'],
                       grau, curso['area'], fac_tipo))
            resumo['cursos'] += 1

    conn.commit()
    if any(resumo.values()):
        print(f"[init_db] Catálogo v{CATALOGO_VERSAO}: {resumo['catalogo']} formação(ões), "
              f"{resumo['faculdades']} instituição(ões) e {resumo['cursos']} oferta(s) de curso inseridas.")
    return resumo


if __name__ == '__main__':
    init_db()
