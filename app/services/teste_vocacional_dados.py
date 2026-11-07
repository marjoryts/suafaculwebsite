"""Conteúdo do Teste Vocacional: única fonte da verdade (Web e Mobile).

Antes, as perguntas e os pesos ficavam no HTML (atributos `value` dos
radios) e a pontuação no JavaScript. Agora ficam aqui; clientes só exibem as
perguntas e enviam as respostas — a pontuação é sempre calculada no backend.

Cada opção tem um `id` (letra, na ordem exibida) e os `perfis` que pontua.
"""

PERFIS = {
    'tecnico': {
        'nome': 'Perfil Técnico / Exato',
        'descricao': 'Você gosta de lógica, tecnologia e resolução de problemas. '
                     'Prefere atividades estruturadas e analíticas.',
        'areas': ['Engenharia', 'TI / Desenvolvimento de Software', 'Análise de Dados',
                  'Sistemas de Informação', 'Arquitetura'],
        # Áreas reais da tabela `cursos` usadas para sugerir cursos (a primeira é a principal).
        'areas_cursos': ['Tecnologia', 'Engenharias'],
    },
    'criativo': {
        'nome': 'Perfil Criativo / Comunicativo',
        'descricao': 'Você se destaca pela criatividade, comunicação e expressão. '
                     'Gosta de ambientes dinâmicos e flexíveis.',
        'areas': ['Design', 'Publicidade e Propaganda', 'Marketing', 'Arquitetura', 'Moda',
                  'Produção Audiovisual'],
        'areas_cursos': ['Artes e Design', 'Comunicação'],
    },
    'humano': {
        'nome': 'Perfil Humano / Social',
        'descricao': 'Você tem empatia, gosta de ajudar pessoas e trabalhar em grupo. '
                     'Valoriza impacto social.',
        'areas': ['Psicologia', 'Pedagogia', 'Recursos Humanos', 'Serviço Social', 'Enfermagem',
                  'Fisioterapia'],
        'areas_cursos': ['Saúde'],
    },
    'gestao': {
        'nome': 'Perfil Gestão / Negócios',
        'descricao': 'Você gosta de organizar, planejar, liderar e entender como as coisas '
                     'funcionam em empresas.',
        'areas': ['Administração', 'Gestão Comercial', 'Economia', 'Logística', 'Finanças',
                  'Empreendedorismo'],
        'areas_cursos': ['Negócios'],
    },
    'cientifico': {
        'nome': 'Perfil Científico / Investigativo',
        'descricao': 'Você é curioso(a), gosta de pesquisa, experimentos e se aprofunda em '
                     'temas complexos.',
        'areas': ['Medicina', 'Biomedicina', 'Biologia', 'Química', 'Física', 'Pesquisa Acadêmica'],
        'areas_cursos': ['Saúde'],
    },
    'pratico': {
        'nome': 'Perfil Prático / Operacional',
        'descricao': 'Você aprende fazendo, gosta de atividades manuais ou aplicadas e prefere '
                     'menos teoria.',
        'areas': ['Técnico em TI', 'Mecatrônica', 'Segurança do Trabalho', 'Produção Industrial',
                  'Manutenção e Mecânica'],
        'areas_cursos': ['Tecnologia', 'Engenharias'],
    },
}

# Ordem de desempate/exibição dos perfis (a mesma do teste original).
ORDEM_PERFIS = ('tecnico', 'criativo', 'humano', 'gestao', 'cientifico', 'pratico')


def _pergunta(id, texto, *opcoes):
    return {
        'id': id,
        'texto': texto,
        'opcoes': [{'id': chr(ord('a') + i), 'texto': t, 'perfis': p.split(',')}
                   for i, (t, p) in enumerate(opcoes)],
    }


