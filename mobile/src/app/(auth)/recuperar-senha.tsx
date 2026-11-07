import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { Botao } from '../../components/ui/Botao';
import { CampoTexto } from '../../components/ui/CampoTexto';
import { TelaAuth } from '../../components/ui/TelaAuth';
import { cores, tipografia } from '../../theme/tokens';

// SOMENTE INTERFACE (Figma "Verificar"): o backend ainda não tem recuperação de senha
// nem envio de e-mail. O botão fica desabilitado até existir o endpoint.
export default function RecuperarSenha() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  return (
    <TelaAuth variante="roxo" titulo="Recuperar senha">
      <Text style={styles.texto}>Insira seu e-mail para receber o código de verificação.</Text>
      <CampoTexto
        rotulo="E-mail"
        placeholder="Insira o e-mail"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
      />
      <Text style={styles.aviso}>A recuperação de senha ainda não está disponível.</Text>
      <Botao titulo="Enviar" variante="destaque" onPress={() => undefined} desabilitado />
      <Botao titulo="Cancelar" variante="texto" onPress={() => router.back()} />
    </TelaAuth>
  );
}

const styles = StyleSheet.create({
  texto: { ...tipografia.rotulo, color: cores.roxoEscuro, textAlign: 'center' },
  aviso: { ...tipografia.corpo, color: cores.textoSuave, textAlign: 'center' },
});
