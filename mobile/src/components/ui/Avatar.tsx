import { Image, StyleSheet, Text, View } from 'react-native';

import { cores, dimensoes, familias } from '../../theme/tokens';

type Props = { nome?: string | null; url?: string | null; tamanho?: number };

// O Figma usa uma ilustração 3D de exemplo; aqui mostramos a foto do usuário
// (hoje só existe para contas Google) ou a inicial do nome.
export function Avatar({ nome, url, tamanho = dimensoes.avatar }: Props) {
  const forma = { width: tamanho, height: tamanho, borderRadius: tamanho / 2 };
  if (url) {
    return <Image source={{ uri: url }} style={forma} accessibilityIgnoresInvertColors accessible={false} />;
  }
  const inicial = (nome?.trim()[0] ?? '?').toUpperCase();
  return (
    <View style={[styles.circulo, forma]} accessible={false}>
      <Text style={[styles.inicial, { fontSize: tamanho * 0.42 }]}>{inicial}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  circulo: { backgroundColor: cores.laranjaClaro, alignItems: 'center', justifyContent: 'center' },
  inicial: { fontFamily: familias.interSemi, color: cores.branco },
});
