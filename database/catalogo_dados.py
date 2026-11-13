"""Catálogo curado de cursos e instituições exibido na página inicial.

Como os dados foram montados
----------------------------
- INSTITUICOES: universidades e faculdades reais. Nome, sigla, tipo
  (pública/privada), site, cidade e UF são dados públicos das próprias
  instituições. O endereço só foi preenchido quando é o endereço
  institucional amplamente divulgado; quando não, fica em branco (None)
  em vez de ser inventado. Telefone/e-mail não são preenchidos — podem ser
  completados pelo admin ou pela importação do e-MEC.
- CURSOS: um registro por formação. `duracao` é a duração típica da
  graduação no Brasil (cada instituição pode ter variações) e `descricao`
  é um texto próprio do SuaFacul sobre a formação.
- `ofertas`: instituições que oferecem a graduação, com a modalidade.
  Só entraram ofertas de cursos conhecidos e regulares de cada instituição.
- `imagem`: fotos do Unsplash (licença gratuita do Unsplash, uso comercial
  permitido sem atribuição obrigatória). O link da página da foto não é
  guardado aqui; o ID da CDN identifica a foto de forma única. Cada curso
  usa uma foto diferente.

Para alterar os dados já gravados em bancos existentes, edite este
arquivo e incremente CATALOGO_VERSAO: o init_db atualiza os registros do
catálogo e insere as ofertas que faltarem, sem apagar nada.
"""

CATALOGO_VERSAO = 1

# Parâmetros da CDN do Unsplash: recorte padronizado 16:8 (cards da home),
# formato automático (WebP/AVIF quando o navegador aceita) e qualidade média.
_IMG_PARAMS = 'auto=format&fit=crop&w=640&h=320&q=70'


def _img(photo_id):
    return f'https://images.unsplash.com/{photo_id}?{_IMG_PARAMS}'


