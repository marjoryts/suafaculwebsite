import { forwardRef, useState } from 'react';
import { StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';

import { cores, dimensoes, espaco, raio, sombra, tipografia } from '../../theme/tokens';

type Props = TextInputProps & {
  rotulo: string;
  erro?: string;
  /** Rótulo branco: para formulários sobre a folha laranja do login. */
  sobreCor?: boolean;
};

// Campo do Figma: rótulo acima, caixa branca de cantos 15 com sombra.
export const CampoTexto = forwardRef<TextInput, Props>(function CampoTexto(
  { rotulo, erro, sobreCor, style, editable = true, onFocus, onBlur, ...resto },
  ref,
) {
  const [focado, setFocado] = useState(false);
  return (
    <View style={styles.grupo}>
      <Text style={[tipografia.rotulo, { color: sobreCor ? cores.branco : cores.roxoEscuro }]}>{rotulo}</Text>
      <TextInput
        ref={ref}
        accessibilityLabel={rotulo}
        accessibilityState={{ disabled: !editable }}
        editable={editable}
        placeholderTextColor={cores.placeholder}
        onFocus={(e) => {
          setFocado(true);
          onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocado(false);
          onBlur?.(e);
        }}
        style={[
          styles.campo,
          focado && styles.focado,
          !!erro && styles.comErro,
          !editable && styles.inativo,
          style,
        ]}
        {...resto}
      />
      {!!erro && (
        <Text style={[styles.erro, sobreCor && styles.erroSobreCor]} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
    </View>
  );
});

const styles = StyleSheet.create({
  grupo: { gap: espaco.sm },
  campo: {
    minHeight: dimensoes.alturaCampo,
    borderRadius: raio.campo,
    borderWidth: 1.5,
    borderColor: 'transparent',
    backgroundColor: cores.superficie,
    color: cores.texto,
    // Sem lineHeight: no Android ele corta o texto digitado.
    fontFamily: tipografia.corpo.fontFamily,
    fontSize: tipografia.corpo.fontSize,
    paddingHorizontal: espaco.md,
    paddingVertical: espaco.smd,
    ...sombra,
  },
  focado: { borderColor: cores.roxo },
  comErro: { borderColor: cores.erro },
  inativo: { opacity: 0.5 },
  erro: { ...tipografia.corpo, fontSize: 14, color: cores.erro },
  erroSobreCor: { color: cores.branco, fontFamily: tipografia.rotulo.fontFamily },
});
