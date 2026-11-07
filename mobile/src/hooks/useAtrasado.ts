import { useEffect, useState } from 'react';

/** O valor só muda depois de `ms` sem alterações (evita uma consulta por tecla). */
export function useAtrasado<T>(valor: T, ms = 400): T {
  const [atrasado, setAtrasado] = useState(valor);
  useEffect(() => {
    const t = setTimeout(() => setAtrasado(valor), ms);
    return () => clearTimeout(t);
  }, [valor, ms]);
  return atrasado;
}
