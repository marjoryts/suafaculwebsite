import { ScrollView, StyleSheet, Text, View } from 'react-native';

import type { Opcao } from '../../catalogo/filtros';
import { cores, espaco, tipografia } from '../../theme/tokens';
import { Chip } from '../ui/Chip';

type Props = {
  rotulo: string;
  opcoes: Opcao[];
  selecionados: string[];
  onAlternar: (valor: string) => void;
};

// Uma linha de chips de filtro com rolagem horizontal (selecionado = laranja preenchido).
export function GrupoFiltro({ rotulo, opcoes, selecionados, onAlternar }: Props) {
  return (
    <View style={styles.grupo} accessibilityLabel={rotulo}>
      <Text style={styles.rotulo}>{rotulo}</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.rolagem}
        contentContainerStyle={styles.chips}
        keyboardShouldPersistTaps="handled"
      >
        {opcoes.map((o) => (
          <Chip
            key={o.valor}
            titulo={o.rotulo}
            selecionado={selecionados.includes(o.valor)}
            onPress={() => onAlternar(o.valor)}
          />
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  grupo: { gap: espaco.xs },
  rotulo: { ...tipografia.legenda, color: cores.roxoEscuro },
  rolagem: { marginHorizontal: -espaco.lg },
  chips: { gap: espaco.sm, paddingHorizontal: espaco.lg },
});
