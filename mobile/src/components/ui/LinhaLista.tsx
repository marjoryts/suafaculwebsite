import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { ComponentProps, ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { cores, dimensoes, espaco, raio, sombra, tipografia } from '../../theme/tokens';

type Props = {
  titulo: string;
  subtitulo?: string;
  icone?: ComponentProps<typeof MaterialIcons>['name'];
  onPress?: () => void;
  /** Elemento à direita (ex.: botão de desfavoritar, contagem de dias). */
  acessorio?: ReactNode;
};

// Linha de lista do Figma (Favoritos/Vestibulares): cartão branco, cantos 20, sombra,
// ícone laranja de 32 à esquerda e texto Inter 20.
export function LinhaLista({ titulo, subtitulo, icone, onPress, acessorio }: Props) {
  const conteudo = (
    <>
      {!!icone && <MaterialIcons name={icone} size={dimensoes.iconeLinha} color={cores.laranja} />}
      <View style={styles.textos}>
        <Text style={[tipografia.item, styles.titulo]} numberOfLines={2}>
          {titulo}
        </Text>
        {!!subtitulo && (
          <Text style={styles.subtitulo} numberOfLines={1}>
            {subtitulo}
          </Text>
        )}
      </View>
    </>
  );

  return (
    <View style={styles.linha}>
      {onPress ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={subtitulo ? `${titulo}, ${subtitulo}` : titulo}
          onPress={onPress}
          style={({ pressed }) => [styles.cartao, pressed && { opacity: 0.85 }]}
        >
          {conteudo}
        </Pressable>
      ) : (
        <View style={styles.cartao}>{conteudo}</View>
      )}
      {acessorio}
    </View>
  );
}

const styles = StyleSheet.create({
  linha: { flexDirection: 'row', alignItems: 'center', gap: espaco.smd },
  cartao: {
    flex: 1,
    minHeight: dimensoes.alturaLinha,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    paddingHorizontal: espaco.md,
    paddingVertical: espaco.sm,
    borderRadius: raio.linha,
    backgroundColor: cores.superficie,
    ...sombra,
  },
  textos: { flex: 1 },
  titulo: { color: cores.texto },
  subtitulo: { ...tipografia.corpo, fontSize: 14, color: cores.textoSuave },
});
