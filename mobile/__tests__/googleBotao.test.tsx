// Botão "Continuar com Google" (o módulo nativo é simulado: só existe em development build).
import { userEvent } from '@testing-library/react-native';
import { screen, waitFor } from 'expo-router/testing-library';

import { ApiError } from '../src/api/client';
import { abrirApp, auth, tokens, usuarioAna } from '../test-utils/app';
import { prepararApiSimulada } from '../test-utils/apiSimulada';

jest.mock('../src/api/auth');
jest.mock('../src/api/catalogo');
jest.mock('../src/api/favoritos');
jest.mock('../src/api/testeVocacional');
jest.mock('../src/api/perfil');
jest.mock('../src/auth/googleNativo', () => {
  const real = jest.requireActual('../src/auth/googleNativo');
  return { ...real, googleDisponivel: jest.fn(() => true), obterIdTokenDoGoogle: jest.fn() };
});
// eslint-disable-next-line @typescript-eslint/no-require-imports
const google = require('../src/auth/googleNativo') as jest.Mocked<typeof import('../src/auth/googleNativo')>;
// eslint-disable-next-line @typescript-eslint/no-require-imports
const SecureStore = require('expo-secure-store');

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let vista: any;

beforeEach(() => {
  Object.values(auth).forEach((f) => typeof f === 'function' && (f as jest.Mock).mockReset());
  google.obterIdTokenDoGoogle.mockReset();
  SecureStore.__limpar();
  prepararApiSimulada();
});

async function tocarNoGoogle() {
  ({ vista } = await abrirApp('/'));
  const user = userEvent.setup();
  await user.press(await screen.findByRole('button', { name: 'Continuar com Google' }));
}

it('sucesso: o ID token vai para o backend e a sessão abre', async () => {
  google.obterIdTokenDoGoogle.mockResolvedValue({ tipo: 'sucesso', idToken: 'id-token-simulado' });
  auth.entrarComGoogle.mockResolvedValue({ data: { usuario: { ...usuarioAna, auth_provider: 'google' }, tokens: tokens(7) } });
  await tocarNoGoogle();
  await waitFor(() => expect(vista).toHavePathname('/'));
  expect(auth.entrarComGoogle).toHaveBeenCalledWith('id-token-simulado');
  expect(SecureStore.__conteudo()).toEqual({ 'suafacul.refresh_token': 'refresh-7' });
});

it('cancelado: nenhuma chamada ao backend e nenhuma mensagem de erro', async () => {
  google.obterIdTokenDoGoogle.mockResolvedValue({ tipo: 'cancelado' });
  await tocarNoGoogle();
  await waitFor(() => expect(screen.getByRole('button', { name: 'Continuar com Google' })).toBeEnabled());
  expect(auth.entrarComGoogle).not.toHaveBeenCalled();
  expect(vista).toHavePathname('/login');
});

it('sem internet / falha do Google: mostra a mensagem e continua no login', async () => {
  google.obterIdTokenDoGoogle.mockRejectedValue(new google.ErroGoogle('Sem conexão com o Google. Verifique sua internet.'));
  await tocarNoGoogle();
  expect(await screen.findByText('Sem conexão com o Google. Verifique sua internet.')).toBeTruthy();
  expect(auth.entrarComGoogle).not.toHaveBeenCalled();
});

it('token recusado pelo servidor: mostra a mensagem do backend e não abre sessão', async () => {
  google.obterIdTokenDoGoogle.mockResolvedValue({ tipo: 'sucesso', idToken: 'forjado' });
  auth.entrarComGoogle.mockRejectedValue(new ApiError(401, 'INVALID_GOOGLE_TOKEN', 'Não foi possível validar sua conta Google.'));
  await tocarNoGoogle();
  expect(await screen.findByText('Não foi possível validar sua conta Google.')).toBeTruthy();
  expect(vista).toHavePathname('/login');
  expect(SecureStore.__conteudo()).toEqual({});
});
