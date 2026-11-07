import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { useRouter } from 'expo-router';
import { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { cores, dimensoes, espaco, raio, tipografia } from '../../theme/tokens';

export type PropsCabecalho = {
  titulo?: string;
  /** Mostra o botão voltar. Padrão: só quando há para onde voltar. */
  voltar?: boolean;
  /** Ação à direita (ex.: "Salvar", "Editar Perfil"). */
  acao?: ReactNode;
  /** Para cabeçalhos sobre fundo roxo/laranja. */
  sobreCor?: boolean;
  /** Título das páginas de detalhe (Inter Medium 28, até 2 linhas). */
  grande?: boolean;
};

// Cabeçalho do Figma: botão voltar (30×30, cantos 15) + título Roboto 24 + ação opcional.
export function Cabecalho({ titulo, voltar, acao, sobreCor, grande }: PropsCabecalho) {
  const router = useRouter();
  const mostrarVoltar = voltar ?? router.canGoBack();
  return (
    <View style={styles.linha}>
      {mostrarVoltar && <BotaoVoltar sobreCor={sobreCor} onPress={() => router.back()} />}
      {!!titulo && (
        <Text
          accessibilityRole="header"
          numberOfLines={grande ? 2 : 1}
          style={[grande ? tipografia.tituloPagina : tipografia.cabecalho, styles.titulo, { color: sobreCor ? cores.branco : cores.roxoEscuro }]}
        >
          {titulo}
        </Text>
      )}
      {!!acao && <View style={styles.acao}>{acao}</View>}
    </View>
  );
}

export function BotaoVoltar({ onPress, sobreCor }: { onPress: () => void; sobreCor?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel="Voltar"
      onPress={onPress}
      // A área de toque (44) é maior que o círculo desenhado (30).
      hitSlop={(dimensoes.areaToque - dimensoes.botaoVoltar) / 2}
      style={({ pressed }) => [
        styles.voltar,
        { backgroundColor: sobreCor ? cores.botaoVoltarSobreCor : cores.botaoVoltar },
        pressed && { opacity: 0.7 },
      ]}
    >
      <MaterialIcons name="chevron-left" size={dimensoes.iconeVoltar} color={cores.roxoEscuro} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  linha: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm, minHeight: dimensoes.areaToque },
  titulo: { flexShrink: 1 },
  acao: { marginLeft: 'auto' },
  voltar: {
    width: dimensoes.botaoVoltar,
    height: dimensoes.botaoVoltar,
    borderRadius: raio.campo,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
