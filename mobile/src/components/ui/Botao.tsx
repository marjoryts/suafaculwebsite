import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { ComponentProps } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { cores, dimensoes, espaco, raio, sombra, tipografia } from '../../theme/tokens';

type Variante =
  | 'primario' // roxo ("Entrar")
  | 'destaque' // laranja claro ("Cadastrar")
  | 'secundario' // contorno roxo
  | 'texto'; // link sublinhado ("Esqueceu a senha?")

type Props = {
  titulo: string;
  onPress: () => void;
  variante?: Variante;
  /** Botões grandes do Figma (22px) ou compactos (16px), para listas e ações secundárias. */
  tamanho?: 'grande' | 'compacto';
  icone?: ComponentProps<typeof MaterialIcons>['name'];
  /** Texto branco: para botões de texto sobre fundo roxo/laranja. */
  sobreCor?: boolean;
  carregando?: boolean;
  desabilitado?: boolean;
  /** Nome lido pelo leitor de tela quando o texto sozinho é ambíguo (ex.: vários "Ver todos"). */
  rotuloAcessivel?: string;
};

export function Botao({
  titulo,
  onPress,
  variante = 'primario',
  tamanho = 'grande',
  icone,
  sobreCor,
  carregando,
  desabilitado,
  rotuloAcessivel,
}: Props) {
  const inativo = desabilitado || carregando;
  const preenchido = variante === 'primario' || variante === 'destaque';
  const corTexto = preenchido || sobreCor ? cores.sobreMarca : cores.roxo;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={rotuloAcessivel ?? titulo}
      accessibilityState={{ disabled: !!inativo, busy: !!carregando }}
      disabled={inativo}
      onPress={onPress}
      hitSlop={variante === 'texto' ? espaco.sm : undefined}
      style={({ pressed }) => [
        variante !== 'texto' && styles.base,
        variante === 'primario' && styles.primario,
        variante === 'destaque' && styles.destaque,
        variante === 'secundario' && styles.secundario,
        variante === 'secundario' && sobreCor && styles.secundarioSobreCor,
        variante === 'texto' && styles.texto,
        tamanho === 'compacto' && variante !== 'texto' && styles.compacto,
        pressed && styles.pressionado,
        inativo && styles.inativo,
      ]}
    >
      {carregando ? (
        <ActivityIndicator color={corTexto} />
      ) : (
        <View style={styles.conteudo}>
          {!!icone && <MaterialIcons name={icone} size={tamanho === 'grande' ? 20 : 18} color={corTexto} />}
          <Text
            style={[
              tamanho === 'grande' && variante !== 'texto' ? tipografia.botao : tipografia.botaoCompacto,
              variante === 'texto' && styles.sublinhado,
              { color: corTexto },
            ]}
          >
            {titulo}
          </Text>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: dimensoes.alturaBotao,
    borderRadius: raio.campo,
    padding: espaco.smd,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primario: { backgroundColor: cores.roxo, ...sombra },
  destaque: { backgroundColor: cores.laranjaClaro, ...sombra },
  secundario: { borderWidth: 1.5, borderColor: cores.roxo, backgroundColor: 'transparent' },
  secundarioSobreCor: { borderColor: cores.sobreMarca },
  texto: { alignSelf: 'center', minHeight: dimensoes.areaToque, justifyContent: 'center' },
  compacto: { minHeight: dimensoes.areaToque, paddingVertical: espaco.sm },
  conteudo: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm },
  sublinhado: { fontFamily: tipografia.corpo.fontFamily, textDecorationLine: 'underline' },
  pressionado: { opacity: 0.85 },
  inativo: { opacity: 0.5 },
});
