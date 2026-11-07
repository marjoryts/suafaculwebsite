import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { ComponentProps } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { cores, dimensoes, espaco, raio, tipografia } from '../../theme/tokens';

type Props = {
  titulo: string;
  icone: ComponentProps<typeof MaterialIcons>['name'];
  onPress: () => void;
  /** "Sair" usa o círculo laranja, como no Figma. */
  destaque?: boolean;
  carregando?: boolean;
};

// Linha de "Configurações" do Perfil no Figma: círculo roxo de 50 com ícone branco,
// texto Inter SemiBold 22 roxo-escuro e seta à direita.
export function OpcaoMenu({ titulo, icone, onPress, destaque, carregando }: Props) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={titulo}
      accessibilityState={{ busy: !!carregando, disabled: !!carregando }}
      disabled={carregando}
      onPress={onPress}
      style={({ pressed }) => [styles.linha, (pressed || carregando) && { opacity: 0.6 }]}
    >
      <View style={[styles.circulo, { backgroundColor: destaque ? cores.laranja : cores.roxo }]}>
        <MaterialIcons name={icone} size={28} color={cores.branco} />
      </View>
      <Text style={[tipografia.opcao, styles.titulo]} numberOfLines={1}>
        {titulo}
      </Text>
      <MaterialIcons name="chevron-right" size={30} color={cores.textoSuave} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  linha: { flexDirection: 'row', alignItems: 'center', gap: espaco.md, minHeight: dimensoes.iconeOpcao },
  circulo: {
    width: dimensoes.iconeOpcao,
    height: dimensoes.iconeOpcao,
    borderRadius: raio.pilula,
    alignItems: 'center',
    justifyContent: 'center',
  },
  titulo: { flex: 1, color: cores.roxoEscuro },
});