# sigla: (nome, organizacao_academica, tipo, url, endereco, cidade, uf)
# As 14 primeiras já existem no seed original de database/init_db.py (mesmo
# nome) e são apenas reaproveitadas; as demais são inseridas se faltarem.
INSTITUICOES = {
    'USP': ('USP - Universidade de São Paulo', 'Universidade', 'Pública', 'https://www5.usp.br',
            'Rua da Reitoria, 374 - Cidade Universitária', 'São Paulo', 'SP'),
    'UNICAMP': ('UNICAMP - Universidade Estadual de Campinas', 'Universidade', 'Pública', 'https://www.unicamp.br',
                'Cidade Universitária Zeferino Vaz', 'Campinas', 'SP'),
    'UNESP': ('UNESP - Universidade Estadual Paulista', 'Universidade', 'Pública', 'https://www2.unesp.br',
              'Rua Quirino de Andrade, 215', 'São Paulo', 'SP'),
    'UNIFESP': ('UNIFESP - Universidade Federal de São Paulo', 'Universidade', 'Pública', 'https://www.unifesp.br',
                'Rua Sena Madureira, 1500', 'São Paulo', 'SP'),
    'PUC-SP': ('PUC-SP - Pontifícia Universidade Católica de São Paulo', 'Universidade', 'Privada', 'https://www.pucsp.br',
               'Rua Ministro Godói, 969', 'São Paulo', 'SP'),
    'UFBA': ('UFBA - Universidade Federal da Bahia', 'Universidade', 'Pública', 'https://www.ufba.br',
             'Rua Barão de Jeremoabo, s/n - Ondina', 'Salvador', 'BA'),
    'UFMG': ('UFMG - Universidade Federal de Minas Gerais', 'Universidade', 'Pública', 'https://www.ufmg.br',
             'Av. Antônio Carlos, 6627 - Pampulha', 'Belo Horizonte', 'MG'),
    'UFF': ('UFF - Universidade Federal Fluminense', 'Universidade', 'Pública', 'https://www.uff.br',
            'Rua Miguel de Frias, 9 - Icaraí', 'Niterói', 'RJ'),
    'UFSCar': ('UFSCAR - Universidade Federal de São Carlos', 'Universidade', 'Pública', 'https://www.ufscar.br',
               'Rod. Washington Luís, km 235', 'São Carlos', 'SP'),
    'UFRJ': ('UFRJ - Universidade Federal do Rio de Janeiro', 'Universidade', 'Pública', 'https://ufrj.br',
             'Av. Pedro Calmon, 550 - Cidade Universitária', 'Rio de Janeiro', 'RJ'),
    'UFSC': ('UFSC - Universidade Federal de Santa Catarina', 'Universidade', 'Pública', 'https://ufsc.br',
             'Campus Universitário Reitor João David Ferreira Lima - Trindade', 'Florianópolis', 'SC'),
    'UFRGS': ('UFRGS - Universidade Federal do Rio Grande do Sul', 'Universidade', 'Pública', 'https://www.ufrgs.br',
              'Av. Paulo Gama, 110 - Farroupilha', 'Porto Alegre', 'RS'),
    'UnB': ('UnB - Universidade de Brasília', 'Universidade', 'Pública', 'https://www.unb.br',
            'Campus Universitário Darcy Ribeiro', 'Brasília', 'DF'),
    'FATEC': ('FATEC - Faculdade de Tecnologia do Estado de São Paulo', 'Centro Universitário', 'Pública',
              'https://www.cps.sp.gov.br/fatec', 'Rua dos Andradas, 140', 'São Paulo', 'SP'),

    # ── Novas instituições ──
    'UFABC': ('UFABC - Universidade Federal do ABC', 'Universidade', 'Pública', 'https://www.ufabc.edu.br',
              'Av. dos Estados, 5001 - Bangu', 'Santo André', 'SP'),
    'ITA': ('ITA - Instituto Tecnológico de Aeronáutica', None, 'Pública', 'https://www.ita.br',
            'Praça Marechal Eduardo Gomes, 50 - Vila das Acácias', 'São José dos Campos', 'SP'),
    'UNIVESP': ('UNIVESP - Universidade Virtual do Estado de São Paulo', 'Universidade', 'Pública', 'https://univesp.br',
                None, 'São Paulo', 'SP'),
    'UFPE': ('UFPE - Universidade Federal de Pernambuco', 'Universidade', 'Pública', 'https://www.ufpe.br',
             'Av. Prof. Moraes Rego, 1235 - Cidade Universitária', 'Recife', 'PE'),
    'UFC': ('UFC - Universidade Federal do Ceará', 'Universidade', 'Pública', 'https://www.ufc.br',
            'Av. da Universidade, 2853 - Benfica', 'Fortaleza', 'CE'),
    'UFPR': ('UFPR - Universidade Federal do Paraná', 'Universidade', 'Pública', 'https://www.ufpr.br',
             'Rua XV de Novembro, 1299 - Centro', 'Curitiba', 'PR'),
    'UFG': ('UFG - Universidade Federal de Goiás', 'Universidade', 'Pública', 'https://www.ufg.br',
            'Av. Esperança, s/n - Campus Samambaia', 'Goiânia', 'GO'),
    'UFV': ('UFV - Universidade Federal de Viçosa', 'Universidade', 'Pública', 'https://www.ufv.br',
            'Av. Peter Henry Rolfs, s/n - Campus Universitário', 'Viçosa', 'MG'),
    'UTFPR': ('UTFPR - Universidade Tecnológica Federal do Paraná', 'Universidade', 'Pública', 'https://www.utfpr.edu.br',
              'Av. Sete de Setembro, 3165 - Rebouças', 'Curitiba', 'PR'),
    'UERJ': ('UERJ - Universidade do Estado do Rio de Janeiro', 'Universidade', 'Pública', 'https://www.uerj.br',
             'Rua São Francisco Xavier, 524 - Maracanã', 'Rio de Janeiro', 'RJ'),
    'PUC-Rio': ('PUC-Rio - Pontifícia Universidade Católica do Rio de Janeiro', 'Universidade', 'Privada',
                'https://www.puc-rio.br', 'Rua Marquês de São Vicente, 225 - Gávea', 'Rio de Janeiro', 'RJ'),
    'PUCRS': ('PUCRS - Pontifícia Universidade Católica do Rio Grande do Sul', 'Universidade', 'Privada',
              'https://www.pucrs.br', 'Av. Ipiranga, 6681 - Partenon', 'Porto Alegre', 'RS'),
    'PUC Minas': ('PUC Minas - Pontifícia Universidade Católica de Minas Gerais', 'Universidade', 'Privada',
                  'https://www.pucminas.br', 'Av. Dom José Gaspar, 500 - Coração Eucarístico', 'Belo Horizonte', 'MG'),
    'Mackenzie': ('Mackenzie - Universidade Presbiteriana Mackenzie', 'Universidade', 'Privada',
                  'https://www.mackenzie.br', 'Rua da Consolação, 930 - Consolação', 'São Paulo', 'SP'),
    'FGV': ('FGV - Fundação Getulio Vargas', None, 'Privada', 'https://portal.fgv.br',
            None, 'São Paulo', 'SP'),
    'Insper': ('Insper - Instituto de Ensino e Pesquisa', None, 'Privada', 'https://www.insper.edu.br',
               'Rua Quatá, 300 - Vila Olímpia', 'São Paulo', 'SP'),
    'ESPM': ('ESPM - Escola Superior de Propaganda e Marketing', None, 'Privada', 'https://www.espm.br',
             'Rua Dr. Álvaro Alvim, 123 - Vila Mariana', 'São Paulo', 'SP'),
    'FEI': ('FEI - Centro Universitário FEI', 'Centro Universitário', 'Privada', 'https://portal.fei.edu.br',
            'Av. Humberto de Alencar Castelo Branco, 3972 - Assunção', 'São Bernardo do Campo', 'SP'),
    'Mauá': ('Mauá - Instituto Mauá de Tecnologia', 'Centro Universitário', 'Privada', 'https://maua.br',
             'Praça Mauá, 1 - Mauá', 'São Caetano do Sul', 'SP'),
    'UMC': ('UMC - Universidade de Mogi das Cruzes', 'Universidade', 'Privada', 'https://www.umc.br',
            'Av. Dr. Cândido Xavier de Almeida e Souza, 200 - Centro Cívico', 'Mogi das Cruzes', 'SP'),
}

