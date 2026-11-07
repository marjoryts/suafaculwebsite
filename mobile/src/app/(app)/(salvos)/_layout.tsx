import { Stack } from 'expo-router';

import { opcoesDaPilha } from '../../../theme/navegacao';

// Tela inicial da pilha ao tocar na aba (sem isso o Expo Router pode abrir outra rota da pasta).
export const unstable_settings = { initialRouteName: 'salvos' };

export default function Layout() {
  return <Stack screenOptions={opcoesDaPilha} />;
}
