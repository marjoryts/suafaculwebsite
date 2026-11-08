import { useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { cores, espaco, raio, tipografia } from '../../theme/tokens';
import { BotaoVoltar } from './Cabecalho';
import { Logo } from './Logo';

type Props = {
  titulo: string;
  /**
   * laranja: topo branco + folha laranja (Figma "Segunda Tela", login).
   * roxo: topo roxo + folha clara (Figma "Terceira Tela", cadastro).
   */
  variante: 'laranja' | 'roxo';
  children: ReactNode;
};

// Moldura das telas de autenticação: logo no topo e uma folha de cantos arredondados
// com o título e o formulário. Rola e sobe com o teclado.
export function TelaAuth({ titulo, variante, children }: Props) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const laranja = variante === 'laranja';

  return (
    <KeyboardAvoidingView
      style={[styles.raiz, { backgroundColor: laranja ? cores.branco : cores.roxoProfundo }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <StatusBar style={laranja ? 'dark' : 'light'} />
      <ScrollView
        contentContainerStyle={styles.rolagem}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        bounces={false}
      >
        <View style={[styles.topo, { paddingTop: insets.top + espaco.lg }]}>
          <Logo cor={laranja ? 'roxo' : 'branco'} />
        </View>
        <View
          style={[
            styles.folha,
            { backgroundColor: laranja ? cores.laranjaClaro : cores.folha, paddingBottom: insets.bottom + espaco.lg },
          ]}
        >
          <View style={styles.linhaTitulo}>
            {router.canGoBack() && (
              <View style={styles.voltar}>
                <BotaoVoltar sobreCor={laranja} onPress={() => router.back()} />
              </View>
            )}
            <Text
              accessibilityRole="header"
              style={[tipografia.titulo, styles.titulo, { color: laranja ? cores.branco : cores.roxoEscuro }]}
            >
              {titulo}
            </Text>
          </View>
          {children}
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  raiz: { flex: 1 },
  rolagem: { flexGrow: 1 },
  topo: { alignItems: 'center', paddingBottom: espaco.lg },
  folha: {
    flexGrow: 1,
    borderTopLeftRadius: raio.folha,
    borderTopRightRadius: raio.folha,
    paddingHorizontal: espaco.lg + espaco.md,
    paddingTop: espaco.xl,
    gap: espaco.lg,
  },
  linhaTitulo: { minHeight: 44, justifyContent: 'center' },
  voltar: { position: 'absolute', left: -espaco.sm, zIndex: 1 },
  titulo: { textAlign: 'center', paddingHorizontal: espaco.xl },
});
