// Guarda SOMENTE o refresh token no armazenamento seguro do aparelho
// (Keychain no iOS, Keystore no Android). O access token vive só na memória:
// dura 15 min e é refeito a partir do refresh token ao abrir o app.
import * as SecureStore from 'expo-secure-store';

const CHAVE = 'suafacul.refresh_token';

export type TokenStorage = {
  ler(): Promise<string | null>;
  gravar(refreshToken: string): Promise<void>;
  apagar(): Promise<void>;
};

export const tokenStorage: TokenStorage = {
  ler: () => SecureStore.getItemAsync(CHAVE),
  gravar: (refreshToken) => SecureStore.setItemAsync(CHAVE, refreshToken),
  apagar: () => SecureStore.deleteItemAsync(CHAVE),
};
