CREATE DATABASE Suafacul_crud;

DELIMITER //
CREATE PROCEDURE inserir_candidato(
    IN p_email VARCHAR(30),
    IN p_senha VARCHAR(512),
    IN p_nome VARCHAR(80),
    IN p_cpf VARCHAR(14),
    IN p_endereco VARCHAR(150),
    IN p_dataNasc DATE
)
BEGIN
    INSERT INTO Candidato (emailCandidato, senhaCandidato, nomeCandidato, cpfCandidato, endereco, dataNasc)
    VALUES (p_email, p_senha, p_nome, p_cpf, p_endereco, p_dataNasc);
END //
DELIMITER ;

USE Suafacul_crud;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome_usuario VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_nome_usuario (nome_usuario),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cursos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    modalidade ENUM('presencial', 'ead', 'semipresencial') NOT NULL DEFAULT 'presencial',
    descricao TEXT,
    duracao VARCHAR(50),
    grau VARCHAR(100),
    area VARCHAR(100),
    tipo_instituicao ENUM('Pública', 'Privada') NOT NULL DEFAULT 'Pública',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_area (area),
    INDEX idx_modalidade (modalidade),
    INDEX idx_tipo_instituicao (tipo_instituicao),
    INDEX idx_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO cursos (nome, modalidade, descricao, duracao, grau, area, tipo_instituicao) VALUES
('Engenharia de Software', 'presencial', 'Curso focado no desenvolvimento de sistemas complexos e aplicações de software de alta qualidade.', '4 anos', 'Bacharelado', 'Tecnologia', 'Pública'),
('Medicina', 'presencial', 'Formação de médicos generalistas com sólida base científica, técnica e humanística.', '6 anos', 'Bacharelado', 'Saúde', 'Pública'),
('Psicologia', 'presencial', 'Estudo do comportamento humano e processos mentais, preparando para atuação clínica e organizacional.', '5 anos', 'Bacharelado', 'Saúde', 'Privada'),
('Direito', 'presencial', 'Desenvolve o raciocínio jurídico para atuação em diversas áreas do direito.', '5 anos', 'Bacharelado', 'Direito', 'Privada'),
('Administração', 'presencial', 'Prepara líderes e gestores para os desafios do mercado corporativo.', '4 anos', 'Bacharelado', 'Negócios', 'Privada'),
('Ciência da Computação', 'presencial', 'Estudo aprofundado de algoritmos, estruturas de dados e inteligência artificial.', '4 anos', 'Bacharelado', 'Tecnologia', 'Pública'),
('Nutrição', 'semipresencial', 'Foca na relação entre alimentação, saúde e qualidade de vida.', '4 anos', 'Bacharelado', 'Saúde', 'Privada'),
('Engenharia Civil', 'presencial', 'Projetos e construção de infraestruturas como edifícios, pontes e estradas.', '5 anos', 'Bacharelado', 'Engenharias', 'Pública'),
('Jornalismo', 'presencial', 'Forma comunicadores para produzir e disseminar informações em diversas plataformas.', '4 anos', 'Bacharelado', 'Comunicação', 'Privada'),
('Arquitetura e Urbanismo', 'presencial', 'Planejamento e concepção de espaços urbanos e edificações.', '5 anos', 'Bacharelado', 'Artes e Design', 'Privada');

USE Suafacul_crud;

ALTER TABLE cursos
ADD COLUMN instituicao VARCHAR(255) NOT NULL DEFAULT 'Instituição não informada';

-- Atualizar instituições dos cursos com nomes completos
UPDATE cursos SET instituicao = 'UFSCAR - Universidade Federal de São Carlos' WHERE nome = 'Engenharia de Software';
UPDATE cursos SET instituicao = 'UNIFESP - Universidade Federal de São Paulo' WHERE nome = 'Medicina';
UPDATE cursos SET instituicao = 'PUC-SP - Pontifícia Universidade Católica de São Paulo' WHERE nome = 'Psicologia';
UPDATE cursos SET instituicao = 'USP - Universidade de São Paulo' WHERE nome = 'Direito';
UPDATE cursos SET instituicao = 'UFBA - Universidade Federal da Bahia' WHERE nome = 'Administração';
UPDATE cursos SET instituicao = 'UFMG - Universidade Federal de Minas Gerais' WHERE nome = 'Ciência da Computação';
UPDATE cursos SET instituicao = 'UNIFESP - Universidade Federal de São Paulo' WHERE nome = 'Nutrição';
UPDATE cursos SET instituicao = 'USP - Universidade de São Paulo' WHERE nome = 'Engenharia Civil';
UPDATE cursos SET instituicao = 'PUC-SP - Pontifícia Universidade Católica de São Paulo' WHERE nome = 'Jornalismo';
UPDATE cursos SET instituicao = 'UFF - Universidade Federal Fluminense' WHERE nome = 'Arquitetura e Urbanismo';


CREATE TABLE IF NOT EXISTS vestibulares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    tipo_instituicao ENUM('Pública', 'Privada') NOT NULL DEFAULT 'Pública',
    cidade VARCHAR(100),
    regiao VARCHAR(50),
    periodo_inscricao VARCHAR(100),
    data_prova DATE,
    descricao TEXT,
    link_edital VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tipo_instituicao (tipo_instituicao),
    INDEX idx_regiao (regiao),
    INDEX idx_data_prova (data_prova),
    INDEX idx_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=UTF8MB4_UNICODE_CI;

