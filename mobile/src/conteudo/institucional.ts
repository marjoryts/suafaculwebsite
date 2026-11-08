// Conteúdo das páginas Ajuda e Sobre nós. Mesmas perguntas, grupos e textos do site
// (app/templates/ajuda.html e sobrenos.html); nas respostas da Ajuda, as instruções
// falam do app ("aba Salvos") em vez do site ("menu do topo").
import { normalizar } from '../catalogo/formatar';

export { normalizar };

export type Pergunta = { pergunta: string; resposta: string };
export type GrupoFaq = { titulo: string; perguntas: Pergunta[] };

export const FAQ: GrupoFaq[] = [
  {
    titulo: 'Conta e acesso',
    perguntas: [
      {
        pergunta: 'Como me cadastrar?',
        resposta:
          'Na tela de entrada, toque em "Criar conta" e preencha nome de usuário, e-mail e senha. A mesma conta funciona no site do SuaFacul.',
      },
      {
        pergunta: 'Como salvo cursos, faculdades e vestibulares?',
        resposta:
          'Toque no ícone de coração em cursos, faculdades ou vestibulares. Os itens salvos ficam na aba Salvos — e também no site, na mesma conta.',
      },
    ],
  },
  {
    titulo: 'Teste vocacional',
    perguntas: [
      {
        pergunta: 'O teste vocacional é gratuito?',
        resposta: 'Sim. O teste é gratuito e online, com 10 perguntas sobre interesses, habilidades e expectativas de carreira.',
      },
      {
        pergunta: 'Onde vejo o resultado do meu teste depois?',
        resposta:
          'O resultado fica salvo na sua conta. Veja em Explorar → Teste vocacional → "Ver meu último resultado", ou no "Meu painel", na aba Perfil.',
      },
    ],
  },
  {
    titulo: 'Busca de cursos, faculdades e vestibulares',
    perguntas: [
      {
        pergunta: 'Como encontro faculdades perto de mim?',
        resposta:
          'Em Explorar, use a busca e escolha a cidade, o estado ou a região sugeridos. Na lista de faculdades, combine com o curso, a modalidade e o tipo de instituição.',
      },
      {
        pergunta: 'Onde vejo as datas dos vestibulares?',
        resposta:
          'Em Explorar → Vestibulares estão o período de inscrição, a data da prova, a taxa e o link do edital. Use os filtros de região e mês da prova; o calendário marca os dias com prova.',
      },
    ],
  },
];

export const SOBRE = {
  chamada: 'Nossa missão é democratizar a sua jornada educacional e te ajudar a encontrar o futuro ideal.',
  historia: [
    'A SuaFacul nasceu da paixão por educação e do desejo de tornar o acesso à informação sobre cursos e faculdades mais fácil e transparente. Percebemos que muitos estudantes se sentiam perdidos em meio a tantas opções e processos seletivos complexos. Por isso, criamos uma plataforma completa para guiar você em cada etapa, desde a descoberta de seu perfil vocacional até a escolha da instituição ideal.',
    'Acreditamos que a escolha de uma carreira é um dos momentos mais importantes na vida de um estudante. Nosso propósito é empoderar você com as ferramentas e o conhecimento necessários para tomar decisões informadas e confiantes sobre seu futuro acadêmico e profissional.',
  ],
  missao:
    'Democratizar a busca por educação superior, conectando estudantes aos cursos e faculdades que melhor se encaixam em seus sonhos e objetivos.',
  visao:
    'Ser a plataforma líder e mais confiável para orientação educacional no Brasil, reconhecida pela inovação e pelo impacto positivo na vida dos estudantes.',
  valores: [
    ['Transparência', 'Oferecer informações claras e imparciais.'],
    ['Inovação', 'Buscar constantemente novas formas de ajudar e inspirar.'],
    ['Empatia', 'Entender as necessidades e desafios dos estudantes.'],
    ['Excelência', 'Comprometimento com a qualidade em tudo o que fazemos.'],
  ] as [string, string][],
  equipeIntro: 'Somos um time dedicado de desenvolvedores unidos pelo objetivo de transformar a educação no Brasil.',
  // Fotos servidas pelo backend (as mesmas do site, em public/imagens).
  equipe: [
    { nome: 'Vinícius Henrique', cargo: 'Desenvolvedor Front-End', foto: '/static/imagens/Vinicius.png' },
    { nome: 'Erick Dantas', cargo: 'Desenvolvedor', foto: '/static/imagens/Erick.png' },
    { nome: 'Marjory Sousa', cargo: 'Desenvolvedora Full Stack', foto: '/static/imagens/Marjory.png' },
  ],
};

/** Grupos só com as perguntas em que TODOS os termos aparecem (pergunta ou resposta). */
export function filtrarFaq(busca: string, faq: GrupoFaq[] = FAQ): GrupoFaq[] {
  const termos = normalizar(busca).split(/\s+/).filter(Boolean);
  if (termos.length === 0) return faq;
  return faq
    .map((g) => ({
      ...g,
      perguntas: g.perguntas.filter((p) => {
        const texto = normalizar(`${p.pergunta} ${p.resposta}`);
        return termos.every((t) => texto.includes(t));
      }),
    }))
    .filter((g) => g.perguntas.length > 0);
}
