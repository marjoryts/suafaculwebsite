// Hooks de dados e formatação do catálogo (sem telas).
import { act, renderHook, waitFor } from '@testing-library/react-native';

import { query } from '../src/api/catalogo';
import { ApiError } from '../src/api/client';
import type { Paginated } from '../src/api/tipos';
import { detalheSugestao, juntar, limpo, local, modalidade, nomeCurto, plural } from '../src/catalogo/formatar';
import { alternarValor } from '../src/catalogo/filtros';
import { usePaginacao } from '../src/hooks/usePaginacao';

const pagina = (itens: number[], total: number, page: number): Paginated<number> => ({
  data: itens,
  meta: { total, page, limit: 2, total_pages: Math.ceil(total / 2) },
});

describe('usePaginacao', () => {
  it('carrega a primeira página, depois anexa a próxima e para no fim', async () => {
    const buscar = jest.fn(async (p: number) => (p === 1 ? pagina([1, 2], 3, 1) : pagina([3], 3, 2)));
    const { result } = await renderHook(() => usePaginacao(buscar, []));
    await waitFor(() => expect(result.current.itens).toEqual([1, 2]));
    expect(result.current.temMais).toBe(true);

    await act(async () => {
      result.current.carregarMais();
      result.current.carregarMais(); // repetido enquanto a página 2 carrega: ignorado
    });
    await waitFor(() => expect(result.current.itens).toEqual([1, 2, 3]));
    expect(buscar).toHaveBeenCalledTimes(2);
    expect(result.current.temMais).toBe(false);

    await act(async () => result.current.carregarMais()); // no fim: não pede mais nada
    expect(buscar).toHaveBeenCalledTimes(2);
  });

  it('mudar os filtros recomeça da página 1 e descarta a resposta antiga', async () => {
    let resolverVelha: (v: Paginated<number>) => void = () => undefined;
    const buscar = jest.fn((filtro: string) =>
      filtro === 'velho'
        ? new Promise<Paginated<number>>((r) => (resolverVelha = r))
        : Promise.resolve(pagina([9], 1, 1)),
    );
    const { result, rerender } = await renderHook(({ f }: { f: string }) => usePaginacao(() => buscar(f), [f]), {
      initialProps: { f: 'velho' },
    });
    await rerender({ f: 'novo' });
    await waitFor(() => expect(result.current.itens).toEqual([9]));
    await act(async () => resolverVelha(pagina([1, 2], 2, 1))); // chega atrasada
    expect(result.current.itens).toEqual([9]);
  });

  it('erro ao carregar mais mantém os itens e permite tentar de novo', async () => {
    const buscar = jest
      .fn()
      .mockResolvedValueOnce(pagina([1, 2], 3, 1))
      .mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', 'Sem rede.'))
      .mockResolvedValueOnce(pagina([3], 3, 2));
    const { result } = await renderHook(() => usePaginacao(buscar, []));
    await waitFor(() => expect(result.current.itens).toEqual([1, 2]));
    await act(async () => result.current.carregarMais());
    await waitFor(() => expect(result.current.erro).toBe('Sem rede.'));
    expect(result.current.itens).toEqual([1, 2]);
    await act(async () => result.current.carregarMais()); // com erro, só o botão "tentar de novo" pede
    expect(buscar).toHaveBeenCalledTimes(2);
    await act(() => result.current.tentarMaisNovamente());
    expect(result.current.itens).toEqual([1, 2, 3]);
  });
});

describe('formatação do catálogo', () => {
  it('ignora vazios e o texto "null" gravado no banco', () => {
    expect(limpo(' null ')).toBeUndefined();
    expect(limpo('')).toBeUndefined();
    expect(local('null', 'null')).toBeUndefined();
    expect(local('Campinas', 'SP')).toBe('Campinas/SP');
    expect(local(null, 'SP')).toBe('SP');
    expect(juntar('Presencial', null, 'null', 'Bacharelado')).toBe('Presencial · Bacharelado');
    expect(detalheSugestao('null/null · Pública')).toBe('Pública');
    expect(detalheSugestao('Campinas/SP · Privada')).toBe('Campinas/SP · Privada');
  });

  it('rótulos e números', () => {
    expect(modalidade('ead')).toBe('EaD');
    expect(modalidade('semipresencial')).toBe('Semipresencial');
    expect(nomeCurto({ nome: 'Universidade de São Paulo', sigla: 'USP' })).toBe('USP');
    expect(nomeCurto({ nome: 'Faculdade X', sigla: '' })).toBe('Faculdade X');
    expect(plural(1, 'curso', 'cursos')).toBe('1 curso');
    expect(plural(2957, 'faculdade', 'faculdades')).toBe('2.957 faculdades');
    expect(alternarValor(['a'], 'b')).toEqual(['a', 'b']);
    expect(alternarValor(['a', 'b'], 'a')).toEqual(['b']);
  });

  it('query string: listas viram parâmetros repetidos e vazios são omitidos', () => {
    expect(query({ busca: 'são paulo', area: undefined, modalidade: ['ead', 'presencial'], page: 1 })).toBe(
      '?busca=s%C3%A3o%20paulo&modalidade=ead&modalidade=presencial&page=1',
    );
    expect(query({ busca: '' })).toBe('');
  });
});

describe('estabilidade dos hooks', () => {
  it('recarregar do usePaginacao é a mesma função entre renders (seguro em useFocusEffect)', async () => {
    const buscar = jest.fn(async () => pagina([1], 1, 1));
    const { result, rerender } = await renderHook(() => usePaginacao(buscar, []));
    await waitFor(() => expect(result.current.itens).toEqual([1]));
    const antes = result.current.recarregar;
    await rerender({});
    expect(result.current.recarregar).toBe(antes);
  });
});
