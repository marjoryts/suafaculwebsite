// Perfil e painel do usuário logado (as regras de validação são do backend).
import { api } from './client';
import type { Painel, Resposta, Usuario } from './tipos';

export const meuPainel = () => api<Resposta<Painel>>('/me/dashboard', { autenticado: true });

export const atualizarPerfil = (dados: { nome_usuario: string; email: string }) =>
  api<Resposta<Usuario>>('/me', { metodo: 'PATCH', corpo: dados, autenticado: true });

/** Trocar a senha encerra as sessões do app nos OUTROS aparelhos (esta continua). */
export const alterarSenha = (password: string, password_confirm: string) =>
  api<Resposta<Usuario>>('/me', { metodo: 'PATCH', corpo: { password, password_confirm }, autenticado: true });
