// Teste vocacional: a pontuação e a compatibilidade são calculadas no backend.
import { query } from './catalogo';
import { api } from './client';
import type { ItemHistorico, Questionario, Recomendacoes, Resposta, ResultadoTeste } from './tipos';

export const perguntas = () => api<Resposta<Questionario>>('/teste-vocacional/perguntas');

/** respostas: {q1: 'a', ...} (ids das opções). Com o Bearer, entra no histórico da conta. */
export const enviarRespostas = (respostas: Record<string, string>) =>
  api<Resposta<ResultadoTeste>>('/teste-vocacional/resultados', {
    metodo: 'POST',
    corpo: { respostas },
    autenticado: true,
  });

export const historico = (limit = 10) =>
  api<Resposta<ItemHistorico[]>>(`/teste-vocacional/resultados${query({ limit })}`, { autenticado: true });

/** Cursos por compatibilidade com um resultado da própria conta (padrão: o mais recente). */
export const recomendacoes = (id?: number, limite = 50) =>
  api<Resposta<Recomendacoes>>(`/teste-vocacional/recomendacoes${query({ id, limite })}`, { autenticado: true });
