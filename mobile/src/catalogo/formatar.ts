// Apresentação dos dados do catálogo (só formatação; nenhuma regra de negócio).

/**
 * Texto utilizável ou undefined. Parte das faculdades importadas do e-MEC tem cidade/UF
 * gravadas como o texto "null" no banco: não mostramos isso ao usuário.
 */
export function limpo(valor: string | null | undefined): string | undefined {
  const t = valor?.trim();
  return t && t.toLowerCase() !== 'null' ? t : undefined;
}

/** "Campinas/SP", "SP" ou undefined. */
export function local(cidade?: string | null, uf?: string | null): string | undefined {
  const partes = [limpo(cidade), limpo(uf)].filter(Boolean);
  return partes.length ? partes.join('/') : undefined;
}

const MODALIDADES: Record<string, string> = {
  presencial: 'Presencial',
  ead: 'EaD',
  semipresencial: 'Semipresencial',
};

export function modalidade(valor?: string | null): string | undefined {
  const t = limpo(valor);
  return t ? (MODALIDADES[t.toLowerCase()] ?? t) : undefined;
}

/** Junta as partes presentes com " · " (ex.: "Presencial · Bacharelado"). */
export function juntar(...partes: (string | null | undefined)[]): string | undefined {
  const presentes = partes.map((p) => limpo(p ?? undefined)).filter(Boolean);
  return presentes.length ? presentes.join(' · ') : undefined;
}

/** Detalhe das sugestões da busca ("Campinas/SP · Privada") sem as partes "null". */
export function detalheSugestao(texto?: string | null): string | undefined {
  if (!texto) return undefined;
  const partes = texto.split('·').map((parte) =>
    parte.includes('/') ? local(...(parte.split('/') as [string, string])) : limpo(parte),
  );
  return juntar(...partes);
}

/** Nome curto para títulos e cards: a sigla quando existe, senão o nome. */
export function nomeCurto(f: { nome: string; sigla?: string | null }): string {
  return limpo(f.sigla) ?? f.nome;
}

export function plural(n: number, singular: string, pluralTexto: string): string {
  // Separador de milhar sem depender do Intl do motor JS ("2.957").
  const numero = String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${numero} ${n === 1 ? singular : pluralTexto}`;
}

/** Minúsculas e sem acentos (buscas locais, como a da página Ajuda do site). */
export function normalizar(texto: string): string {
  return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}
