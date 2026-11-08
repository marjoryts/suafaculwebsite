import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { ApiError } from '../../api/client';
import { useSessao } from '../../auth/SessaoProvider';
import { Botao } from '../../components/ui/Botao';
import { CampoTexto } from '../../components/ui/CampoTexto';
import { EntrarCom } from '../../components/ui/EntrarCom';
import { TelaAuth } from '../../components/ui/TelaAuth';
import { cores, espaco, tipografia } from '../../theme/tokens';

export default function Cadastro() {
  const { cadastrar } = useSessao();
  const router = useRouter();
  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function enviar() {
    setErro(null);
    // Só conferências de interface. As regras (e-mail válido, tamanho da senha,
    // conta já existente) são do backend e voltam como mensagem.
    if (!nome.trim() || !email.trim() || !senha) {
      setErro('Preencha todos os campos.');
      return;
    }
    if (senha !== confirmacao) {
      setErro('A confirmação não confere com a senha.');
      return;
    }
    setCarregando(true);
    try {
      await cadastrar(nome.trim(), email.trim(), senha);
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível criar a conta.');
      setCarregando(false);
    }
  }

  // Figma "Terceira Tela": topo roxo com a logo branca e folha clara com o formulário.
  // (O frame do Figma não tem o campo "Senha", só "Confirme sua senha"; os dois são necessários.)
  return (
    <TelaAuth variante="roxo" titulo="Bem-vindo(a)!">
      <CampoTexto
        rotulo="Nome de usuário"
        placeholder="Insira o nome de usuário"
        value={nome}
        onChangeText={setNome}
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="username"
      />
      <CampoTexto
        rotulo="E-mail"
        placeholder="Insira seu e-mail"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoComplete="email"
        autoCorrect={false}
      />
      <CampoTexto
        rotulo="Senha"
        placeholder="Insira sua senha"
        value={senha}
        onChangeText={setSenha}
        secureTextEntry
        autoCapitalize="none"
        autoComplete="new-password"
      />
      <CampoTexto
        rotulo="Confirme sua senha"
        placeholder="Insira sua senha"
        value={confirmacao}
        onChangeText={setConfirmacao}
        secureTextEntry
        autoCapitalize="none"
        autoComplete="new-password"
        returnKeyType="go"
        onSubmitEditing={enviar}
      />
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      <Botao titulo="Cadastrar" variante="destaque" icone="login" onPress={enviar} carregando={carregando} />
      <Botao titulo="Já tem uma conta? Entrar" variante="texto" onPress={() => router.back()} />
      <Text style={styles.ou}>ou registrar com</Text>
      <EntrarCom />
    </TelaAuth>
  );
}

const styles = StyleSheet.create({
  erro: { ...tipografia.corpo, color: cores.erro },
  ou: { ...tipografia.corpo, color: cores.roxoEscuro, textAlign: 'center', marginBottom: -espaco.sm },
});
