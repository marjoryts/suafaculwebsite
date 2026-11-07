import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Pressable, StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';

import { cores, dimensoes, espaco, raio, tipografia } from '../../theme/tokens';

type Props = Omit<TextInputProps, 'style'> & {
  /** Sem onChangeText vira um atalho: um botão que abre a tela de busca. */
  onPress?: () => void;
};

const PLACEHOLDER = 'Pesquise faculdades, cursos...';

// Busca do Figma: pílula cinza translúcida, borda #d9d9d9, lupa laranja à direita.
export function CampoBusca({ onPress, placeholder = PLACEHOLDER, ...resto }: Props) {
  const lupa = <MaterialIcons name="search" size={24} color={cores.laranja} />;

  if (onPress) {
    return (
      <Pressable
        accessibilityRole="search"
        accessibilityLabel={placeholder}
        onPress={onPress}
        style={({ pressed }) => [styles.pilula, pressed && { opacity: 0.8 }]}
      >
        <Text style={[styles.texto, styles.atalho]} numberOfLines={1}>
          {placeholder}
        </Text>
        {lupa}
      </Pressable>
    );
  }

  return (
    <View style={styles.pilula}>
      <TextInput
        accessibilityLabel={placeholder}
        placeholder={placeholder}
        placeholderTextColor={cores.roxoEscuro}
        returnKeyType="search"
        autoCorrect={false}
        style={[styles.texto, styles.entrada]}
        {...resto}
      />
      {lupa}
    </View>
  );
}

const styles = StyleSheet.create({
  pilula: {
    minHeight: dimensoes.alturaBusca,
    borderRadius: raio.pilula,
    borderWidth: 1,
    borderColor: cores.borda,
    backgroundColor: cores.campoBusca,
    paddingHorizontal: espaco.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.sm,
  },
  texto: { flex: 1, fontFamily: tipografia.corpo.fontFamily, fontSize: tipografia.corpo.fontSize, color: cores.roxoEscuro },
  atalho: { paddingVertical: espaco.smd },
  entrada: { paddingVertical: espaco.sm },
});
