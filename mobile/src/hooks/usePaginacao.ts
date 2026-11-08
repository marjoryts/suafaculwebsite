import { DependencyList, useCallback, useEffect, useRef, useState } from 'react';

import type { Paginated } from '../api/tipos';
import { mensagemDeErro } from './useConsulta';

type Estado<T> = {
  itens: T[];
  total: number;
  pagina: number;
  totalPaginas: number;
  carregando: boolean; // primeira página
  carregandoMais: boolean;
  erro: string | null;
};

const INICIAL = { itens: [], total: 0, pagina: 0, totalPaginas: 0, carregando: true, carregandoMais: false, erro: null };

/**
 * Lista paginada do backend ({data, meta}) com "carregar mais" para rolagem infinita.
 * Quando as dependências (filtros) mudam, recomeça da página 1 e descarta respostas antigas.
 */
export function usePaginacao<T>(buscarPagina: (pagina: number) => Promise<Paginated<T>>, deps: DependencyList) {
  const [estado, setEstado] = useState<Estado<T>>(INICIAL);
  const versao = useRef(0);
  const ocupado = useRef(false);

  // As dependências (filtros) vêm de quem chama, como num useEffect.
  const buscar = useCallback(buscarPagina, deps);

  const carregarPagina = useCallback(
    async (pagina: number) => {
      const minha = pagina === 1 ? ++versao.current : versao.current;
      ocupado.current = true;
      setEstado((e) =>
        pagina === 1 ? { ...INICIAL, carregando: true } : { ...e, carregandoMais: true, erro: null },
      );
      try {
        const { data, meta } = await buscar(pagina);
        if (minha !== versao.current) return;
        setEstado((e) => ({
          itens: pagina === 1 ? data : [...e.itens, ...data],
          total: meta.total,
          pagina: meta.page,
          totalPaginas: meta.total_pages,
          carregando: false,
          carregandoMais: false,
          erro: null,
        }));
      } catch (err) {
        if (minha !== versao.current) return;
        setEstado((e) => ({ ...e, carregando: false, carregandoMais: false, erro: mensagemDeErro(err) }));
      } finally {
        if (minha === versao.current) ocupado.current = false;
      }
    },
    [buscar],
  );

  useEffect(() => {
    void carregarPagina(1);
  }, [carregarPagina]);

  const carregarMais = useCallback(() => {
    if (ocupado.current || estado.erro || estado.pagina >= estado.totalPaginas) return;
    void carregarPagina(estado.pagina + 1);
  }, [carregarPagina, estado.erro, estado.pagina, estado.totalPaginas]);

  // Funções estáveis: telas as usam em useFocusEffect; uma função nova a cada render
  // faria o efeito (e a requisição) se repetir sem fim.
  const recarregar = useCallback(() => carregarPagina(1), [carregarPagina]);
  /** Depois de um erro ao carregar mais, tenta a mesma página de novo. */
  const tentarMaisNovamente = useCallback(() => carregarPagina(estado.pagina + 1), [carregarPagina, estado.pagina]);

  return {
    ...estado,
    temMais: estado.pagina < estado.totalPaginas,
    carregarMais,
    recarregar,
    tentarMaisNovamente,
  };
}
