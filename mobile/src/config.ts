// Endereço do backend Flask.
//
// 1) EXPO_PUBLIC_API_URL (mobile/.env.local), se definido: vale sempre (ex.: produção).
// 2) Em desenvolvimento, sem a variável: o mesmo computador que serve o app pelo Expo,
//    na porta 5000. Assim trocar de rede Wi-Fi não exige editar o .env.local — o IP do
//    Expo (hostUri) já é o IP do computador visto pelo celular.
// 3) Último recurso: localhost (só funciona no emulador/simulador do próprio computador).
import Constants from 'expo-constants';

const PORTA_FLASK = 5000;

function computadorDoExpo(): string | undefined {
  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  return host ? `http://${host}:${PORTA_FLASK}` : undefined;
}

const definido = process.env.EXPO_PUBLIC_API_URL?.trim();

export const API_URL = (
  definido || (__DEV__ ? computadorDoExpo() : undefined) || `http://localhost:${PORTA_FLASK}`
).replace(/\/+$/, '');

// Contrato oficial do app: toda a lógica de negócio fica no backend.
export const API_V1_URL = `${API_URL}/api/v1`;
