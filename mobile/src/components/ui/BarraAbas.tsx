import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import type { BottomTabBarProps } from 'expo-router/js-tabs';
import { ComponentProps } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { cores, dimensoes, espaco, raio, tipografia } from '../../theme/tokens';

type Icone = ComponentProps<typeof MaterialIcons>['name'];

// Ícone de cada aba (inativo, ativo). O Figma usa os ícones Material: search, favorite, account_circle.
const ICONES: Record<string, [Icone, Icone]> = {
  '(explorar)': ['search', 'search'],
  '(salvos)': ['favorite-border', 'favorite'],
  '(perfil)': ['account-circle', 'account-circle'],
};

// Barra inferior do Figma: pílula laranja (#ff9100, cantos 30, altura 56) que flutua acima
// da área segura, com ícone 24 e rótulo Roboto Medium 12 em #fef7ff.
export function BarraAbas({ state, descriptors, navigation, insets }: BottomTabBarProps) {
  return (
    <View style={[styles.faixa, { paddingBottom: Math.max(insets.bottom, espaco.smd) }]}>
      <View style={styles.pilula} accessibilityRole="tablist">
        {state.routes.map((rota, indice) => {
          const { options } = descriptors[rota.key];
          const rotulo = options.title ?? rota.name;
          const ativo = state.index === indice;
          const [inativo, iconeAtivo] = ICONES[rota.name] ?? ['circle', 'circle'];

          function aoPressionar() {
            const evento = navigation.emit({ type: 'tabPress', target: rota.key, canPreventDefault: true });
            if (!ativo && !evento.defaultPrevented) navigation.navigate(rota.name, rota.params);
          }

          return (
            <Pressable
              key={rota.key}
              accessibilityRole="tab"
              accessibilityState={{ selected: ativo }}
              accessibilityLabel={rotulo}
              onPress={aoPressionar}
              onLongPress={() => navigation.emit({ type: 'tabLongPress', target: rota.key })}
              style={styles.item}
            >
              <View style={[styles.indicador, ativo && styles.indicadorAtivo]}>
                <MaterialIcons name={ativo ? iconeAtivo : inativo} size={24} color={cores.sobreBarra} />
              </View>
              <Text style={[tipografia.barra, styles.rotulo, ativo && styles.rotuloAtivo]}>{rotulo}</Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  faixa: { backgroundColor: cores.fundo, paddingHorizontal: espaco.lg, paddingTop: espaco.sm },
  pilula: {
    minHeight: dimensoes.alturaBarra,
    borderRadius: raio.barra,
    backgroundColor: cores.laranja,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: espaco.sm,
  },
  item: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingVertical: espaco.xs, gap: 2 },
  indicador: { width: 56, height: 28, borderRadius: raio.pilula, alignItems: 'center', justifyContent: 'center' },
  // Fora do Figma (todas as abas aparecem inativas no frame): realce da aba atual.
  indicadorAtivo: { backgroundColor: 'rgba(255, 255, 255, 0.28)' },
  rotulo: { color: cores.sobreBarra },
  rotuloAtivo: { fontFamily: tipografia.cabecalho.fontFamily },
});
