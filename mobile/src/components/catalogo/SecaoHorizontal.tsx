import { ReactNode } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';

import { cores, espaco, tipografia } from '../../theme/tokens';
import { Botao } from '../ui/Botao';

type Props = {
  titulo: string;
  onVerTodos?: () => void;
  carregando?: boolean;
  erro?: string | null;
  onTentarNovamente?: () => void;
  vazio?: string;
  children?: ReactNode;
};

// Seção da home do Figma ("Faculdades Públicas", "Cursos"...): título + cards rolando
// na horizontal. Mostra carregando, erro e vazio sem quebrar o resto da tela.
export function SecaoHorizontal({ titulo, onVerTodos, carregando, erro, onTentarNovamente, vazio, children }: Props) {
  let corpo: ReactNode;
  if (carregando) corpo = <ActivityIndicator color={cores.roxo} style={styles.estado} />;
  else if (erro)
    corpo = (
      <View style={styles.estado}>
        <Text style={styles.aviso}>{erro}</Text>
        {!!onTentarNovamente && (
          <Botao titulo="Tentar novamente" variante="texto" onPress={onTentarNovamente} />
        )}
      </View>
    );
  else if (vazio) corpo = <Text style={[styles.aviso, styles.estado]}>{vazio}</Text>;
  else
    corpo = (
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.cards}
        style={styles.rolagem}
      >
        {children}
      </ScrollView>
    );

  return (
    <View style={styles.secao}>
      <View style={styles.cabecalho}>
        <Text style={[tipografia.secao, styles.titulo]} accessibilityRole="header" numberOfLines={1}>
          {titulo}
        </Text>
        {!!onVerTodos && (
          <Botao titulo="Ver todos" variante="texto" onPress={onVerTodos} rotuloAcessivel={`Ver todos: ${titulo}`} />
        )}
      </View>
      {corpo}
    </View>
  );
}

const styles = StyleSheet.create({
  secao: { gap: espaco.smd },
  cabecalho: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: espaco.sm },
  titulo: { color: cores.roxoEscuro, flexShrink: 1 },
  // Os cards encostam na borda da tela ao rolar, como no Figma.
  rolagem: { marginHorizontal: -espaco.lg },
  cards: { gap: espaco.md, paddingHorizontal: espaco.lg },
  estado: { minHeight: 80, justifyContent: 'center', alignItems: 'flex-start' },
  aviso: { ...tipografia.descricao, color: cores.textoSuave },
});
