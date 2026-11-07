import { useRouter } from 'expo-router';
import { StyleSheet, Text } from 'react-native';

import { Botao } from '../../components/ui/Botao';
import { TelaAuth } from '../../components/ui/TelaAuth';
import { cores, tipografia } from '../../theme/tokens';

// SOMENTE INTERFACE (Figma "Esqueceu Senha", código de 5 dígitos): o backend ainda
// não tem verificação de e-mail, então não há campos de código.
export default function VerificarEmail() {
  const router = useRouter();
  return (
    <TelaAuth variante="roxo" titulo="Verifique seu e-mail">
      <Text style={styles.texto}>A verificação de e-mail ainda não está disponível.</Text>
      <Botao titulo="Voltar" variante="secundario" tamanho="compacto" onPress={() => router.back()} />
    </TelaAuth>
  );
}

const styles = StyleSheet.create({
  texto: { ...tipografia.corpo, color: cores.textoSuave, textAlign: 'center' },
});
