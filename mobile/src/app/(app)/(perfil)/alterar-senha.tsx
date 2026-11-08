import { useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, Text, TextInput } from 'react-native';

import { alterarSenha } from '../../../api/perfil';
import { useSessao } from '../../../auth/SessaoProvider';
import { Botao } from '../../../components/ui/Botao';
import { CampoTexto } from '../../../components/ui/CampoTexto';
import { TelaPerfil } from '../../../components/ui/TelaPerfil';
import { mensagemDeErro } from '../../../hooks/useConsulta';
import { cores, tipografia } from '../../../theme/tokens';

// Troca de senha, como no "Perfil e configurações" do site: nova senha + confirmação.
// O backend valida o tamanho e encerra as sessões do app nos outros aparelhos.
export default function AlterarSenha() {
  const router = useRouter();
  const { usuario } = useSessao();
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState(false);
  const campoConfirmacao = useRef<TextInput>(null);

  async function salvar() {
    setErro(null);
    setSucesso(false);
    if (!senha) {
      setErro('Informe a nova senha.');
      return;
    }
    if (senha !== confirmacao) {
      setErro('A confirmação não confere com a nova senha.');
      return;
    }
    setSalvando(true);
    try {
      await alterarSenha(senha, confirmacao);
      setSenha('');
      setConfirmacao('');
      setSucesso(true);
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <TelaPerfil usuario={usuario} onVoltar={() => router.back()}>
      <Text style={[tipografia.subtitulo, styles.titulo]} accessibilityRole="header">
        Alterar senha
      </Text>
      <CampoTexto
        rotulo="Nova senha"
        value={senha}
        onChangeText={setSenha}
        secureTextEntry
        autoCapitalize="none"
        autoComplete="new-password"
        returnKeyType="next"
        onSubmitEditing={() => campoConfirmacao.current?.focus()}
        submitBehavior="submit"
      />
      <CampoTexto
        ref={campoConfirmacao}
        rotulo="Confirme a nova senha"
        value={confirmacao}
        onChangeText={setConfirmacao}
        secureTextEntry
        autoCapitalize="none"
        autoComplete="new-password"
        returnKeyType="done"
        onSubmitEditing={salvar}
      />
      <Text style={[tipografia.descricao, styles.cinza]}>
        Ao trocar a senha, as sessões do app em outros aparelhos são encerradas.
      </Text>
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      {sucesso && (
        <Text style={styles.sucesso} accessibilityLiveRegion="polite">
          Senha alterada com sucesso!
        </Text>
      )}
      <Botao titulo="Alterar senha" onPress={salvar} carregando={salvando} />
    </TelaPerfil>
  );
}

const styles = StyleSheet.create({
  titulo: { color: cores.roxoEscuro },
  cinza: { color: cores.textoSuave },
  erro: { ...tipografia.corpo, color: cores.erro },
  sucesso: { ...tipografia.rotulo, color: cores.sucesso },
});