INSERT INTO vestibulares (nome, tipo_instituicao, cidade, regiao, periodo_inscricao, data_prova, descricao, link_edital) VALUES
('Fuvest 2025', 'Pública', 'São Paulo', 'Sudeste', '15/08 a 15/09', '2025-11-15', 'O vestibular da Fuvest é a principal porta de entrada para a Universidade de São Paulo (USP).', 'https://www.fuvest.br/vestibular-da-usp'),
('Enem 2024', 'Pública', 'Nacional', 'Nacional', '01/05 a 15/05', '2024-11-03', 'O Exame Nacional do Ensino Médio é usado como porta de entrada para diversas universidades e programas governamentais.', 'https://www.gov.br/inep'),
('Unicamp 2025', 'Pública', 'Campinas', 'Sudeste', '29/07 a 30/08', '2025-10-20', 'O vestibular da Unicamp é um dos mais concorridos do país, conhecido por sua prova dissertativa.', 'https://www.comvest.unicamp.br'),
('Vestibular UNESP 2025', 'Pública', 'São Paulo', 'Sudeste', '10/09 a 10/10', '2025-12-15', 'Vestibular da UNESP, uma das principais universidades estaduais de São Paulo.', 'https://www.vunesp.com.br'),
('Vestibular UFMG 2025', 'Pública', 'Belo Horizonte', 'Sudeste', '01/08 a 31/08', '2025-11-10', 'Vestibular da UFMG, uma das maiores universidades federais do Brasil.', 'https://www.ufmg.br'),
('Vestibular UFRJ 2025', 'Pública', 'Rio de Janeiro', 'Sudeste', '15/08 a 15/09', '2025-12-01', 'Vestibular da UFRJ, principal universidade federal do Rio de Janeiro.', 'https://www.ufrj.br'),
('Vestibular UFSC 2025', 'Pública', 'Florianópolis', 'Sul', '01/09 a 30/09', '2025-11-25', 'Vestibular da UFSC, uma das principais universidades do sul do país.', 'https://www.ufsc.br'),
('Vestibular UFRGS 2025', 'Pública', 'Porto Alegre', 'Sul', '10/08 a 10/09', '2025-11-20', 'Vestibular da UFRGS, uma das mais tradicionais universidades do sul.', 'https://www.ufrgs.br'),
('Vestibular UFBA 2025', 'Pública', 'Salvador', 'Nordeste', '01/09 a 30/09', '2025-12-10', 'Vestibular da UFBA, principal universidade federal da Bahia.', 'https://www.ufba.br'),
('Vestibular UnB 2025', 'Pública', 'Brasília', 'Centro-Oeste', '15/08 a 15/09', '2025-11-15', 'Vestibular da UnB, principal universidade federal do Distrito Federal.', 'https://www.unb.br'),
('Vestibular FATEC 2025', 'Pública', 'São Paulo', 'Sudeste', '01/05 a 31/05', '2025-06-29', 'Vestibular da FATEC, faculdades de tecnologia do estado de São Paulo.', 'https://vestibular.fatec.sp.gov.br');

ALTER TABLE vestibulares
ADD COLUMN instituicao VARCHAR(255);

UPDATE vestibulares SET instituicao = 'USP' WHERE nome = 'Fuvest 2025';
UPDATE vestibulares SET instituicao = 'INEP' WHERE nome = 'Enem 2024';
UPDATE vestibulares SET instituicao = 'UNICAMP' WHERE nome = 'Unicamp 2025';
UPDATE vestibulares SET instituicao = 'UNESP' WHERE nome = 'Vestibular UNESP 2025';
UPDATE vestibulares SET instituicao = 'UFMG' WHERE nome = 'Vestibular UFMG 2025';
UPDATE vestibulares SET instituicao = 'UFRJ' WHERE nome = 'Vestibular UFRJ 2025';
UPDATE vestibulares SET instituicao = 'UFSC' WHERE nome = 'Vestibular UFSC 2025';
UPDATE vestibulares SET instituicao = 'UFRGS' WHERE nome = 'Vestibular UFRGS 2025';
UPDATE vestibulares SET instituicao = 'UFBA' WHERE nome = 'Vestibular UFBA 2025';
UPDATE vestibulares SET instituicao = 'UnB' WHERE nome = 'Vestibular UnB 2025';
UPDATE vestibulares SET instituicao = 'FATEC' WHERE nome = 'Vestibular FATEC 2025';

CREATE TABLE IF NOT EXISTS teste_vocacional_resultados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    perfil_principal VARCHAR(50) NOT NULL,
    perfis_json TEXT NOT NULL,
    respostas_json TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS favoritos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    tipo ENUM('curso', 'vestibular', 'faculdade') NOT NULL,
    item_id INT NOT NULL,
    nome_item VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_favorito (usuario_id, tipo, item_id),
    INDEX idx_usuario (usuario_id),
    INDEX idx_tipo (tipo),
    INDEX idx_item_id (item_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;