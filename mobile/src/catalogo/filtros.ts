// Opções de filtro: os MESMOS valores das páginas /cursos e /faculdades do website
// (app/templates/cursos.html, faculdades.html e public/js/*.js). O backend ainda não
// tem um endpoint que liste as opções disponíveis (lacuna registrada em
// docs/etapa7-mobile.md); quando existir, estas listas devem vir dele.

export type Opcao = { rotulo: string; valor: string };

export const AREAS: Opcao[] = [
  { rotulo: 'Tecnologia', valor: 'Tecnologia' },
  { rotulo: 'Saúde', valor: 'Saúde' },
  { rotulo: 'Direito', valor: 'Direito' },
  { rotulo: 'Negócios', valor: 'Negócios' },
  { rotulo: 'Artes e Design', valor: 'Artes e Design' },
];

// Cursos: checkboxes "Presencial", "EaD", "Semipresencial" (enviados em minúsculas).
export const MODALIDADES_CURSO: Opcao[] = [
  { rotulo: 'Presencial', valor: 'presencial' },
  { rotulo: 'EaD', valor: 'ead' },
  { rotulo: 'Semipresencial', valor: 'semipresencial' },
];

// Faculdades: o site chama de "Híbrido" e envia "semipresencial".
export const MODALIDADES_FACULDADE: Opcao[] = [
  { rotulo: 'Presencial', valor: 'presencial' },
  { rotulo: 'Híbrido', valor: 'semipresencial' },
  { rotulo: 'EaD', valor: 'ead' },
];

export const TIPOS_INSTITUICAO: Opcao[] = [
  { rotulo: 'Pública', valor: 'Pública' },
  { rotulo: 'Privada', valor: 'Privada' },
];

/** Liga/desliga um valor numa seleção múltipla. */
export function alternarValor(lista: string[], valor: string): string[] {
  return lista.includes(valor) ? lista.filter((v) => v !== valor) : [...lista, valor];
}

// Vestibulares: mesmas opções da página /vestibulares do site.
export const INSTITUICOES_VESTIBULAR: Opcao[] = [
  { rotulo: 'Todas', valor: 'Todas' },
  { rotulo: 'Públicas', valor: 'Pública' },
  { rotulo: 'Privadas', valor: 'Privada' },
];

export const REGIOES: Opcao[] = ['Sudeste', 'Sul', 'Nordeste', 'Norte', 'Centro-Oeste'].map((r) => ({
  rotulo: r,
  valor: r,
}));

export const MESES: Opcao[] = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
].map((m, i) => ({ rotulo: m, valor: String(i + 1) }));
