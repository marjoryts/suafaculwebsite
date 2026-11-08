import { useRouter } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import { useEffect } from 'react';

import { useSessao } from '../../auth/SessaoProvider';
import { BarraAbas } from '../../components/ui/BarraAbas';
import { DentroDasAbas } from '../../components/ui/Tela';
import { FavoritosProvider } from '../../favoritos/FavoritosProvider';

// Abas principais: SOMENTE Explorar, Salvos e Perfil. Cursos, Faculdades,
// Vestibulares e Teste vocacional ficam dentro de Explorar.
export default function AppLayout() {
  const router = useRouter();
  const { verificacaoPendente, verificacaoAberta } = useSessao();

  // Logo após o cadastro: abre a tela do código enviado ao e-mail.
  useEffect(() => {
    if (!verificacaoPendente) return;
    verificacaoAberta();
    router.push('/verificar-email?enviado=1');
  }, [verificacaoPendente, verificacaoAberta, router]);

  return (
    <FavoritosProvider>
      <DentroDasAbas.Provider value={true}>
        <Tabs screenOptions={{ headerShown: false }} tabBar={(props) => <BarraAbas {...props} />}>
          <Tabs.Screen name="(explorar)" options={{ title: 'Explorar' }} />
          <Tabs.Screen name="(salvos)" options={{ title: 'Salvos' }} />
          <Tabs.Screen name="(perfil)" options={{ title: 'Perfil' }} />
        </Tabs>
      </DentroDasAbas.Provider>
    </FavoritosProvider>
  );
}
