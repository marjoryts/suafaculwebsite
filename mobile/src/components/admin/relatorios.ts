import type { RelatorioImportacao } from '../../api/tipos';
import { juntar } from '../../catalogo/formatar';

/** Uma linha legível a partir do relatório da importação (o formato varia por tipo). */
export function resumoImportacao(r: RelatorioImportacao): string {
  if (typeof r.message === 'string' && r.message) return r.message;
  const n = (k: string) => (typeof r[k] === 'number' ? (r[k] as number) : undefined);
  const partes = [
    n('total_encontradas') !== undefined ? `${n('total_encontradas')} encontradas` : undefined,
    n('total_criadas') !== undefined ? `${n('total_criadas')} criadas` : undefined,
    n('total_atualizadas') !== undefined ? `${n('total_atualizadas')} atualizadas` : undefined,
    n('ufs_processadas') !== undefined ? `${n('ufs_processadas')} UFs processadas` : undefined,
  ];
  return juntar(...partes) ?? (r.success === false ? 'A importação falhou.' : 'Importação concluída.');
}
