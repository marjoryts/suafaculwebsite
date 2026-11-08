// Endpoints públicos do catálogo (somente os que existem em /api/v1).
import { api } from './client';
import type { Curso, Faculdade, FaculdadeDetalhe, Paginated, Resposta, Sugestoes, Vestibular } from './tipos';

type Valor = string | number | undefined | null | string[];

/** Monta a query string; listas viram parâmetros repetidos (?modalidade=a&modalidade=b). */
export function query(params: Record<string, Valor>): string {
  const partes: string[] = [];
  for (const [chave, valor] of Object.entries(params)) {
    const valores = Array.isArray(valor) ? valor : [valor];
    for (const v of valores) {
      if (v === undefined || v === null || v === '') continue;
      partes.push(`${encodeURIComponent(chave)}=${encodeURIComponent(String(v))}`);
    }
  }
  return partes.length ? `?${partes.join('&')}` : '';
}

export type FiltrosCursos = {
  busca?: string;
  area?: string;
  modalidade?: string[];
  tipo_instituicao?: string[];
};

export type FiltrosFaculdades = {
  busca?: string;
  tipo_instituicao?: string;
  modalidade?: string[];
  /** Cidade, sigla de UF ou região (o backend interpreta os três). */
  cidade?: string;
  /** Faculdades que oferecem um curso com este nome. */
  curso?: string;
};

export type FiltrosVestibulares = {
  busca?: string;
  /** "Todas" (padrão do site), "Pública" ou "Privada". */
  instituicao?: 'Todas' | 'Pública' | 'Privada';
  regiao?: string[];
  mes?: number[];
  curso?: string;
};

export const listarCursos = (filtros: FiltrosCursos, page = 1, limit = 20) =>
  api<Paginated<Curso>>(`/cursos${query({ ...filtros, page, limit })}`);

export const obterCurso = (id: number) => api<Resposta<Curso>>(`/cursos/${id}`);

export const listarFaculdades = (filtros: FiltrosFaculdades, page = 1, limit = 20) =>
  api<Paginated<Faculdade>>(`/faculdades${query({ ...filtros, page, limit })}`);

export const obterFaculdade = (id: number) => api<Resposta<FaculdadeDetalhe>>(`/faculdades/${id}`);

export function listarVestibulares(filtros: FiltrosVestibulares, page = 1, limit = 20) {
  const { instituicao = 'Todas', mes, ...resto } = filtros;
  // Como no site: sem incluir_privados a API devolve só as públicas.
  const tipo = instituicao === 'Todas' ? {} : { tipo_instituicao: instituicao };
  return api<Paginated<Vestibular>>(
    `/vestibulares${query({
      ...resto,
      ...tipo,
      mes: mes?.map(String),
      incluir_privados: instituicao === 'Pública' ? undefined : 'true',
      page,
      limit,
    })}`,
  );
}

export const obterVestibular = (id: number) => api<Resposta<Vestibular>>(`/vestibulares/${id}`);

export const sugestoes = (q: string, limite = 5) =>
  api<Resposta<Sugestoes>>(`/busca/sugestoes${query({ q, limite })}`);
