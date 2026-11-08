// Datas das provas (apresentação). As datas vêm em ISO "AAAA-MM-DD" e são tratadas
// como datas locais (sem fuso), para "10/04" não virar "09/04" em UTC-3.
import { juntar } from './formatar';

const DIAS = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado'];
const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro',
  'outubro', 'novembro', 'dezembro'];
export const DIAS_CURTOS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']; // como no Figma

/** Date local a partir de "AAAA-MM-DD"; null se ausente ou inválida. */
export function lerData(iso?: string | null): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso?.trim() ?? '');
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return d.getMonth() === Number(m[2]) - 1 ? d : null; // rejeita 2026-02-31
}

export function inicioDoDia(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export function chaveDia(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** "10/04/2026" */
export function dataCurta(iso?: string | null): string | undefined {
  const d = lerData(iso);
  if (!d) return undefined;
  return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`;
}

/** "Sexta-feira, 10 de abril de 2026" (cabeçalho do calendário, como no Figma). */
export function dataPorExtenso(d: Date): string {
  return `${DIAS[d.getDay()]}, ${d.getDate()} de ${MESES[d.getMonth()]} de ${d.getFullYear()}`;
}

/** Dias inteiros de `hoje` até a data (0 = hoje, negativo = já passou); null sem data. */
export function diasAte(iso: string | null | undefined, hoje: Date = new Date()): number | null {
  const d = lerData(iso);
  if (!d) return null;
  return Math.round((d.getTime() - inicioDoDia(hoje).getTime()) / 86_400_000);
}

/** "Hoje", "Amanhã", "68 dias", "Prova realizada" ou undefined (sem data). */
export function rotuloDias(iso: string | null | undefined, hoje: Date = new Date()): string | undefined {
  const n = diasAte(iso, hoje);
  if (n === null) return undefined;
  if (n < 0) return 'Prova realizada';
  if (n === 0) return 'Hoje';
  if (n === 1) return 'Amanhã';
  return `${n} dias`;
}

/** Os 7 dias (segunda a domingo) da semana de `referencia`. */
export function semana(referencia: Date): Date[] {
  const base = inicioDoDia(referencia);
  const deslocamento = (base.getDay() + 6) % 7; // segunda = 0
  return Array.from({ length: 7 }, (_, i) => new Date(base.getFullYear(), base.getMonth(), base.getDate() - deslocamento + i));
}

/** "Prova: 10/04/2026 · 68 dias" (ou "Data a definir"), para listas de vestibulares. */
export function resumoProva(v: { data_prova: string | null; instituicao: string | null }, hoje: Date = new Date()) {
  const data = dataCurta(v.data_prova);
  return data ? juntar(`Prova: ${data}`, rotuloDias(v.data_prova, hoje)) : juntar(v.instituicao, 'Data a definir');
}
