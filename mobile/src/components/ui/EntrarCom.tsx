import { useState } from 'react';
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { ApiError } from '../../api/client';
import { useSessao } from '../../auth/SessaoProvider';
import { ErroGoogle, googleDisponivel, obterIdTokenDoGoogle } from '../../auth/googleNativo';
import { cores, espaco, raio, tipografia } from '../../theme/tokens';

const EMAIL = require('../../../assets/figma/email.png');
const GOOGLE = require('../../../assets/figma/google.png');

// Bloco "Entrar com" do Figma: E-mail (o formulário acima) e Google.
// O Google só aparece quando pode funcionar (development build/produção com o
// EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID configurado); no Expo Go ele fica oculto.
export function EntrarCom({ sobreCor }: { sobreCor?: boolean }) {
  const { entrarComGoogle } = useSessao();
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const cor = sobreCor ? cores.branco : cores.texto;
  const comGoogle = googleDisponivel();

  async function entrar() {
    setErro(null);
    setCarregando(true);
    try {
      const resultado = await obterIdTokenDoGoogle();
      if (resultado.tipo === 'cancelado') {
        setCarregando(false);
        return; // o usuário fechou a janela do Google: nada a mostrar
      }
      await entrarComGoogle(resultado.idToken);
      // A navegação é do porteiro da raiz (a sessão passou a existir).
    } catch (e) {
      setErro(e instanceof ErroGoogle || e instanceof ApiError ? e.message : 'Não foi possível entrar com o Google.');
      setCarregando(false);
    }
  }

  return (
    <View style={styles.bloco}>
      <View style={styles.linha}>
        <View style={styles.opcao} accessible accessibilityLabel="E-mail (formulário acima)">
          <Image source={EMAIL} style={styles.icone} />
          <Text style={[tipografia.legenda, { color: cor }]}>E-mail</Text>
        </View>
        {comGoogle && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Continuar com Google"
            accessibilityState={{ busy: carregando, disabled: carregando }}
            disabled={carregando}
            onPress={entrar}
            style={({ pressed }) => [styles.opcao, (pressed || carregando) && styles.pressionado]}
          >
            {carregando ? (
              <ActivityIndicator style={styles.icone} color={sobreCor ? cores.branco : cores.roxo} />
            ) : (
              <Image source={GOOGLE} style={styles.icone} />
            )}
            <Text style={[tipografia.legenda, { color: cor }]}>Google</Text>
          </Pressable>
        )}
      </View>
      {!!erro && (
        <Text style={[styles.erro, sobreCor && styles.erroSobreCor]} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  bloco: { gap: espaco.sm },
  linha: { flexDirection: 'row', justifyContent: 'center', gap: 40 },
  opcao: { alignItems: 'center', gap: espaco.xxs },
  icone: { width: 47, height: 47 },
  pressionado: { opacity: 0.6 },
  erro: { ...tipografia.corpo, color: cores.erro, textAlign: 'center' },
  erroSobreCor: {
    ...tipografia.rotulo,
    color: cores.branco,
    backgroundColor: cores.erro,
    borderRadius: raio.campo,
    padding: espaco.smd,
  },
});
