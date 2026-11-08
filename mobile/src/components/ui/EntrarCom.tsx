import { Image, Pressable, StyleSheet, Text, View } from 'react-native';

import { cores, espaco, tipografia } from '../../theme/tokens';

const EMAIL = require('../../../assets/figma/email.png');
const GOOGLE = require('../../../assets/figma/google.png');

// Bloco "Entrar com" do Figma: E-mail (o formulário acima) e Google.
// O login com Google ainda não existe no backend para o app: aparece desabilitado.
export function EntrarCom({ sobreCor }: { sobreCor?: boolean }) {
  const cor = sobreCor ? cores.branco : cores.texto;
  return (
    <View style={styles.linha}>
      <View style={styles.opcao} accessible accessibilityLabel="E-mail (formulário acima)">
        <Image source={EMAIL} style={styles.icone} />
        <Text style={[tipografia.legenda, { color: cor }]}>E-mail</Text>
      </View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Entrar com Google (em breve)"
        accessibilityState={{ disabled: true }}
        disabled
        style={[styles.opcao, styles.inativo]}
      >
        <Image source={GOOGLE} style={styles.icone} />
        <Text style={[tipografia.legenda, { color: cor }]}>Google</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  linha: { flexDirection: 'row', justifyContent: 'center', gap: 40 },
  opcao: { alignItems: 'center', gap: espaco.xxs },
  icone: { width: 47, height: 47 },
  inativo: { opacity: 0.5 },
});
