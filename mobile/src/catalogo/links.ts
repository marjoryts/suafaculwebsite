import { Alert, Linking } from 'react-native';

import { limpo } from './formatar';

async function abrir(url: string) {
  try {
    await Linking.openURL(url);
  } catch {
    Alert.alert('Não foi possível abrir', 'Nenhum aplicativo do aparelho conseguiu abrir este link.');
  }
}

/** Site da instituição (o e-MEC às vezes grava sem "http"). */
export function abrirSite(url: string) {
  return abrir(/^https?:\/\//i.test(url) ? url : `https://${url}`);
}

/** Endereço no app de mapas (busca pelo texto; o banco não tem coordenadas). */
export function abrirMapa(...partes: (string | null | undefined)[]) {
  const texto = partes.map((p) => limpo(p)).filter(Boolean).join(', ');
  return abrir(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(texto)}`);
}

export const ligar = (telefone: string) => abrir(`tel:${telefone.replace(/[^\d+]/g, '')}`);

export const enviarEmail = (email: string) => abrir(`mailto:${email}`);
