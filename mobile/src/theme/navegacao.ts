import { cores } from './tokens';

// Opções das pilhas das abas: o cabeçalho é desenhado pela própria tela
// (componente Cabecalho, como no Figma), não pelo navegador.
export const opcoesDaPilha = {
  headerShown: false,
  contentStyle: { backgroundColor: cores.fundo },
} as const;
