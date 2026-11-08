import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { atualizarPerfil } from '../../../api/perfil';
import { useSessao } from '../../../auth/SessaoProvider';
import { Botao } from '../../../components/ui/Botao';
import { CampoTexto } from '../../../components/ui/CampoTexto';
import { OpcaoMenu } from '../../../components/ui/OpcaoMenu';
import { TelaPerfil } from '../../../components/ui/TelaPerfil';
import { mensagemDeErro } from '../../../hooks/useConsulta';
import { cores, tipografia } from '../../../theme/tokens';

// Figma "Editar Perfil" (+ "Perfil e configurações" do painel do site): nome de usuário e
// e-mail. O Figma também mostra "Telefone", que não existe no cadastro.
export default function EditarPerfil() {
  const router = useRouter();
  const { usuario, atualizarUsuario } = useSessao();
  const [nome, setNome] = useState(usuario?.nome_usuario ?? '');
  const [email, setEmail] = useState(usuario?.email ?? '');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState(false);

  const mudou = nome.trim() !== usuario?.nome_usuario || email.trim() !== usuario?.email;

  async function salvar() {
    setErro(null);
    setSucesso(false);
    if (!nome.trim() || !email.trim()) {
      setErro('Preencha o nome de usuário e o e-mail.');
      return;
    }
    setSalvando(true);
    try {
      const { data } = await atualizarPerfil({ nome_usuario: nome.trim(), email: email.trim() });
      atualizarUsuario(data);
      setSucesso(true);
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <TelaPerfil
      usuario={usuario}
      onVoltar={() => router.back()}
      acao={<Botao titulo="Salvar" variante="texto" sobreCor onPress={salvar} carregando={salvando} desabilitado={!mudou} />}
    >
      <Text style={[tipografia.subtitulo, styles.titulo]} accessibilityRole="header">
        Alterar Perfil
      </Text>
      <CampoTexto
        rotulo="Nome de usuário"
        value={nome}
        onChangeText={setNome}
        autoCapitalize="none"
        autoCorrect={false}
        autoComplete="username"
      />
      <CampoTexto
        rotulo="Endereço de E-mail"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        autoComplete="email"
        autoCorrect={false}
        returnKeyType="done"
        onSubmitEditing={salvar}
      />
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      {sucesso && (
        <Text style={styles.sucesso} accessibilityLiveRegion="polite">
          Perfil atualizado com sucesso!
        </Text>
      )}
      <Botao titulo="Salvar alterações" onPress={salvar} carregando={salvando} desabilitado={!mudou} />
      <OpcaoMenu titulo="Alterar senha" icone="lock" onPress={() => router.push('/alterar-senha')} />
    </TelaPerfil>
  );
}

const styles = StyleSheet.create({
  titulo: { color: cores.roxoEscuro },
  erro: { ...tipografia.corpo, color: cores.erro },
  sucesso: { ...tipografia.rotulo, color: cores.sucesso },
});
