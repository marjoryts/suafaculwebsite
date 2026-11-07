import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { ComponentProps } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { cores, dimensoes, espaco, raio, tipografia } from '../../theme/tokens';

type Props = {
  icone: ComponentProps<typeof MaterialIcons>['name'];
  texto: string;
  /** Torna o item tocável (ex.: abrir o site ou o mapa). */
  onPress?: () => void;
  rotuloAcessivel?: string;
};

// Item de informação do Figma "Cursos": quadrado roxo-escuro de 40 (cantos 10) com
// ícone branco e texto Inter Medium 14 cinza.
export function InfoItem({ icone, texto, onPress, rotuloAcessivel }: Props) {
  const conteudo = (
    <>
      <View style={styles.icone}>
        <MaterialIcons name={icone} size={24} color={cores.branco} />
      </View>
      <Text style={[tipografia.info, styles.texto, !!onPress && styles.link]}>{texto}</Text>
    </>
  );
  if (!onPress) return <View style={styles.linha}>{conteudo}</View>;
  return (
    <Pressable
      accessibilityRole="link"
      accessibilityLabel={rotuloAcessivel ?? texto}
      onPress={onPress}
      style={({ pressed }) => [styles.linha, pressed && { opacity: 0.7 }]}
    >
      {conteudo}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  linha: { flexDirection: 'row', alignItems: 'center', gap: espaco.smd, minHeight: dimensoes.areaToque },
  icone: {
    width: dimensoes.iconeInfo,
    height: dimensoes.iconeInfo,
    borderRadius: raio.icone,
    backgroundColor: cores.roxoEscuro,
    alignItems: 'center',
    justifyContent: 'center',
  },
  texto: { flex: 1, color: cores.textoSuave },
  link: { color: cores.roxo, textDecorationLine: 'underline' },
});
