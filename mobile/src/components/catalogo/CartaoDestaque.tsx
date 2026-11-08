import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { TipoFavorito } from '../../api/tipos';
import { cores, dimensoes, espaco, raio, tipografia } from '../../theme/tokens';
import { BotaoFavorito } from './BotaoFavorito';

// O Figma usa fotos das instituições/cursos, que não existem no banco. Os cards usam
// os três tons de roxo dos cards de cursos do Figma, alternados pela posição.
const TONS = [cores.roxoEscuro, cores.roxo, cores.roxoClaro];

type Props = {
  titulo: string;
  subtitulo?: string;
  indice: number;
  onPress: () => void;
  favorito: { tipo: TipoFavorito; id: number };
};

// Card da home do Figma (196×153, cantos 26) com nome em branco e coração no canto.
export function CartaoDestaque({ titulo, subtitulo, indice, onPress, favorito }: Props) {
  return (
    <View style={[styles.cartao, { backgroundColor: TONS[indice % TONS.length] }]}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={subtitulo ? `${titulo}, ${subtitulo}` : titulo}
        onPress={onPress}
        style={({ pressed }) => [styles.toque, pressed && { opacity: 0.85 }]}
      >
        <Text style={[tipografia.cartao, styles.titulo]} numberOfLines={3}>
          {titulo}
        </Text>
        {!!subtitulo && (
          <Text style={styles.subtitulo} numberOfLines={1}>
            {subtitulo}
          </Text>
        )}
      </Pressable>
      <View style={styles.coracao}>
        <BotaoFavorito tipo={favorito.tipo} id={favorito.id} nome={titulo} cor={cores.branco} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  cartao: {
    width: dimensoes.cartao.largura,
    height: dimensoes.cartao.altura,
    borderRadius: raio.cartao,
    overflow: 'hidden',
  },
  toque: { flex: 1, padding: espaco.md, justifyContent: 'space-between' },
  titulo: { color: cores.branco },
  subtitulo: { ...tipografia.legenda, color: cores.sobreBarra, marginRight: 40 },
  coracao: { position: 'absolute', right: espaco.smd, bottom: espaco.smd },
});
