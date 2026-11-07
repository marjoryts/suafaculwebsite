import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { Alert, Pressable } from 'react-native';

import type { TipoFavorito } from '../../api/tipos';
import { useFavoritos } from '../../favoritos/FavoritosProvider';
import { cores, dimensoes } from '../../theme/tokens';

type Props = {
  tipo: TipoFavorito;
  id: number;
  nome: string;
  /** Cor do coração (roxo-escuro sobre fundo claro, branco sobre os cards coloridos). */
  cor?: string;
  tamanho?: number;
};

// Coração do Figma ("favorite"): contorno quando não salvo, preenchido quando salvo.
export function BotaoFavorito({ tipo, id, nome, cor = cores.roxoEscuro, tamanho = 27 }: Props) {
  const { ehFavorito, alternar } = useFavoritos();
  const salvo = ehFavorito(tipo, id);

  async function aoPressionar() {
    try {
      await alternar(tipo, id, nome);
    } catch (e) {
      Alert.alert('Não foi possível atualizar seus salvos', (e as Error).message);
    }
  }

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={salvo ? `Remover ${nome} dos salvos` : `Salvar ${nome}`}
      accessibilityState={{ selected: salvo }}
      onPress={aoPressionar}
      hitSlop={Math.max(0, (dimensoes.areaToque - tamanho) / 2)}
      style={({ pressed }) => pressed && { opacity: 0.6 }}
    >
      <MaterialIcons name={salvo ? 'favorite' : 'favorite-border'} size={tamanho} color={cor} />
    </Pressable>
  );
}
