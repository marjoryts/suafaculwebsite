// Endpoints de autenticação e perfil (somente os que existem em /api/v1).
import { api } from './client';
import type { Resposta, Sessao, Tokens, Usuario } from './tipos';

export const entrar = (email: string, password: string) =>
  api<Resposta<Sessao>>('/auth/login', { metodo: 'POST', corpo: { email, password } });

/** Troca o ID token do Google Sign-In por uma sessão (o servidor valida o token). */
export const entrarComGoogle = (id_token: string) =>
  api<Resposta<Sessao>>('/auth/google', { metodo: 'POST', corpo: { id_token } });

export const cadastrar = (nome_usuario: string, email: string, password: string) =>
  api<Resposta<Sessao>>('/auth/registrar', {
    metodo: 'POST',
    corpo: { nome_usuario, email, password },
  });

export const renovar = (refresh_token: string) =>
  api<Resposta<{ tokens: Tokens }>>('/auth/refresh', { metodo: 'POST', corpo: { refresh_token } });

export const sair = (refresh_token: string) =>
  api<void>('/auth/logout', { metodo: 'POST', corpo: { refresh_token } });

export const meuPerfil = () => api<Resposta<Usuario>>('/me', { autenticado: true });
