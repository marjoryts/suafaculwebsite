import { useFocusEffect } from 'expo-router';
import { setStatusBarStyle } from 'expo-status-bar';
import { ReactNode, useCallback } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { Usuario } from '../../api/tipos';
import { cores, dimensoes, espaco, familias, raio, tipografia } from '../../theme/tokens';
import { Avatar } from './Avatar';
import { BotaoVoltar } from './Cabecalho';

type Props = {
  usuario: Usuario | null;
  /** Ação no canto superior direito ("Editar Perfil", "Salvar"). */
  acao?: ReactNode;
  /** Mostra o botão voltar (telas empilhadas, como Editar Perfil). */
  onVoltar?: () => void;
  /** Linha extra sob o e-mail (ex.: "Estudante"). */
  detalhe?: string;
  children: ReactNode;
};

// Moldura dos frames "Perfil" e "Editar Perfil" do Figma: topo roxo com avatar e nome,
// folha clara de cantos 40 com o conteúdo.
export function TelaPerfil({ usuario, acao, onVoltar, detalhe, children }: Props) {
  const insets = useSafeAreaInsets();

  // Texto claro na barra de status só enquanto o topo roxo está visível.
  useFocusEffect(
    useCallback(() => {
      setStatusBarStyle('light');
      return () => setStatusBarStyle('dark');
    }, []),
  );

  return (
    <KeyboardAvoidingView style={styles.raiz} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.rolagem} bounces={false} keyboardShouldPersistTaps="handled">
        <View style={[styles.topo, { paddingTop: insets.top + espaco.sm }]}>
          <View style={styles.barra}>
            {onVoltar ? <BotaoVoltar sobreCor onPress={onVoltar} /> : <View />}
            {acao}
          </View>
          <Avatar nome={usuario?.nome_usuario} url={usuario?.avatar_url} tamanho={dimensoes.avatarGrande} />
          <Text style={styles.nome} numberOfLines={1}>
            {usuario?.nome_usuario}
          </Text>
          <Text style={styles.email} numberOfLines={1}>
            {usuario?.email}
          </Text>
          {!!detalhe && <Text style={styles.detalhe}>{detalhe}</Text>}
        </View>
        <View style={styles.folha}>{children}</View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  raiz: { flex: 1, backgroundColor: cores.roxo },
  rolagem: { flexGrow: 1 },
  topo: { alignItems: 'center', paddingHorizontal: espaco.lg, paddingBottom: espaco.xl, gap: espaco.sm },
  barra: { alignSelf: 'stretch', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', minHeight: dimensoes.areaToque },
  nome: { fontFamily: familias.interMedio, fontSize: 30, lineHeight: 40, color: cores.branco, marginTop: espaco.sm },
  email: { ...tipografia.corpo, color: cores.sobreBarra },
  detalhe: { ...tipografia.legenda, color: cores.sobreBarra },
  folha: {
    flexGrow: 1,
    backgroundColor: cores.folha,
    borderTopLeftRadius: raio.painel,
    borderTopRightRadius: raio.painel,
    padding: espaco.lg,
    gap: espaco.md + 2, // 18 entre as linhas, como no Figma
  },
});
