import { useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { cores, espaco, raio, sombra, tipografia } from '../../theme/tokens';

export const DIGITOS_DO_CODIGO = 5;

type Props = {
  valor: string;
  onChange(valor: string): void;
  /** Chamado quando os 5 dígitos foram digitados. */
  onCompleto?(valor: string): void;
  desabilitado?: boolean;
  autoFocus?: boolean;
};

// Figma "Esqueceu Senha": cinco caixas de dígito. Um único campo invisível recebe o
// teclado (colar e o preenchimento automático de SMS/e-mail funcionam de uma vez).
export function CampoCodigo({ valor, onChange, onCompleto, desabilitado, autoFocus }: Props) {
  const campo = useRef<TextInput>(null);
  const [focado, setFocado] = useState(false);

  function mudar(texto: string) {
    const digitos = texto.replace(/\D/g, '').slice(0, DIGITOS_DO_CODIGO);
    onChange(digitos);
    if (digitos.length === DIGITOS_DO_CODIGO) onCompleto?.(digitos);
  }

  return (
    <Pressable onPress={() => campo.current?.focus()} accessible={false} style={styles.linha}>
      {Array.from({ length: DIGITOS_DO_CODIGO }, (_, i) => {
        const atual = focado && i === Math.min(valor.length, DIGITOS_DO_CODIGO - 1);
        return (
          <View key={i} style={[styles.caixa, atual && styles.caixaAtual, desabilitado && styles.inativo]}>
            <Text style={styles.digito}>{valor[i] ?? ''}</Text>
          </View>
        );
      })}
      <TextInput
        ref={campo}
        value={valor}
        onChangeText={mudar}
        editable={!desabilitado}
        autoFocus={autoFocus}
        keyboardType="number-pad"
        textContentType="oneTimeCode"
        autoComplete="one-time-code"
        maxLength={DIGITOS_DO_CODIGO}
        accessibilityLabel="Código de 5 dígitos"
        onFocus={() => setFocado(true)}
        onBlur={() => setFocado(false)}
        caretHidden
        style={styles.invisivel}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  linha: { flexDirection: 'row', justifyContent: 'center', gap: espaco.smd },
  caixa: {
    width: 52,
    height: 60,
    borderRadius: raio.campo,
    borderWidth: 2,
    borderColor: 'transparent',
    backgroundColor: cores.superficie,
    alignItems: 'center',
    justifyContent: 'center',
    ...sombra,
  },
  caixaAtual: { borderColor: cores.roxo },
  inativo: { opacity: 0.5 },
  digito: { ...tipografia.subtitulo, color: cores.roxoEscuro },
  invisivel: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, opacity: 0.01, color: 'transparent' },
});
