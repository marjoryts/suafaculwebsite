import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { StyleSheet, Text, View } from 'react-native';

import { cores, espaco, tipografia } from '../../theme/tokens';
import { Botao } from './Botao';
import { Logo } from './Logo';

// Mostrada quando o app abre sem rede: a sessão guardada é mantida (não desloga).
export function TelaSemConexao({ onTentarNovamente }: { onTentarNovamente: () => void }) {
  return (
    <View style={styles.raiz}>
      <Logo />
      <MaterialIcons name="wifi-off" size={48} color={cores.laranja} />
      <Text style={[tipografia.titulo, styles.titulo]} accessibilityRole="header">
        Sem conexão
      </Text>
      <Text style={styles.texto}>Não foi possível falar com o servidor. Verifique sua internet.</Text>
      <View style={styles.botao}>
        <Botao titulo="Tentar novamente" onPress={onTentarNovamente} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  raiz: {
    flex: 1,
    backgroundColor: cores.fundo,
    alignItems: 'center',
    justifyContent: 'center',
    padding: espaco.lg,
    gap: espaco.md,
  },
  titulo: { color: cores.roxoEscuro },
  texto: { ...tipografia.corpo, color: cores.textoSuave, textAlign: 'center' },
  botao: { alignSelf: 'stretch', marginTop: espaco.sm },
});
