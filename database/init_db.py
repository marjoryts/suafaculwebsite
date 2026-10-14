"""Initialize SQLite database with tables and seed data."""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.database import get_db_path, get_connection

def _senha_admin_inicial():
    """Senha do admin criado automaticamente quando o banco não tem nenhum.

    - SUAFACUL_ADMIN_PASSWORD definida: usa essa senha (qualquer ambiente).
    - Na Vercel sem a variável: senha aleatória. Lá o banco fica em /tmp e
      é recriado a cada inicialização, então uma senha padrão conhecida
      voltaria sempre, mesmo que alguém a tivesse trocado pelo painel.
    - Desenvolvimento local sem a variável: mantém admin123 (README/testes).
    """
    senha = os.environ.get('SUAFACUL_ADMIN_PASSWORD', '').strip()
    if senha:
        return senha, 'env'
    if os.environ.get('VERCEL'):
        import secrets
        return secrets.token_urlsafe(24), 'aleatoria'
    return 'admin123', 'padrao'


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
    conn.commit()

    # Garante que exista pelo menos um usuário admin.
    # Se nenhum admin existir, promove o primeiro usuário cadastrado;
    # se não houver nenhum usuário, cria um admin padrão (senha deve ser trocada).
    c.execute("SELECT COUNT(*) FROM usuarios WHERE tipo='admin'")
    if c.fetchone()[0] == 0:
        c.execute("SELECT id FROM usuarios ORDER BY id LIMIT 1")
        primeiro = c.fetchone()
        if primeiro:
            c.execute("UPDATE usuarios SET tipo='admin' WHERE id=?", (primeiro[0],))
            print(f"[init_db] Usuário id={primeiro[0]} promovido a admin (nenhum admin existia).")
        else:
            from werkzeug.security import generate_password_hash
            senha_admin, origem = _senha_admin_inicial()
            c.execute(
                "INSERT INTO usuarios (nome_usuario, email, senha, tipo) VALUES (?,?,?,?)",
                ('admin', 'admin@suafacul.local', generate_password_hash(senha_admin), 'admin')
            )
            if origem == 'env':
                print("[init_db] Usuário admin criado com a senha de SUAFACUL_ADMIN_PASSWORD.")
            elif origem == 'aleatoria':
                print("[init_db] AVISO: SUAFACUL_ADMIN_PASSWORD não está definida neste ambiente. "
                      "O admin foi criado com uma senha aleatória (não há senha padrão em produção). "
                      "Defina a variável nas configurações do projeto na Vercel para conseguir entrar.")
            else:
                print("[init_db] Usuário admin padrão criado -> login: admin / senha: admin123 "
                      "(somente desenvolvimento local; em produção use SUAFACUL_ADMIN_PASSWORD).")
        conn.commit()

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


if __name__ == '__main__':
    init_db()
