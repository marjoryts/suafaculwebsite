// Abre as rotas REAIS de src/app com uma sessão simulada. O teste precisa chamar
// jest.mock('../src/api/auth') (e catálogo/favoritos) antes de usar estes helpers.
import { renderRouter } from 'expo-router/testing-library';
import path from 'path';

import * as authReal from '../src/api/auth';
import type { Tokens, Usuario } from '../src/api/tipos';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const SecureStore = require('expo-secure-store');

export const auth = authReal as jest.Mocked<typeof authReal>;
export const APP_DIR = path.join(__dirname, '..', 'src', 'app');
export const CHAVE_REFRESH = 'suafacul.refresh_token';

export const usuarioAna: Usuario = {
  id: 1,
  nome_usuario: 'ana',
  email: 'ana@x.com',
  tipo: 'aluno',
  avatar_url: null,
  auth_provider: 'local',
  created_at: null,
  email_verificado: true,
  senha_definida: true,
};

export const tokens = (n: number): Tokens => ({
  token_type: 'Bearer',
  access_token: `access-${n}`,
  expires_in: 900,
  refresh_token: `refresh-${n}`,
  refresh_expires_in: 2592000,
});

export async function comSessaoGuardada() {
  await SecureStore.setItemAsync(CHAVE_REFRESH, 'refresh-guardado');
  auth.renovar.mockResolvedValue({ data: { tokens: tokens(2) } });
  auth.meuPerfil.mockResolvedValue({ data: usuarioAna });
}

/**
 * renderRouter devolve uma Promise com getPathname() etc. anexados. Devolvemos essa
 * referência dentro de um objeto: devolvê-la direto de uma função async faria o await
 * "abrir" a Promise e perder esses métodos (usados por toHavePathname).
 */
export async function abrirApp(initialUrl = '/') {
  const vista = renderRouter(APP_DIR, { initialUrl });
  await vista;
  return { vista };
}
