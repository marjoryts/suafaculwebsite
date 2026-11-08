// Perfil e painel do usuário logado (as regras de validação são do backend).
import { api } from './client';
import type { Painel, Resposta, Usuario } from './tipos';

export const meuPainel = () => api<Resposta<Painel>>('/me/dashboard', { autenticado: true });

export const atualizarPerfil = (dados: { nome_usuario: string; email: string }) =>
  api<Resposta<Usuario>>('/me', { metodo: 'PATCH', corpo: dados, autenticado: true });

/**
 * Trocar a senha exige a senha atual (exceto conta Google sem senha própria) e encerra
 * as sessões nos OUTROS aparelhos e no site (esta continua).
 */
export const alterarSenha = (password: string, password_confirm: string, password_atual?: string) =>
  api<Resposta<Usuario>>('/me', {
    metodo: 'PATCH',
    corpo: { password, password_confirm, ...(password_atual ? { password_atual } : {}) },
    autenticado: true,
  });

/** Pede a troca do e-mail: o código vai para o endereço NOVO (o atual vale até confirmar). */
export const pedirTrocaDeEmail = (email: string, password_atual?: string) =>
  api<Resposta<{ mensagem: string }>>('/me/email', {
    metodo: 'POST',
    corpo: { email, ...(password_atual ? { password_atual } : {}) },
    autenticado: true,
  });

export const confirmarTrocaDeEmail = (codigo: string) =>
  api<Resposta<Usuario>>('/me/email/confirmar', { metodo: 'POST', corpo: { codigo }, autenticado: true });
