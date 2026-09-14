"""Initialize SQLite database with tables and seed data."""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config.database import DB_PATH, get_connection

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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
    _add_column_if_missing('usuarios', 'google_id', "google_id TEXT")
    _add_column_if_missing('usuarios', 'foto_url', "foto_url TEXT")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_google_id ON usuarios(google_id) WHERE google_id IS NOT NULL")
    _add_column_if_missing('cursos', 'faculdade_id', "faculdade_id INTEGER")
    _add_column_if_missing('vestibulares', 'faculdade_id', "faculdade_id INTEGER")
    _add_column_if_missing('vestibulares', 'status_validacao', "status_validacao TEXT DEFAULT 'nao_validado'")
    _add_column_if_missing('vestibulares', 'cadastrado_ok', "cadastrado_ok INTEGER DEFAULT 0")
    _add_column_if_missing('vestibulares', 'ultima_validacao', "ultima_validacao TIMESTAMP")
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
            c.execute(
                "INSERT INTO usuarios (nome_usuario, email, senha, tipo) VALUES (?,?,?,?)",
                ('admin', 'admin@suafacul.local', generate_password_hash('admin123'), 'admin')
            )
            print("[init_db] Usuário admin padrão criado -> login: admin / senha: admin123 (TROQUE a senha).")
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
             '5 anos', 'Bacharelado', 'Direito', 'Privada'),
            ('Administração', 'UFBA - Universidade Federal da Bahia', 'presencial',
             'Prepara líderes e gestores para os desafios do mercado corporativo.',
             '4 anos', 'Bacharelado', 'Negócios', 'Privada'),
            ('Ciência da Computação', 'UFMG - Universidade Federal de Minas Gerais', 'presencial',
             'Estudo aprofundado de algoritmos, estruturas de dados e inteligência artificial.',
             '4 anos', 'Bacharelado', 'Tecnologia', 'Pública'),
            ('Nutrição', 'UNIFESP - Universidade Federal de São Paulo', 'semipresencial',
             'Foca na relação entre alimentação, saúde e qualidade de vida.',
             '4 anos', 'Bacharelado', 'Saúde', 'Privada'),
            ('Engenharia Civil', 'USP - Universidade de São Paulo', 'presencial',
             'Projetos e construção de infraestruturas como edifícios, pontes e estradas.',
             '5 anos', 'Bacharelado', 'Engenharias', 'Pública'),
            ('Jornalismo', 'PUC-SP - Pontifícia Universidade Católica de São Paulo', 'presencial',
             'Forma comunicadores para produzir e disseminar informações em diversas plataformas.',
             '4 anos', 'Bacharelado', 'Comunicação', 'Privada'),
            ('Arquitetura e Urbanismo', 'UFF - Universidade Federal Fluminense', 'presencial',
             'Planejamento e concepção de espaços urbanos e edificações.',
             '5 anos', 'Bacharelado', 'Artes e Design', 'Privada'),
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

    # Seed vestibulares if empty — datas reais e atuais (pesquisadas em
    # fontes oficiais/jornalísticas em 22/08/2026). UFMG, UFRJ e UFBA não
    # possuem mais vestibular tradicional próprio (ingresso majoritariamente
    # via SISU/ENEM); UFMG passou a ter o "Seriado" (30% das vagas) a partir
    # de 2025 e por isso está representada por ele aqui.
    c.execute("SELECT COUNT(*) FROM vestibulares")
    if c.fetchone()[0] == 0:
        vestibulares = [
            ('Fuvest 2027', 'USP - Universidade de São Paulo', 'Pública', 'São Paulo', 'Sudeste',
             '17/08 a 09/10/2026', '2026-11-01',
             'Vestibular da Fuvest para ingresso na USP em 2027. 1ª fase em 01/11/2026; 2ª fase em 06 e 07/12/2026.',
             'https://www.fuvest.br/vestibular-da-usp'),
            ('Enem 2026', 'INEP', 'Pública', 'Nacional', 'Nacional', '25/05 a 05/06/2026', '2026-11-08',
             'Exame Nacional do Ensino Médio, aplicado em dois domingos: 8 e 15 de novembro de 2026. Usado para ingresso via SISU, ProUni e FIES.',
             'https://www.gov.br/inep'),
            ('Vestibular Unicamp 2027', 'UNICAMP - Universidade Estadual de Campinas', 'Pública', 'Campinas', 'Sudeste',
             '03/08 a 31/08/2026', '2026-10-18',
             'Vestibular da Comvest para ingresso na Unicamp em 2027. 1ª fase em 18/10/2026; 2ª fase em 29 e 30/11/2026.',
             'https://www.comvest.unicamp.br'),
            ('Vestibular UNESP 2027', 'UNESP - Universidade Estadual Paulista', 'Pública', 'São Paulo', 'Sudeste',
             '04/09 a 20/10/2026', '2026-11-22',
             'Vestibular da Fundação Vunesp para ingresso na UNESP em 2027. 1ª fase em 22/11/2026; 2ª fase em 13 e 14/12/2026.',
             'https://www.vunesp.com.br'),
            ('Seriado UFMG 2026', 'UFMG - Universidade Federal de Minas Gerais', 'Pública', 'Belo Horizonte', 'Sudeste',
             '15/06 a 22/07/2026', '2026-12-13',
             'A UFMG não tem mais vestibular tradicional (extinto em 2013): 70% das vagas são pelo SISU/ENEM e 30% pelo novo Vestibular Seriado, com provas em 12 e 13/12/2026.',
             'https://www.ufmg.br'),
            ('Vestibular UFRJ (ingresso via SISU)', 'UFRJ - Universidade Federal do Rio de Janeiro', 'Pública', 'Rio de Janeiro', 'Sudeste',
             '25/05 a 05/06/2026 (inscrição no Enem)', '2026-11-15',
             'A UFRJ não possui vestibular próprio: o ingresso é feito exclusivamente pela nota do Enem via SISU.',
             'https://ufrj.br'),
            ('Vestibular Unificado UFSC/IFC 2027', 'UFSC - Universidade Federal de Santa Catarina', 'Pública', 'Florianópolis', 'Sul',
             '12/08 a 17/09/2026', '2026-12-05',
             'Vestibular da Coperve para ingresso na UFSC (e no IFC) em 2027, com provas em 05 e 06/12/2026.',
             'https://vestibular.coperve.ufsc.br'),
            ('Vestibular UFRGS 2026', 'UFRGS - Universidade Federal do Rio Grande do Sul', 'Pública', 'Porto Alegre', 'Sul',
             'Consulte o edital da Coperse', '2026-11-29',
             'Vestibular da Coperse, responsável por 70% das vagas de graduação da UFRGS; os outros 30% são pelo SISU. Provas em 29 e 30/11/2026.',
             'https://www.ufrgs.br/ingresso/'),
            ('Vestibular UFBA (ingresso via SISU)', 'UFBA - Universidade Federal da Bahia', 'Pública', 'Salvador', 'Nordeste',
             '25/05 a 05/06/2026 (inscrição no Enem)', '2026-11-15',
             'A UFBA não possui vestibular próprio: o ingresso é feito exclusivamente pela nota do Enem via SISU.',
             'https://www.ufba.br'),
            ('Vestibular Tradicional UnB 2027', 'UnB - Universidade de Brasília', 'Pública', 'Brasília', 'Centro-Oeste',
             'Edital previsto para 20/08/2026', '2026-11-21',
             'Vestibular Tradicional da UnB (Cebraspe) para ingresso em 2027, com provas em 21 e 22/11/2026. A UnB também seleciona pelo PAS (avaliação seriada) e pelo SISU.',
             'https://www.cebraspe.org.br'),
            ('Vestibular FATEC - 1º semestre de 2027', 'FATEC - Faculdade de Tecnologia do Estado de São Paulo', 'Pública', 'São Paulo', 'Sudeste',
             '14/09 a 06/11/2026 (previsão)', None,
             'Vestibular das Fatecs para o 1º semestre de 2027. Período de inscrição é previsão inicial; data da prova ainda não divulgada oficialmente.',
             'https://vestibular.fatec.sp.gov.br'),
        ]
        c.executemany(
            "INSERT INTO vestibulares (nome, instituicao, tipo_instituicao, cidade, regiao, periodo_inscricao, data_prova, descricao, link_edital) VALUES (?,?,?,?,?,?,?,?,?)",
            vestibulares
        )
        conn.commit()

        # Vincula os vestibulares recém-semeados às faculdades pelo nome da instituição
        c.execute("SELECT id, nome FROM faculdades")
        mapa_faculdades = {nome: id for id, nome in c.fetchall()}
        c.execute("SELECT id, instituicao FROM vestibulares WHERE faculdade_id IS NULL")
        for vest_id, instituicao in c.fetchall():
            if instituicao in mapa_faculdades:
                c.execute("UPDATE vestibulares SET faculdade_id=? WHERE id=?", (mapa_faculdades[instituicao], vest_id))
        conn.commit()

    # ── Migração: corrige vestibulares desatualizados em bancos já existentes
    # (mesma lógica do seed acima, mas via UPDATE, para não perder favoritos
    # e outros dados já vinculados aos registros antigos por ID).
    _ATUALIZACOES_VESTIBULARES = {
        'Fuvest 2025': dict(nome='Fuvest 2027', periodo_inscricao='17/08 a 09/10/2026', data_prova='2026-11-01',
                             descricao='Vestibular da Fuvest para ingresso na USP em 2027. 1ª fase em 01/11/2026; 2ª fase em 06 e 07/12/2026.'),
        'Enem 2024': dict(nome='Enem 2026', periodo_inscricao='25/05 a 05/06/2026', data_prova='2026-11-08',
                           descricao='Exame Nacional do Ensino Médio, aplicado em dois domingos: 8 e 15 de novembro de 2026. Usado para ingresso via SISU, ProUni e FIES.'),
        'Unicamp 2025': dict(nome='Vestibular Unicamp 2027', periodo_inscricao='03/08 a 31/08/2026', data_prova='2026-10-18',
                              descricao='Vestibular da Comvest para ingresso na Unicamp em 2027. 1ª fase em 18/10/2026; 2ª fase em 29 e 30/11/2026.'),
        'Vestibular UNESP 2025': dict(nome='Vestibular UNESP 2027', periodo_inscricao='04/09 a 20/10/2026', data_prova='2026-11-22',
                                       descricao='Vestibular da Fundação Vunesp para ingresso na UNESP em 2027. 1ª fase em 22/11/2026; 2ª fase em 13 e 14/12/2026.'),
        'Vestibular UFMG 2025': dict(nome='Seriado UFMG 2026', periodo_inscricao='15/06 a 22/07/2026', data_prova='2026-12-13',
                                      descricao='A UFMG não tem mais vestibular tradicional (extinto em 2013): 70% das vagas são pelo SISU/ENEM e 30% pelo novo Vestibular Seriado, com provas em 12 e 13/12/2026.'),
        'Vestibular UFRJ 2025': dict(nome='Vestibular UFRJ (ingresso via SISU)', periodo_inscricao='25/05 a 05/06/2026 (inscrição no Enem)', data_prova='2026-11-15',
                                      descricao='A UFRJ não possui vestibular próprio: o ingresso é feito exclusivamente pela nota do Enem via SISU.'),
        'Vestibular UFSC 2025': dict(nome='Vestibular Unificado UFSC/IFC 2027', periodo_inscricao='12/08 a 17/09/2026', data_prova='2026-12-05',
                                      descricao='Vestibular da Coperve para ingresso na UFSC (e no IFC) em 2027, com provas em 05 e 06/12/2026.'),
        'Vestibular UFRGS 2025': dict(nome='Vestibular UFRGS 2026', periodo_inscricao='Consulte o edital da Coperse', data_prova='2026-11-29',
                                       descricao='Vestibular da Coperse, responsável por 70% das vagas de graduação da UFRGS; os outros 30% são pelo SISU. Provas em 29 e 30/11/2026.'),
        'Vestibular UFBA 2025': dict(nome='Vestibular UFBA (ingresso via SISU)', periodo_inscricao='25/05 a 05/06/2026 (inscrição no Enem)', data_prova='2026-11-15',
                                      descricao='A UFBA não possui vestibular próprio: o ingresso é feito exclusivamente pela nota do Enem via SISU.'),
        'Vestibular UnB 2025': dict(nome='Vestibular Tradicional UnB 2027', periodo_inscricao='Edital previsto para 20/08/2026', data_prova='2026-11-21',
                                     descricao='Vestibular Tradicional da UnB (Cebraspe) para ingresso em 2027, com provas em 21 e 22/11/2026. A UnB também seleciona pelo PAS (avaliação seriada) e pelo SISU.'),
        'Vestibular FATEC 2025': dict(nome='Vestibular FATEC - 1º semestre de 2027', periodo_inscricao='14/09 a 06/11/2026 (previsão)', data_prova=None,
                                       descricao='Vestibular das Fatecs para o 1º semestre de 2027. Período de inscrição é previsão inicial; data da prova ainda não divulgada oficialmente.'),
    }
    for nome_antigo, novos_dados in _ATUALIZACOES_VESTIBULARES.items():
        c.execute("SELECT id FROM vestibulares WHERE nome=?", (nome_antigo,))
        row = c.fetchone()
        if row:
            c.execute(
                "UPDATE vestibulares SET nome=?, periodo_inscricao=?, data_prova=?, descricao=?, status_validacao='nao_validado' WHERE id=?",
                (novos_dados['nome'], novos_dados['periodo_inscricao'], novos_dados['data_prova'], novos_dados['descricao'], row[0])
            )
    conn.commit()

    conn.commit()
    conn.close()
    print(f"Banco de dados inicializado em: {DB_PATH}")

if __name__ == '__main__':
    init_db()
