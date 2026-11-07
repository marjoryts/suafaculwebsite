// Favoritos do usuário logado (exigem o Bearer).
import { api } from './client';
import type { Favorito, Resposta, TipoFavorito } from './tipos';

export const listarFavoritos = () => api<Resposta<Favorito[]>>('/favoritos', { autenticado: true });

/** Idempotente no servidor: favoritar duas vezes não duplica. */
export const favoritar = (tipo: TipoFavorito, id: number) =>
  api<Resposta<Favorito>>(`/favoritos/${tipo}/${id}`, { metodo: 'PUT', autenticado: true });

export const desfavoritar = (tipo: TipoFavorito, id: number) =>
  api<void>(`/favoritos/${tipo}/${id}`, { metodo: 'DELETE', autenticado: true });
