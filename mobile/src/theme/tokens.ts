// Tokens de design extraídos do Figma do SuaFacul (página "Mobile", arquivo
// HhMYIH3w5TqKBUE9o40rY0). Nenhuma tela deve usar valores soltos: sempre estes tokens.
// Valores que o Figma não define estão marcados com "fora do Figma".
import type { TextStyle, ViewStyle } from 'react-native';

export const cores = {
  // Marca
  roxo: '#5a189a', // botões primários, cabeçalhos roxos, ícones de configuração
  roxoEscuro: '#401a65', // títulos e textos de destaque
  roxoMedio: '#632e97', // botões e cartão de destaque do teste vocacional (Figma)
  roxoProfundo: '#48137b', // topo do cadastro (#5a189a com 20% de preto por cima, como no Figma)
  roxoClaro: '#8a56bd', // terceiro tom dos cards de cursos (Figma "Página Faculdades")
  laranja: '#ff9100', // barra inferior, chips, ícones de busca e listas
  laranjaClaro: '#ffa833', // folha do login, botão "Cadastrar"

  // Superfícies
  fundo: '#f2f2f2', // fundo das telas
  folha: '#f5f5f5', // folhas arredondadas sobre cabeçalhos coloridos
  superficie: '#ffffff', // campos, cards e linhas de lista
  campoBusca: 'rgba(20, 18, 24, 0.08)',
  botaoVoltar: '#dadada', // sobre fundo claro
  botaoVoltarSobreCor: 'rgba(241, 241, 241, 0.95)', // sobre roxo/laranja

  // Texto
  texto: '#262626',
  textoSuave: '#757575', // fora do Figma: textos de apoio (contraste AA sobre #f2f2f2)
  placeholder: '#b3b3b3',
  textoInativo: 'rgba(26, 26, 26, 0.24)',
  sobreMarca: '#f5f5f5', // texto sobre botões roxos/laranja
  sobreBarra: '#fef7ff', // rótulos da barra inferior
  branco: '#ffffff',

  borda: '#d9d9d9',

  // Estados (fora do Figma: o design não define cores de erro/sucesso)
  erro: '#b3261e',
  sucesso: '#1e7d32',
};

/** Famílias carregadas em app/_layout.tsx (useFonts). */
export const familias = {
  interRegular: 'Inter_400Regular',
  interMedio: 'Inter_500Medium',
  interSemi: 'Inter_600SemiBold',
  interNegrito: 'Inter_700Bold',
  interExtra: 'Inter_800ExtraBold',
  robotoMedio: 'Roboto_500Medium',
  robotoSemi: 'Roboto_600SemiBold',
  slogan: 'DarkerGrotesque_400Regular',
};

/** Estilos de texto do Figma. */
export const tipografia = {
  // "Bem-vindo(a) de volta!" (Heading 24/1.2, -0.48)
  titulo: { fontFamily: familias.interSemi, fontSize: 24, lineHeight: 29, letterSpacing: -0.48 },
  // "Faculdades Públicas" na home
  secao: { fontFamily: familias.interExtra, fontSize: 25 },
  // "Faculdades Favoritas", "Cursos Favoritos"
  subtitulo: { fontFamily: familias.interSemi, fontSize: 24, lineHeight: 30, letterSpacing: 0.2 },
  // "Olá, Júlio!"
  saudacao: { fontFamily: familias.interSemi, fontSize: 25 },
  // Título do cabeçalho com voltar ("Favoritos", "Vestibulares")
  cabecalho: { fontFamily: familias.robotoSemi, fontSize: 24, lineHeight: 30, letterSpacing: 0.2 },
  // Itens de lista ("Fatec Ferraz")
  item: { fontFamily: familias.interRegular, fontSize: 20, lineHeight: 30, letterSpacing: 0.2 },
  // Linhas de configuração do Perfil
  opcao: { fontFamily: familias.interSemi, fontSize: 22 },
  // Título das páginas de detalhe ("USP", "Engenharia de Software")
  tituloPagina: { fontFamily: familias.interMedio, fontSize: 28, lineHeight: 34, letterSpacing: 0.2 },
  // "O que você vai aprender?", "Cursos e suas compatibilidades"
  tituloBloco: { fontFamily: familias.interSemi, fontSize: 20, lineHeight: 30, letterSpacing: 0.2 },
  // Textos descritivos (Figma: 13/15 em #757575; aqui 14/20 para leitura no celular)
  descricao: { fontFamily: familias.interRegular, fontSize: 14, lineHeight: 20, letterSpacing: 0.2 },
  // Itens de informação do curso ("Duração: 4 ou 5 anos.")
  info: { fontFamily: familias.interMedio, fontSize: 14, lineHeight: 20, letterSpacing: 0.2 },
  // Nome sobre os cards coloridos
  cartao: { fontFamily: familias.interSemi, fontSize: 20, lineHeight: 26 },
  corpo: { fontFamily: familias.interRegular, fontSize: 16, lineHeight: 22 },
  rotulo: { fontFamily: familias.interSemi, fontSize: 16, lineHeight: 22 },
  // Texto dos botões grandes (no Figma: SF Pro 22/28; Inter no Android e iOS)
  botao: { fontFamily: familias.interRegular, fontSize: 22, lineHeight: 28, letterSpacing: -0.26 },
  botaoCompacto: { fontFamily: familias.interSemi, fontSize: 16, lineHeight: 22 },
  // M3 Label Large (chips) e Label Medium (barra inferior)
  chip: { fontFamily: familias.robotoMedio, fontSize: 14, lineHeight: 20, letterSpacing: 0.1 },
  barra: { fontFamily: familias.robotoMedio, fontSize: 12, lineHeight: 16, letterSpacing: 0.5 },
  legenda: { fontFamily: familias.interMedio, fontSize: 12 },
  slogan: { fontFamily: familias.slogan, fontSize: 30 },
} satisfies Record<string, TextStyle>;

/** Escala de espaçamento (Simple Design System do Figma: space-100..600). */
export const espaco = { xxs: 2, xs: 4, sm: 8, smd: 12, md: 16, lg: 24, xl: 32 };

export const raio = {
  icone: 10, // quadrado roxo dos itens de informação
  campo: 15, // campos, botões e o botão voltar
  linha: 20, // linhas de lista
  cartao: 26, // cards com imagem
  barra: 30, // barra inferior
  painel: 40, // folha clara do Perfil
  folha: 53, // folha arredondada sobre cabeçalho colorido
  pilula: 100, // chips e busca
};

export const dimensoes = {
  alturaBotao: 52, // 28 de linha + 2×12 de padding
  alturaCampo: 47,
  alturaBusca: 45,
  alturaLinha: 62,
  alturaBarra: 56,
  botaoVoltar: 30,
  iconeVoltar: 26,
  iconeLinha: 32,
  iconeOpcao: 50,
  avatar: 66,
  avatarGrande: 120,
  cartao: { largura: 196, altura: 153 }, // cards da home
  iconeInfo: 40,
  logo: { largura: 128, altura: 110 },
  logoGrande: { largura: 244, altura: 210 },
  areaToque: 44, // mínimo recomendado para toque
};

/** Sombra "0 4 4 rgba(0,0,0,.25)" do Figma (campos, botões e linhas). */
export const sombra: ViewStyle = {
  shadowColor: '#000',
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.25,
  shadowRadius: 4,
  elevation: 4,
};
