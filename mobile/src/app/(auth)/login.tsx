import { useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { ApiError } from '../../api/client';
import { useSessao } from '../../auth/SessaoProvider';
import { Botao } from '../../components/ui/Botao';
import { CampoTexto } from '../../components/ui/CampoTexto';
import { EntrarCom } from '../../components/ui/EntrarCom';
import { TelaAuth } from '../../components/ui/TelaAuth';
import { cores, espaco, raio, tipografia } from '../../theme/tokens';

export default function Login() {
  const { entrar } = useSessao();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);
  const campoSenha = useRef<TextInput>(null);

  async function enviar() {
    setErro(null);
    if (!email.trim() || !senha) {
      setErro('Informe e-mail e senha.');
      return;
    }
    setCarregando(true);
    try {
      await entrar(email.trim(), senha);
      // A navegação é feita pelo porteiro da raiz (a sessão passou a existir).
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível entrar.');
      setCarregando(false);
    }
  }

  // Figma "Segunda Tela": topo branco com a logo e folha laranja com o formulário.
  // O Figma rotula o campo "Nome do usuário ou E-mail", mas a API v1 só aceita e-mail.
  return (
    <TelaAuth variante="laranja" titulo="Bem-vindo(a) de volta!">
      <CampoTexto
        sobreCor
        rotulo="E-mail"
        placeholder="Insira seu e-mail"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoComplete="email"
        autoCorrect={false}
        returnKeyType="next"
        onSubmitEditing={() => campoSenha.current?.focus()}
        submitBehavior="submit"
      />
      <CampoTexto
        ref={campoSenha}
        sobreCor
        rotulo="Senha"
        placeholder="Insira sua senha"
        value={senha}
        onChangeText={setSenha}
        secureTextEntry
        autoCapitalize="none"
        autoComplete="current-password"
        returnKeyType="go"
        onSubmitEditing={enviar}
      />
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      <Botao titulo="Entrar" icone="login" onPress={enviar} carregando={carregando} />
      <View style={styles.direita}>
        <Botao titulo="Esqueceu a senha?" variante="texto" sobreCor onPress={() => router.push('/recuperar-senha')} />
      </View>
      <Botao titulo="Criar conta" variante="secundario" sobreCor tamanho="compacto" onPress={() => router.push('/cadastro')} />
      <Text style={styles.entrarCom}>Entrar com</Text>
      <EntrarCom sobreCor />
    </TelaAuth>
  );
}

const styles = StyleSheet.create({
  erro: { ...tipografia.rotulo, color: cores.branco, backgroundColor: cores.erro, borderRadius: raio.campo, padding: espaco.smd },
  direita: { alignItems: 'flex-end', marginTop: -espaco.md },
  entrarCom: { ...tipografia.rotulo, color: cores.branco, textAlign: 'center', textDecorationLine: 'underline' },
});
