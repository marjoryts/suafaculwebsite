import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { codigoPerdido, mensagemDoCodigo } from '../../../api/conta';
import { atualizarPerfil, confirmarTrocaDeEmail, pedirTrocaDeEmail } from '../../../api/perfil';
import { useSessao } from '../../../auth/SessaoProvider';
import { Botao } from '../../../components/ui/Botao';
import { CampoCodigo, DIGITOS_DO_CODIGO } from '../../../components/ui/CampoCodigo';
import { CampoTexto } from '../../../components/ui/CampoTexto';
import { OpcaoMenu } from '../../../components/ui/OpcaoMenu';
import { TelaPerfil } from '../../../components/ui/TelaPerfil';
import { mensagemDeErro } from '../../../hooks/useConsulta';
import { cores, tipografia } from '../../../theme/tokens';

// Figma "Editar Perfil" (+ "Perfil e configurações" do painel do site): nome de usuário e
// e-mail. O Figma também mostra "Telefone", que não existe no cadastro.
// Trocar o e-mail exige a senha atual e um código enviado ao endereço NOVO; até a
// confirmação, o e-mail antigo continua valendo.
export default function EditarPerfil() {
  const router = useRouter();
  const { usuario, atualizarUsuario } = useSessao();
  const pedeSenhaAtual = usuario?.senha_definida !== false;
  const [nome, setNome] = useState(usuario?.nome_usuario ?? '');
  const [email, setEmail] = useState(usuario?.email ?? '');
  const [senhaAtual, setSenhaAtual] = useState('');
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);
  // Troca de e-mail aguardando o código.
  const [emailPendente, setEmailPendente] = useState<string | null>(null);
  const [codigo, setCodigo] = useState('');

  const mudouNome = nome.trim() !== usuario?.nome_usuario;
  const mudouEmail = email.trim().toLowerCase() !== (usuario?.email ?? '').toLowerCase();
  const mudou = mudouNome || mudouEmail;

  async function salvar() {
    setErro(null);
    setSucesso(null);
    if (!nome.trim() || !email.trim()) {
      setErro('Preencha o nome de usuário e o e-mail.');
      return;
    }
    if (mudouEmail && pedeSenhaAtual && !senhaAtual) {
      setErro('Informe sua senha atual para trocar o e-mail.');
      return;
    }
    setSalvando(true);
    try {
      if (mudouNome) {
        const { data } = await atualizarPerfil({ nome_usuario: nome.trim(), email: usuario?.email ?? '' });
        atualizarUsuario(data);
      }
      if (mudouEmail) {
        const { data } = await pedirTrocaDeEmail(email.trim(), pedeSenhaAtual ? senhaAtual : undefined);
        setEmailPendente(email.trim());
        setSenhaAtual('');
        setSucesso(data.mensagem);
      } else {
        setSucesso('Perfil atualizado com sucesso!');
      }
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setSalvando(false);
    }
  }

  async function confirmarEmail(valor = codigo) {
    setErro(null);
    if (valor.length !== DIGITOS_DO_CODIGO) {
      setErro('Digite os 5 dígitos do código.');
      return;
    }
    setSalvando(true);
    try {
      const { data } = await confirmarTrocaDeEmail(valor);
      atualizarUsuario(data);
      setEmail(data.email);
      setEmailPendente(null);
      setCodigo('');
      setSucesso('E-mail atualizado e confirmado!');
    } catch (e) {
      setErro(mensagemDoCodigo(e) + (codigoPerdido(e) ? ' Salve o novo e-mail de novo para receber outro código.' : ''));
      setCodigo('');
    } finally {
      setSalvando(false);
    }
  }

  function cancelarTroca() {
    setEmailPendente(null);
    setCodigo('');
    setEmail(usuario?.email ?? '');
    setErro(null);
    setSucesso(null);
  }

  const mensagens = (
    <>
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      {!!sucesso && (
        <Text style={styles.sucesso} accessibilityLiveRegion="polite">
          {sucesso}
        </Text>
      )}
    </>
  );

  if (emailPendente) {
    return (
      <TelaPerfil usuario={usuario} onVoltar={cancelarTroca}>
        <Text style={[tipografia.subtitulo, styles.titulo]} accessibilityRole="header">
          Confirme o novo e-mail
        </Text>
        <Text style={[tipografia.corpo, styles.cinza]}>
          Digite o código de 5 dígitos enviado para {emailPendente}. Ele vale por 30 minutos.
        </Text>
        <CampoCodigo valor={codigo} onChange={setCodigo} onCompleto={confirmarEmail} desabilitado={salvando} autoFocus />
        {mensagens}
        <Botao titulo="Confirmar novo e-mail" onPress={() => confirmarEmail()} carregando={salvando} />
        <Botao titulo="Cancelar troca" variante="texto" onPress={cancelarTroca} />
      </TelaPerfil>
    );
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
      {mudouEmail && pedeSenhaAtual && (
        <CampoTexto
          rotulo="Senha atual"
          value={senhaAtual}
          onChangeText={setSenhaAtual}
          secureTextEntry
          autoCapitalize="none"
          autoComplete="current-password"
        />
      )}
      {mudouEmail && (
        <Text style={[tipografia.descricao, styles.cinza]}>
          Enviaremos um código para o novo e-mail. O atual continua valendo até você confirmar.
        </Text>
      )}
      {mensagens}
      <Botao titulo="Salvar alterações" onPress={salvar} carregando={salvando} desabilitado={!mudou} />
      <OpcaoMenu titulo="Alterar senha" icone="lock" onPress={() => router.push('/alterar-senha')} />
    </TelaPerfil>
  );
}

const styles = StyleSheet.create({
  titulo: { color: cores.roxoEscuro },
  cinza: { color: cores.textoSuave },
  erro: { ...tipografia.corpo, color: cores.erro },
  sucesso: { ...tipografia.rotulo, color: cores.sucesso },
});
