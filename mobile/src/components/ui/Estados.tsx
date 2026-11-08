import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { ComponentProps } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { cores, espaco, tipografia } from '../../theme/tokens';
import { Botao } from './Botao';

// Padrões de carregando, erro e vazio para todas as telas que buscam dados.
// O Figma não desenha esses estados: seguem a mesma paleta e tipografia.

export function Carregando({ mensagem = 'Carregando...' }: { mensagem?: string }) {
  return (
    <View style={styles.centro} accessibilityRole="progressbar" accessibilityLabel={mensagem}>
      <ActivityIndicator size="large" color={cores.roxo} />
      <Text style={styles.texto}>{mensagem}</Text>
    </View>
  );
}

export function EstadoErro({
  mensagem,
  onTentarNovamente,
}: {
  mensagem: string;
  onTentarNovamente?: () => void;
}) {
  return (
    <View style={styles.centro} accessibilityLiveRegion="polite">
      <MaterialIcons name="error-outline" size={48} color={cores.erro} />
      <Text style={[styles.titulo, { color: cores.erro }]}>Algo deu errado</Text>
      <Text style={styles.texto}>{mensagem}</Text>
      {!!onTentarNovamente && (
        <Botao titulo="Tentar novamente" tamanho="compacto" variante="secundario" onPress={onTentarNovamente} />
      )}
    </View>
  );
}

export function EstadoVazio({
  titulo,
  mensagem,
  icone = 'inbox',
}: {
  titulo: string;
  mensagem?: string;
  icone?: ComponentProps<typeof MaterialIcons>['name'];
}) {
  return (
    <View style={styles.centro}>
      <MaterialIcons name={icone} size={48} color={cores.laranja} />
      <Text style={styles.titulo}>{titulo}</Text>
      {!!mensagem && <Text style={styles.texto}>{mensagem}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  centro: { flexGrow: 1, alignItems: 'center', justifyContent: 'center', gap: espaco.smd, padding: espaco.lg },
  titulo: { ...tipografia.rotulo, fontSize: 20, color: cores.roxoEscuro, textAlign: 'center' },
  texto: { ...tipografia.corpo, color: cores.textoSuave, textAlign: 'center' },
});