SECOES = [
    {'titulo': 'Interesses', 'perguntas': [
        _pergunta('q1', 'Que tipo de atividade você MAIS gosta de fazer?',
                  ('Resolver problemas lógicos, mexer com números ou tecnologia', 'tecnico,cientifico'),
                  ('Criar coisas novas, desenhar, escrever, produzir conteúdo', 'criativo'),
                  ('Ajudar pessoas, ouvir, aconselhar, ensinar', 'humano'),
                  ('Organizar, planejar, liderar grupos ou projetos', 'gestao'),
                  ('Colocar a mão na massa, atividades práticas', 'pratico')),
        _pergunta('q2', 'Você prefere trabalhar mais com:',
                  ('Pessoas', 'humano'),
                  ('Dados, planilhas, análises', 'gestao,tecnico'),
                  ('Objetos, máquinas, tecnologia', 'tecnico,pratico'),
                  ('Arte, criação, comunicação', 'criativo')),
    ]},
    {'titulo': 'Habilidades', 'perguntas': [
        _pergunta('q3', 'Em quais matérias você tem mais facilidade?',
                  ('Matemática, Física, Química', 'tecnico,cientifico'),
                  ('Artes, Redação, Línguas', 'criativo'),
                  ('História, Sociologia, Filosofia', 'humano'),
                  ('Geografia, Economia, Empreendedorismo', 'gestao')),
        _pergunta('q4', 'As pessoas te elogiam mais por:',
                  ('Empatia e jeito com pessoas', 'humano'),
                  ('Criatividade e boas ideias', 'criativo'),
                  ('Raciocínio lógico e solução de problemas', 'tecnico'),
                  ('Organização e liderança', 'gestao'),
                  ('Agilidade para fazer as coisas na prática', 'pratico')),
    ]},
    {'titulo': 'Personalidade no trabalho', 'perguntas': [
        _pergunta('q5', 'Você prefere trabalhar:',
                  ('Mais sozinho(a), focado(a) em suas tarefas', 'tecnico,pratico'),
                  ('Em equipe, trocando ideias com outras pessoas', 'humano,gestao,criativo')),
        _pergunta('q6', 'Você se sente melhor em ambientes:',
                  ('Dinâmicos, com mudanças e novidades', 'criativo,gestao,pratico'),
                  ('Mais estáveis e previsíveis', 'tecnico,cientifico,humano')),
    ]},
    {'titulo': 'Valores e estilo de vida', 'perguntas': [
        _pergunta('q7', 'O que é mais importante para você em uma carreira?',
                  ('Alta remuneração e crescimento financeiro', 'gestao'),
                  ('Impacto social e ajudar pessoas', 'humano'),
                  ('Liberdade criativa e autonomia', 'criativo'),
                  ('Estudar temas complexos e se aprofundar', 'tecnico,cientifico'),
                  ('Ter uma profissão prática e objetiva', 'pratico')),
        _pergunta('q8', 'Você se vê:',
                  ('Estudando por muitos anos (faculdade longa, pós, etc.)', 'cientifico,tecnico'),
                  ('Fazendo cursos mais curtos e já trabalhando rápido', 'pratico,gestao')),
    ]},
    {'titulo': 'Expectativas de carreira', 'perguntas': [
        _pergunta('q9', 'Onde você se imagina trabalhando?',
                  ('Empresa grande ou multinacional', 'gestao,tecnico'),
                  ('Startup ou empresa de tecnologia', 'criativo,tecnico,pratico'),
                  ('Setor público, hospitais, escolas ou pesquisa', 'humano,cientifico'),
                  ('Tendo o próprio negócio', 'gestao,criativo')),
        _pergunta('q10', 'De forma geral, você se identifica mais com qual tipo de área?',
                  ('Técnica / Exatas / Programação', 'tecnico'),
                  ('Criativa / Comunicação / Design', 'criativo'),
                  ('Humana / Social / Educação / Saúde', 'humano'),
                  ('Gestão / Negócios / Administração', 'gestao'),
                  ('Científica / Laboratório / Pesquisa', 'cientifico'),
                  ('Cursos técnicos e profissões práticas', 'pratico')),
    ]},
]
