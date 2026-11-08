import { useCallback, useEffect, useState } from 'react';

/** Contagem regressiva em segundos (ex.: "Reenviar código em 42 s"). */
export function useContagem() {
  const [restante, setRestante] = useState(0);

  useEffect(() => {
    if (restante <= 0) return;
    const timer = setTimeout(() => setRestante((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [restante]);

  const iniciar = useCallback((segundos: number) => setRestante(Math.max(0, Math.ceil(segundos))), []);
  return { restante, iniciar };
}
