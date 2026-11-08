// Login com Google no app: o ID token vira a MESMA sessão do login por senha.
// (O Google Sign-In nativo só existe em development build; aqui testamos o resto do fluxo.)
import { act, renderHook, waitFor } from '@testing-library/react-native';
import { ReactNode } from 'react';

import { ApiError } from '../src/api/client';
import { SessaoProvider, useSessao } from '../src/auth/SessaoProvider';
import { auth, tokens, usuarioAna } from '../test-utils/app';

jest.mock('../src/api/auth');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const SecureStore = require('expo-secure-store');

const envolver = ({ children }: { children: ReactNode }) => <SessaoProvider>{children}</SessaoProvider>;

beforeEach(() => {
  Object.values(auth).forEach((f) => typeof f === 'function' && (f as jest.Mock).mockReset());
  SecureStore.__limpar();
});

it('troca o ID token por sessão e guarda só o refresh token', async () => {
  auth.entrarComGoogle.mockResolvedValue({ data: { usuario: { ...usuarioAna, auth_provider: 'google' }, tokens: tokens(5) } });
  const { result } = await renderHook(() => useSessao(), { wrapper: envolver });
  await waitFor(() => expect(result.current.estado).toBe('anonimo'));

  await act(() => result.current.entrarComGoogle('id-token-do-google'));
  expect(auth.entrarComGoogle).toHaveBeenCalledWith('id-token-do-google');
  expect(result.current.estado).toBe('autenticado');
  expect(result.current.usuario?.auth_provider).toBe('google');
  expect(SecureStore.__conteudo()).toEqual({ 'suafacul.refresh_token': 'refresh-5' });
});

it('token recusado pelo servidor não abre sessão', async () => {
  auth.entrarComGoogle.mockRejectedValue(new ApiError(401, 'INVALID_GOOGLE_TOKEN', 'Token do Google inválido.'));
  const { result } = await renderHook(() => useSessao(), { wrapper: envolver });
  await waitFor(() => expect(result.current.estado).toBe('anonimo'));
  await act(async () => {
    await expect(result.current.entrarComGoogle('forjado')).rejects.toMatchObject({ code: 'INVALID_GOOGLE_TOKEN' });
  });
  expect(result.current.estado).toBe('anonimo');
  expect(SecureStore.__conteudo()).toEqual({});
});
