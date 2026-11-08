import { Stack } from 'expo-router';

// Sem esta âncora a primeira tela seria a primeira em ordem alfabética (cadastro).
export const unstable_settings = { anchor: 'login' };

export default function AuthLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
