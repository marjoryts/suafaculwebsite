// Login com Google no app (biblioteca nativa @react-native-google-signin/google-signin).
//
// - Só funciona num DEVELOPMENT BUILD ou build de produção (o Expo Go não traz o módulo
//   nativo). No Expo Go o botão não aparece.
// - O app só obtém o ID token do Google; quem valida (assinatura, emissor, audiência,
//   validade, e-mail verificado) e decide vincular/criar a conta é o backend
//   (POST /api/v1/auth/google). Nenhum segredo fica no app.
// - EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID: o ID do cliente OAuth "Web" (o mesmo GOOGLE_CLIENT_ID
//   do servidor). É público por natureza; o token emitido terá essa audiência.
import Constants, { ExecutionEnvironment } from 'expo-constants';

const WEB_CLIENT_ID = process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID?.trim() ?? '';

export type ResultadoGoogle = { tipo: 'sucesso'; idToken: string } | { tipo: 'cancelado' };

/** Erro com mensagem pronta para a tela. */
export class ErroGoogle extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ErroGoogle';
  }
}

type Modulo = typeof import('@react-native-google-signin/google-signin');
let modulo: Modulo | null | undefined;
let configurado = false;

function carregar(): Modulo | null {
  if (modulo !== undefined) return modulo;
  try {
    // require tardio: no Expo Go o módulo nativo não existe e o import quebraria o app.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    modulo = require('@react-native-google-signin/google-signin') as Modulo;
  } catch {
    modulo = null;
  }
  return modulo;
}

/** O botão do Google só aparece quando o login pode de fato acontecer. */
export function googleDisponivel(): boolean {
  if (!WEB_CLIENT_ID) return false;
  if (Constants.executionEnvironment === ExecutionEnvironment.StoreClient) return false; // Expo Go
  return carregar() !== null;
}

export async function obterIdTokenDoGoogle(): Promise<ResultadoGoogle> {
  const lib = carregar();
  if (!lib || !WEB_CLIENT_ID) throw new ErroGoogle('Login com Google indisponível nesta versão do app.');
  const { GoogleSignin, isErrorWithCode, isSuccessResponse, statusCodes } = lib;

  if (!configurado) {
    GoogleSignin.configure({ webClientId: WEB_CLIENT_ID });
    configurado = true;
  }
  try {
    await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
    // Sempre deixa escolher a conta (sem reaproveitar a última escolha em silêncio).
    await GoogleSignin.signOut().catch(() => undefined);
    const resposta = await GoogleSignin.signIn();
    if (!isSuccessResponse(resposta)) return { tipo: 'cancelado' };
    const idToken = resposta.data.idToken;
    if (!idToken) throw new ErroGoogle('O Google não devolveu a credencial. Tente novamente.');
    return { tipo: 'sucesso', idToken };
  } catch (e) {
    if (e instanceof ErroGoogle) throw e;
    if (isErrorWithCode(e)) {
      if (e.code === statusCodes.SIGN_IN_CANCELLED) return { tipo: 'cancelado' };
      if (e.code === statusCodes.IN_PROGRESS) throw new ErroGoogle('O login com Google já está em andamento.');
      if (e.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) {
        throw new ErroGoogle('O Google Play Services não está disponível ou precisa ser atualizado.');
      }
      // Código 7 (NETWORK_ERROR) do Google Sign-In no Android.
      if (String(e.code) === '7') throw new ErroGoogle('Sem conexão com o Google. Verifique sua internet.');
    }
    throw new ErroGoogle('Não foi possível entrar com o Google. Tente novamente.');
  }
}
