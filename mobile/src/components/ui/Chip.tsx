import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { ComponentProps } from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';

import { cores, espaco, raio, tipografia } from '../../theme/tokens';

type Props = {
  titulo: string;
  onPress?: () => void;
  icone?: ComponentProps<typeof MaterialIcons>['name'];
  /** Selecionado = laranja preenchido; não selecionado = contorno laranja (as duas formas do Figma). */
  selecionado?: boolean;
};

// Chip do Figma (M3 Button XSmall Filled): pílula laranja, ícone 20 e Roboto Medium 14 brancos.
export function Chip({ titulo, onPress, icone, selecionado = true }: Props) {
  const cor = selecionado ? cores.branco : cores.roxoEscuro;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={titulo}
      accessibilityState={{ selected: selecionado }}
      disabled={!onPress}
      onPress={onPress}
      hitSlop={{ top: espaco.sm, bottom: espaco.sm }}
      style={({ pressed }) => [
        styles.base,
        selecionado ? styles.selecionado : styles.contorno,
        pressed && { opacity: 0.8 },
      ]}
    >
      {!!icone && <MaterialIcons name={icone} size={20} color={cor} />}
      <Text style={[tipografia.chip, styles.texto, { color: cor }]} numberOfLines={1}>
        {titulo}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.xs,
    paddingHorizontal: espaco.smd,
    paddingVertical: 6,
    minHeight: 32,
    borderRadius: raio.pilula,
    alignSelf: 'flex-start',
    maxWidth: 260,
  },
  texto: { flexShrink: 1 },
  selecionado: { backgroundColor: cores.laranja },
  contorno: { borderWidth: 1, borderColor: cores.laranja },
});
