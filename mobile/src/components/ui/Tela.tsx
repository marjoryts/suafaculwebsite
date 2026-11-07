import { createContext, ReactNode, useContext } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { cores, espaco } from '../../theme/tokens';
import { Cabecalho, PropsCabecalho } from './Cabecalho';

/** true dentro das abas: a barra inferior já cuida da área segura de baixo. */
export const DentroDasAbas = createContext(false);

type Props = {
  children: ReactNode;
  cabecalho?: PropsCabecalho;
  /** Padrão: rola. Use false em telas com lista própria (FlatList). */
  rolar?: boolean;
};

// Container padrão das telas: fundo claro, área segura, rolagem e teclado.
export function Tela({ children, cabecalho, rolar = true }: Props) {
  const insets = useSafeAreaInsets();
  const nasAbas = useContext(DentroDasAbas);
  const margens = {
    paddingTop: insets.top + espaco.md,
    paddingBottom: (nasAbas ? 0 : insets.bottom) + espaco.lg,
  };
  const topo = cabecalho ? <Cabecalho {...cabecalho} /> : null;

  return (
    <KeyboardAvoidingView style={styles.raiz} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      {rolar ? (
        <ScrollView
          contentContainerStyle={[styles.conteudo, margens]}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
        >
          {topo}
          {children}
        </ScrollView>
      ) : (
        <View style={[styles.conteudo, styles.fixo, margens]}>
          {topo}
          {children}
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  raiz: { flex: 1, backgroundColor: cores.fundo },
  conteudo: { flexGrow: 1, paddingHorizontal: espaco.lg, gap: espaco.md },
  fixo: { flex: 1 },
});