P, EAD = 'presencial', 'ead'
BL = 'Bacharelado/Licenciatura'

# Cada curso: nome, area, grau, duracao, descricao, imagem, ofertas.
# Uma oferta é (sigla, modalidade) ou (sigla, modalidade, grau) quando o
# grau naquela instituição difere do grau típico do curso.
CURSOS = [
    # ── Tecnologia ──
    {'nome': 'Ciência da Computação', 'area': 'Tecnologia', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Base teórica e prática da computação: algoritmos, estruturas de dados, sistemas, '
                  'redes e inteligência artificial, para atuar em desenvolvimento e pesquisa.',
     'imagem': _img('photo-1542831371-29b0f74f9713'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFMG', P), ('UFRJ', P), ('UFPE', P), ('UnB', P),
                 ('UFSCar', P), ('UFRGS', P), ('UFABC', P), ('Mackenzie', P), ('PUC-Rio', P), ('Insper', P)]},
    {'nome': 'Engenharia de Software', 'area': 'Tecnologia', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Processos, métodos e ferramentas para projetar, construir, testar e manter '
                  'sistemas de software de qualidade em equipe.',
     'imagem': _img('photo-1522071820081-009f0129c71c'),
     'ofertas': [('UFSCar', P), ('UnB', P), ('UFG', P), ('PUCRS', P)]},
    {'nome': 'Análise e Desenvolvimento de Sistemas', 'area': 'Tecnologia', 'grau': 'Tecnólogo', 'duracao': '3 anos',
     'descricao': 'Graduação tecnológica voltada ao mercado: programação, banco de dados, '
                  'desenvolvimento web e mobile e metodologias ágeis.',
     'imagem': _img('photo-1498050108023-c5249f4df085'),
     'ofertas': [('FATEC', P), ('UTFPR', P)]},
    {'nome': 'Sistemas de Informação', 'area': 'Tecnologia', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Une computação e gestão: desenvolvimento de sistemas, infraestrutura, dados e '
                  'uso estratégico da tecnologia nas organizações.',
     'imagem': _img('photo-1558494949-ef010cbdcc31'),
     'ofertas': [('USP', P), ('UFMG', P), ('UFSC', P), ('PUC Minas', P)]},
    {'nome': 'Engenharia de Computação', 'area': 'Tecnologia', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Integra hardware e software: eletrônica digital, arquitetura de computadores, '
                  'sistemas embarcados e programação.',
     'imagem': _img('photo-1562408590-e32931084e23'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('ITA', P), ('UFRGS', P), ('UTFPR', P), ('UNIVESP', EAD)]},
    {'nome': 'Ciência de Dados', 'area': 'Tecnologia', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Estatística, programação e aprendizado de máquina para coletar, analisar e '
                  'transformar dados em decisões.',
     'imagem': _img('photo-1666875753105-c63a6f3bdc86'),
     'ofertas': [('USP', P), ('UNIVESP', EAD)]},

    # ── Saúde ──
    {'nome': 'Medicina', 'area': 'Saúde', 'grau': 'Bacharelado', 'duracao': '6 anos',
     'descricao': 'Formação de médicos generalistas com sólida base científica, técnica e humanística, '
                  'com internato em serviços de saúde.',
     'imagem': _img('photo-1758691462651-611d730c5272'),
     'ofertas': [('USP', P), ('UNIFESP', P), ('UNICAMP', P), ('UNESP', P), ('UFMG', P), ('UFRJ', P),
                 ('UFC', P), ('UFPE', P), ('UFRGS', P), ('UFPR', P), ('PUCRS', P), ('UMC', P)]},
    {'nome': 'Enfermagem', 'area': 'Saúde', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Cuidado integral ao paciente, gestão de serviços de saúde e promoção da saúde '
                  'em hospitais, unidades básicas e comunidades.',
     'imagem': _img('photo-1758575514475-2a84975db58e'),
     'ofertas': [('USP', P), ('UNIFESP', P), ('UNICAMP', P), ('UFMG', P), ('UFBA', P), ('UFC', P), ('UFRJ', P)]},
    {'nome': 'Odontologia', 'area': 'Saúde', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Prevenção, diagnóstico e tratamento da saúde bucal, com prática clínica '
                  'supervisionada desde a metade do curso.',
     'imagem': _img('photo-1606811856475-5e6fcdc6e509'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UNESP', P), ('UFMG', P), ('UFRJ', P), ('UFPE', P), ('UFPR', P)]},
    {'nome': 'Psicologia', 'area': 'Saúde', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Estudo do comportamento humano e dos processos mentais, preparando para atuação '
                  'clínica, organizacional, escolar e social.',
     'imagem': _img('photo-1758273241078-8eec353836be'),
     'ofertas': [('PUC-SP', P), ('USP', P), ('UNESP', P), ('UFMG', P), ('UFRJ', P), ('UnB', P),
                 ('Mackenzie', P), ('UMC', P), ('PUCRS', P)]},
    {'nome': 'Nutrição', 'area': 'Saúde', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Relação entre alimentação, saúde e qualidade de vida: nutrição clínica, '
                  'esportiva, coletiva e segurança alimentar.',
     'imagem': _img('photo-1535914254981-b5012eebbd15'),
     'ofertas': [('UNIFESP', P), ('USP', P), ('UFRJ', P), ('UFSC', P), ('UnB', P), ('UFG', P), ('UFV', P)]},
    {'nome': 'Farmácia', 'area': 'Saúde', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Medicamentos do desenvolvimento ao uso: farmacologia, análises clínicas, '
                  'indústria farmacêutica e atenção farmacêutica.',
     'imagem': _img('photo-1631549916768-4119b2e5f926'),
     'ofertas': [('USP', P), ('UFMG', P), ('UFRJ', P), ('UFRGS', P), ('UNESP', P), ('UFC', P), ('UFPR', P)]},
    {'nome': 'Fisioterapia', 'area': 'Saúde', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Prevenção e reabilitação de disfunções do movimento, com atuação em clínicas, '
                  'hospitais, esporte e saúde do trabalhador.',
     'imagem': _img('photo-1757689314932-bec6e9c39e51'),
     'ofertas': [('USP', P), ('UNIFESP', P), ('UFMG', P), ('UFSCar', P), ('UNESP', P), ('UFPE', P)]},
    {'nome': 'Medicina Veterinária', 'area': 'Saúde', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Saúde e bem-estar animal, clínica de pequenos e grandes animais, produção animal '
                  'e saúde pública.',
     'imagem': _img('photo-1770836037793-95bdbf190f71'),
     'ofertas': [('USP', P), ('UNESP', P), ('UFMG', P), ('UFV', P), ('UFG', P), ('UFRGS', P), ('UFPR', P)]},
    {'nome': 'Educação Física', 'area': 'Saúde', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Movimento humano, treinamento esportivo, saúde e ensino da educação física '
                  'em escolas, clubes e academias.',
     'imagem': _img('photo-1517836357463-d25dfeac3438'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UNESP', P), ('UFMG', P), ('UFRGS', P)]},
    {'nome': 'Biomedicina', 'area': 'Saúde', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Ciência aplicada à saúde: análises clínicas, imagenologia, genética e pesquisa '
                  'biomédica em laboratório.',
     'imagem': _img('photo-1579165466949-3180a3d056d5'),
     'ofertas': [('UNIFESP', P), ('UNESP', P), ('UFPE', P)]},

    # ── Engenharias ──
    {'nome': 'Engenharia Civil', 'area': 'Engenharias', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Projeto e construção de edificações, estradas, pontes e obras de saneamento, '
                  'com estruturas, geotecnia e gestão de obras.',
     'imagem': _img('photo-1541888946425-d81bb19240f5'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFRJ', P), ('UFMG', P), ('UFPR', P), ('ITA', P),
                 ('UFC', P), ('Mackenzie', P), ('UnB', P), ('FEI', P), ('Mauá', P)]},
    {'nome': 'Engenharia Mecânica', 'area': 'Engenharias', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Projeto e fabricação de máquinas, sistemas térmicos e processos industriais, '
                  'com mecânica dos sólidos, fluidos e materiais.',
     'imagem': _img('photo-1581092160562-40aa08e78837'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('ITA', P), ('UFSC', P), ('UFMG', P), ('FEI', P),
                 ('Mauá', P), ('UTFPR', P)]},
    {'nome': 'Engenharia Elétrica', 'area': 'Engenharias', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Geração, transmissão e uso da energia elétrica, eletrônica, automação '
                  'e sistemas de controle.',
     'imagem': _img('photo-1621905251189-08b45d6a269e'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFSC', P), ('UFMG', P), ('UTFPR', P), ('FEI', P), ('Mauá', P)]},
    {'nome': 'Engenharia de Produção', 'area': 'Engenharias', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Planejamento e otimização de processos produtivos, logística, qualidade '
                  'e gestão de operações.',
     'imagem': _img('photo-1647427060118-4911c9821b82'),
     'ofertas': [('USP', P), ('UFSCar', P), ('UFRJ', P), ('UFSC', P), ('FEI', P)]},
    {'nome': 'Engenharia Química', 'area': 'Engenharias', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Processos que transformam matérias-primas em produtos nas indústrias química, '
                  'petroquímica, alimentícia e farmacêutica.',
     'imagem': _img('photo-1532187863486-abf9dbad1b69'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFRJ', P), ('UFMG', P), ('UFRGS', P), ('Mauá', P), ('FEI', P)]},
    {'nome': 'Engenharia Aeronáutica', 'area': 'Engenharias', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Projeto, fabricação e manutenção de aeronaves: aerodinâmica, estruturas, '
                  'propulsão e sistemas de voo.',
     'imagem': _img('photo-1628000156679-b36c91956540'),
     'ofertas': [('ITA', P), ('USP', P)]},

    # ── Negócios e gestão ──
    {'nome': 'Administração', 'area': 'Negócios', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Gestão de pessoas, finanças, marketing e operações para liderar empresas, '
                  'organizações públicas e o próprio negócio.',
     'imagem': _img('photo-1664575602276-acd073f104c1'),
     'ofertas': [('UFBA', P), ('USP', P), ('FGV', P), ('Insper', P), ('Mackenzie', P), ('UFMG', P),
                 ('UFRGS', P), ('UnB', P), ('PUC-SP', P), ('ESPM', P), ('UMC', P)]},
    {'nome': 'Ciências Contábeis', 'area': 'Negócios', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Contabilidade, auditoria, tributos e finanças para registrar, analisar e '
                  'controlar o patrimônio das organizações.',
     'imagem': _img('photo-1454165804606-c3d57bc86b40'),
     'ofertas': [('USP', P), ('UFMG', P), ('UFRJ', P), ('Mackenzie', P), ('PUC-SP', P), ('UnB', P)]},
    {'nome': 'Ciências Econômicas', 'area': 'Negócios', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Funcionamento dos mercados, políticas públicas, finanças e desenvolvimento, '
                  'com forte base em matemática e estatística.',
     'imagem': _img('photo-1591696205602-2f950c417cb9'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('FGV', P), ('Insper', P), ('UFRJ', P), ('UFMG', P),
                 ('PUC-Rio', P), ('UnB', P), ('UFRGS', P)]},
    {'nome': 'Relações Internacionais', 'area': 'Negócios', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Política internacional, comércio exterior, diplomacia e organizações '
                  'internacionais.',
     'imagem': _img('photo-1521920592574-49e0b121c964'),
     'ofertas': [('USP', P), ('UnB', P), ('PUC-SP', P), ('UFRJ', P), ('UFSC', P), ('PUC-Rio', P), ('ESPM', P)]},
    {'nome': 'Logística', 'area': 'Negócios', 'grau': 'Tecnólogo', 'duracao': '3 anos',
     'descricao': 'Graduação tecnológica em transporte, armazenagem, distribuição e cadeia '
                  'de suprimentos.',
     'imagem': _img('photo-1605745341112-85968b19335b'),
     'ofertas': [('FATEC', P)]},

    # ── Direito ──
    {'nome': 'Direito', 'area': 'Direito', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Raciocínio jurídico e conhecimento das leis para atuar na advocacia, '
                  'magistratura, Ministério Público e carreiras públicas.',
     'imagem': _img('photo-1589829545856-d10d557cf95f'),
     'ofertas': [('USP', P), ('UFMG', P), ('UFRJ', P), ('UnB', P), ('PUC-SP', P), ('Mackenzie', P),
                 ('FGV', P), ('UFPE', P), ('UFPR', P), ('UERJ', P), ('UMC', P), ('PUC-Rio', P), ('UFRGS', P)]},

    # ── Humanas ──
    {'nome': 'História', 'area': 'Humanas', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Estudo crítico das sociedades ao longo do tempo, pesquisa em arquivos e '
                  'formação para o ensino e o patrimônio cultural.',
     'imagem': _img('photo-1491156855053-9cdff72c7f85'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFMG', P), ('UFRJ', P), ('UFF', P), ('UnB', P), ('UNESP', P)]},
    {'nome': 'Filosofia', 'area': 'Humanas', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Grandes questões do pensamento — ética, política, conhecimento e linguagem — '
                  'a partir da leitura dos clássicos.',
     'imagem': _img('photo-1627666338597-ce13e208a93d'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFMG', P), ('PUC-SP', P), ('UFRJ', P)]},
    {'nome': 'Letras', 'area': 'Humanas', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Língua portuguesa, línguas estrangeiras e literatura, com formação para '
                  'ensino, tradução, revisão e produção de textos.',
     'imagem': _img('photo-1497633762265-9d179a990aa6'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFMG', P), ('UFRJ', P), ('UNESP', P),
                 ('UNIVESP', EAD, 'Licenciatura')]},
    {'nome': 'Ciências Sociais', 'area': 'Humanas', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Sociologia, antropologia e ciência política para compreender a sociedade, '
                  'a cultura e as instituições.',
     'imagem': _img('photo-1506787497326-c2736dde1bef'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFMG', P), ('UFRJ', P), ('PUC-SP', P), ('UnB', P)]},

    # ── Educação ──
    {'nome': 'Pedagogia', 'area': 'Educação', 'grau': 'Licenciatura', 'duracao': '4 anos',
     'descricao': 'Formação de professores para a educação infantil e os anos iniciais, além de '
                  'gestão escolar e coordenação pedagógica.',
     'imagem': _img('photo-1509062522246-3755977927d7'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFMG', P), ('UNESP', P), ('UFRJ', P), ('UNIVESP', EAD)]},

    # ── Ciências Exatas ──
    {'nome': 'Matemática', 'area': 'Ciências Exatas', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Álgebra, análise, geometria e matemática aplicada, para pesquisa, mercado '
                  'financeiro, tecnologia e ensino.',
     'imagem': _img('photo-1509228468518-180dd4864904'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFRJ', P), ('UFMG', P), ('UNIVESP', EAD, 'Licenciatura')]},
    {'nome': 'Física', 'area': 'Ciências Exatas', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Leis da natureza da escala atômica à cósmica, com laboratório, modelagem '
                  'matemática e pesquisa científica.',
     'imagem': _img('photo-1633493702341-4d04841df53b'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFRJ', P), ('UFMG', P), ('UFRGS', P)]},
    {'nome': 'Química', 'area': 'Ciências Exatas', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Composição e transformação da matéria, síntese e análise química em '
                  'laboratório, indústria e ensino.',
     'imagem': _img('photo-1532094349884-543bc11b234d'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFMG', P), ('UFRJ', P), ('UNESP', P)]},

    # ── Ciências Biológicas e Agrárias ──
    {'nome': 'Ciências Biológicas', 'area': 'Ciências Biológicas', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Seres vivos e suas interações: genética, ecologia, microbiologia e '
                  'biotecnologia, para pesquisa, meio ambiente e ensino.',
     'imagem': _img('photo-1526930382372-67bf22c0fce2'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFRJ', P), ('UFMG', P), ('UNESP', P), ('UFSC', P)]},
    {'nome': 'Agronomia', 'area': 'Ciências Agrárias', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Produção agrícola sustentável: solos, plantas, irrigação, manejo de culturas '
                  'e gestão do agronegócio.',
     'imagem': _img('photo-1560493676-04071c5f467b'),
     'ofertas': [('USP', P), ('UFV', P), ('UNESP', P), ('UFRGS', P), ('UFG', P), ('UnB', P)]},

    # ── Comunicação ──
    {'nome': 'Jornalismo', 'area': 'Comunicação', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Apuração, redação e edição de notícias para mídia impressa, TV, rádio e '
                  'plataformas digitais.',
     'imagem': _img('photo-1504711434969-e33886168f5c'),
     'ofertas': [('PUC-SP', P), ('USP', P), ('UFRJ', P), ('UFMG', P), ('Mackenzie', P), ('UnB', P), ('ESPM', P)]},
    {'nome': 'Publicidade e Propaganda', 'area': 'Comunicação', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Criação de campanhas, branding, mídia e comunicação digital para marcas '
                  'e organizações.',
     'imagem': _img('photo-1562577308-9e66f0c65ce5'),
     'ofertas': [('USP', P), ('ESPM', P), ('Mackenzie', P), ('UFRJ', P), ('UFMG', P)]},

    # ── Artes e Design ──
    {'nome': 'Arquitetura e Urbanismo', 'area': 'Artes e Design', 'grau': 'Bacharelado', 'duracao': '5 anos',
     'descricao': 'Projeto de edificações, interiores e espaços urbanos, unindo técnica, '
                  'estética e planejamento das cidades.',
     'imagem': _img('photo-1503387762-592deb58ef4e'),
     'ofertas': [('UFF', P), ('USP', P), ('Mackenzie', P), ('UNICAMP', P), ('UFMG', P), ('UFRJ', P), ('UnB', P)]},
    {'nome': 'Design', 'area': 'Artes e Design', 'grau': 'Bacharelado', 'duracao': '4 anos',
     'descricao': 'Design gráfico, de produto e de interfaces: criação visual, tipografia, '
                  'ergonomia e experiência do usuário.',
     'imagem': _img('photo-1561070791-2526d30994b5'),
     'ofertas': [('USP', P), ('UNESP', P), ('ESPM', P), ('Mackenzie', P), ('UFPE', P)]},
    {'nome': 'Música', 'area': 'Artes e Design', 'grau': BL, 'duracao': '4 anos',
     'descricao': 'Prática instrumental ou vocal, composição, regência e teoria musical, com '
                  'formação para palco, estúdio e ensino.',
     'imagem': _img('photo-1514320291840-2e0a9bf2a9ae'),
     'ofertas': [('USP', P), ('UNICAMP', P), ('UFRJ', P), ('UNESP', P), ('UFMG', P)]},
]
