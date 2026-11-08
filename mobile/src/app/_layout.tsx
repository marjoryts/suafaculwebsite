// Cada peso pelo seu subcaminho: o índice dos pacotes incluiria todos os pesos no app.
import { DarkerGrotesque_400Regular } from '@expo-google-fonts/darker-grotesque/400Regular';
import { Inter_400Regular } from '@expo-google-fonts/inter/400Regular';
import { Inter_500Medium } from '@expo-google-fonts/inter/500Medium';
import { Inter_600SemiBold } from '@expo-google-fonts/inter/600SemiBold';
import { Inter_700Bold } from '@expo-google-fonts/inter/700Bold';
import { Inter_800ExtraBold } from '@expo-google-fonts/inter/800ExtraBold';
import { Roboto_500Medium } from '@expo-google-fonts/roboto/500Medium';
import { Roboto_600SemiBold } from '@expo-google-fonts/roboto/600SemiBold';
import { useFonts } from 'expo-font';
import { SplashScreen, Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { SessaoProvider, useSessao } from '../auth/SessaoProvider';
import { TelaSemConexao } from '../components/ui/TelaSemConexao';
import { cores } from '../theme/tokens';

// A splash nativa fica visível enquanto a sessão é restaurada e as fontes carregam.
void SplashScreen.preventAutoHideAsync();

export default function RaizLayout() {
  return (
    <SessaoProvider>
      <StatusBar style="dark" />
      <Navegacao />
    </SessaoProvider>
  );
}

function Navegacao() {
  const { estado, tentarNovamente } = useSessao();
  // Fontes do Figma (Inter, Roboto e Darker Grotesque). Se falharem, o app segue com a
  // fonte do sistema em vez de ficar preso na splash.
  const [fontesProntas, erroFontes] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
    Inter_800ExtraBold,
    Roboto_500Medium,
    Roboto_600SemiBold,
    DarkerGrotesque_400Regular,
  });
  const pronto = estado !== 'carregando' && (fontesProntas || !!erroFontes);

  useEffect(() => {
    if (pronto) void SplashScreen.hideAsync();
  }, [pronto]);

  if (!pronto) return null;
  if (estado === 'sem-conexao') return <TelaSemConexao onTentarNovamente={tentarNovamente} />;

  // Login obrigatório: (auth) só para quem não tem sessão, (app) só para quem tem.
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: cores.fundo } }}>
      <Stack.Protected guard={estado === 'autenticado'}>
        <Stack.Screen name="(app)" />
      </Stack.Protected>
      <Stack.Protected guard={estado === 'anonimo'}>
        <Stack.Screen name="(auth)" />
      </Stack.Protected>
    </Stack>
  );
}
