import { ReactElement, ReactNode } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';

import type { usePaginacao } from '../../hooks/usePaginacao';
import { cores, espaco, tipografia } from '../../theme/tokens';
import { Botao } from '../ui/Botao';
import { Carregando, EstadoErro, EstadoVazio } from '../ui/Estados';

type Props<T> = {
  pagina: ReturnType<typeof usePaginacao<T>>;
  renderItem: (item: T) => ReactElement;
  chave: (item: T) => string;
  /** Busca e filtros: rolam junto com a lista. */
  cabecalho: ReactNode;
  contagem: (total: number) => string;
  vazio: { titulo: string; mensagem: string };
};

// Lista do catálogo com rolagem infinita e os estados padrão (carregando, erro, vazio).
export function ListaPaginada<T>({ pagina, renderItem, chave, cabecalho, contagem, vazio }: Props<T>) {
  const { itens, total, carregando, carregandoMais, erro, temMais } = pagina;

  let estado: ReactNode = null;
  if (carregando) estado = <Carregando />;
  else if (erro && itens.length === 0) estado = <EstadoErro mensagem={erro} onTentarNovamente={pagina.recarregar} />;
  else if (itens.length === 0) estado = <EstadoVazio icone="search-off" titulo={vazio.titulo} mensagem={vazio.mensagem} />;

  return (
    <FlatList
      data={carregando ? [] : itens}
      keyExtractor={chave}
      renderItem={({ item }) => renderItem(item)}
      ListHeaderComponent={
        <View style={styles.cabecalho}>
          {cabecalho}
          {!carregando && !(erro && itens.length === 0) && (
            <Text style={styles.contagem} accessibilityLiveRegion="polite">
              {contagem(total)}
            </Text>
          )}
        </View>
      }
      ListEmptyComponent={<View style={styles.estado}>{estado}</View>}
      ListFooterComponent={
        carregandoMais ? (
          <ActivityIndicator color={cores.roxo} style={styles.rodape} />
        ) : erro && itens.length > 0 ? (
          <View style={styles.rodape}>
            <Text style={styles.contagem}>{erro}</Text>
            <Botao titulo="Tentar novamente" variante="texto" onPress={pagina.tentarMaisNovamente} />
          </View>
        ) : temMais ? null : (
          <View style={styles.rodape} />
        )
      }
      onEndReached={pagina.carregarMais}
      onEndReachedThreshold={0.5}
      contentContainerStyle={styles.conteudo}
      style={styles.lista}
      keyboardShouldPersistTaps="handled"
      keyboardDismissMode="on-drag"
    />
  );
}

const styles = StyleSheet.create({
  // A Tela já dá o recuo lateral; a lista ocupa a largura toda para a sombra não cortar.
  lista: { marginHorizontal: -espaco.lg },
  conteudo: { paddingHorizontal: espaco.lg, gap: espaco.md, flexGrow: 1 },
  cabecalho: { gap: espaco.md },
  contagem: { ...tipografia.descricao, color: cores.textoSuave },
  estado: { flexGrow: 1, minHeight: 240 },
  rodape: { paddingVertical: espaco.lg, alignItems: 'center' },
});
