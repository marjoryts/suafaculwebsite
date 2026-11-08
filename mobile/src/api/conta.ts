// Verificação de e-mail e recuperação de senha (/api/v1/auth/...). As regras (validade,
// tentativas, intervalo de reenvio) são do backend; o app só mostra as mensagens.
import { api, ApiError } from './client';
import type { Resposta, Usuario } from './tipos';

type Mensagem = Resposta<{ mensagem: string }>;

/** (Re)envia o código de verificação. Resposta genérica: não diz se a conta existe. */
export const enviarCodigoDeVerificacao = (email: string) =>
  api<Mensagem>('/auth/verificacao/enviar', { metodo: 'POST', corpo: { email } });

export const confirmarEmail = (email: string, codigo: string) =>
  api<Resposta<{ usuario: Usuario }>>('/auth/verificacao/confirmar', { metodo: 'POST', corpo: { email, codigo } });

/** Pede o código de recuperação de senha. Resposta genérica. */
export const solicitarRecuperacao = (email: string) =>
  api<Mensagem>('/auth/recuperacao/solicitar', { metodo: 'POST', corpo: { email } });

/** Confere o código sem gastá-lo (libera o passo da nova senha). */
export const validarCodigoDeRecuperacao = (email: string, codigo: string) =>
  api<Resposta<{ valido: boolean }>>('/auth/recuperacao/validar', { metodo: 'POST', corpo: { email, codigo } });

/** Define a nova senha; o servidor encerra todas as sessões da conta. */
export const redefinirSenha = (email: string, codigo: string, password: string, password_confirm: string) =>
  api<Mensagem>('/auth/recuperacao/redefinir', {
    metodo: 'POST',
    corpo: { email, codigo, password, password_confirm },
  });

/** Segundos que o servidor pediu para esperar (429 com details.retry_after), ou 0. */
export function segundosParaTentarDeNovo(e: unknown): number {
  if (!(e instanceof ApiError) || e.status !== 429) return 0;
  const valor = Number(e.details?.retry_after);
  return Number.isFinite(valor) && valor > 0 ? valor : 0;
}

/** O código não serve mais (inválido, expirado ou sem tentativas): é preciso pedir outro. */
export const codigoPerdido = (e: unknown) =>
  e instanceof ApiError && (e.code === 'CODE_EXPIRED' || e.code === 'TOO_MANY_ATTEMPTS');

/** Mensagem do servidor + quantas tentativas restam (INVALID_CODE). */
export function mensagemDoCodigo(e: unknown): string {
  if (!(e instanceof ApiError)) return 'Não foi possível concluir. Tente novamente.';
  const restantes = e.details?.tentativas_restantes;
  return typeof restantes === 'number' ? `${e.message} Restam ${restantes} tentativa(s).` : e.message;
}
