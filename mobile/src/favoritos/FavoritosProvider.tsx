import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import * as api from '../api/favoritos';
import type { Favorito, TipoFavorito } from '../api/tipos';
import { mensagemDeErro } from '../hooks/useConsulta';

type Contexto = {
  /** Favoritos do servidor (mais recentes primeiro), já com as mudanças locais. */
  favoritos: Favorito[];
  carregando: boolean;
  erro: string | null;
  ehFavorito(tipo: TipoFavorito, id: number): boolean;
  /** Marca/desmarca na hora e confirma no servidor; desfaz e rejeita se falhar. */
  alternar(tipo: TipoFavorito, id: number, nome: string): Promise<void>;
  recarregar(): Promise<void>;
};

const FavoritosContexto = createContext<Contexto | null>(null);

const mesmo = (f: Favorito, tipo: TipoFavorito, id: number) => f.tipo === tipo && f.item_id === id;

// Fonte única dos favoritos no app: o coração de qualquer tela lê daqui, então
// marcar em um lugar atualiza os outros. A regra (o que pode ser favoritado,
// duplicidade) continua no backend.
export function FavoritosProvider({ children }: { children: ReactNode }) {
  const [favoritos, setFavoritos] = useState<Favorito[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const emAndamento = useRef(new Set<string>());

  const recarregar = useCallback(async () => {
    setCarregando(true);
    try {
      const { data } = await api.listarFavoritos();
      setFavoritos(data);
      setErro(null);
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void recarregar();
  }, [recarregar]);

  const ehFavorito = useCallback(
    (tipo: TipoFavorito, id: number) => favoritos.some((f) => mesmo(f, tipo, id)),
    [favoritos],
  );

  const alternar = useCallback(
    async (tipo: TipoFavorito, id: number, nome: string) => {
      const chave = `${tipo}:${id}`;
      if (emAndamento.current.has(chave)) return; // ignora toques repetidos
      emAndamento.current.add(chave);
      const original = favoritos.find((f) => mesmo(f, tipo, id));
      const marcar = !original;
      const semEle = (lista: Favorito[]) => lista.filter((f) => !mesmo(f, tipo, id));
      setFavoritos((atual) =>
        marcar ? [{ tipo, item_id: id, nome_item: nome, created_at: null }, ...semEle(atual)] : semEle(atual),
      );
      try {
        if (marcar) {
          const { data } = await api.favoritar(tipo, id);
          setFavoritos((atual) => atual.map((f) => (mesmo(f, tipo, id) ? data : f)));
        } else {
          await api.desfavoritar(tipo, id);
        }
      } catch (e) {
        // Desfaz só este item (outros podem ter mudado enquanto isso).
        setFavoritos((atual) => (original ? [original, ...semEle(atual)] : semEle(atual)));
        throw new Error(mensagemDeErro(e));
      } finally {
        emAndamento.current.delete(chave);
      }
    },
    [favoritos],
  );

  const valor = useMemo(
    () => ({ favoritos, carregando, erro, ehFavorito, alternar, recarregar }),
    [favoritos, carregando, erro, ehFavorito, alternar, recarregar],
  );
  return <FavoritosContexto.Provider value={valor}>{children}</FavoritosContexto.Provider>;
}

export function useFavoritos(): Contexto {
  const contexto = useContext(FavoritosContexto);
  if (!contexto) throw new Error('useFavoritos deve ser usado dentro de <FavoritosProvider>.');
  return contexto;
}
