import { DependencyList, useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';

/** Texto para o usuário a partir de qualquer erro da API. */
export function mensagemDeErro(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return 'Não foi possível carregar. Tente novamente.';
}

type Estado<T> = { dados: T | null; erro: string | null; carregando: boolean };

/**
 * Executa uma consulta quando as dependências mudam. Respostas que chegam
 * depois de uma consulta mais nova são descartadas (evita mostrar dados velhos
 * quando o usuário troca filtros rápido).
 */
export function useConsulta<T>(consultar: () => Promise<T>, deps: DependencyList) {
  const [estado, setEstado] = useState<Estado<T>>({ dados: null, erro: null, carregando: true });
  const versao = useRef(0);

  // As dependências vêm de quem chama, como num useEffect.
  const executar = useCallback(consultar, deps);

  const recarregar = useCallback(async () => {
    const minha = ++versao.current;
    setEstado((e) => ({ ...e, erro: null, carregando: true }));
    try {
      const dados = await executar();
      if (minha === versao.current) setEstado({ dados, erro: null, carregando: false });
    } catch (e) {
      if (minha === versao.current) setEstado((s) => ({ ...s, erro: mensagemDeErro(e), carregando: false }));
    }
  }, [executar]);

  useEffect(() => {
    void recarregar();
  }, [recarregar]);

  return { ...estado, recarregar };
}
