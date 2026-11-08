import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import {
  codigoPerdido,
  confirmarEmail,
  enviarCodigoDeVerificacao,
  mensagemDoCodigo,
  segundosParaTentarDeNovo,
} from '../../../api/conta';
import { useSessao } from '../../../auth/SessaoProvider';
import { Botao } from '../../../components/ui/Botao';
import { CampoCodigo, DIGITOS_DO_CODIGO } from '../../../components/ui/CampoCodigo';
import { TelaPerfil } from '../../../components/ui/TelaPerfil';
import { mensagemDeErro } from '../../../hooks/useConsulta';
import { useContagem } from '../../../hooks/useContagem';
import { cores, espaco, tipografia } from '../../../theme/tokens';

const INTERVALO_REENVIO = 60;

// Figma "Esqueceu Senha" (cinco caixas de código), usada para confirmar o e-mail da conta
// logada: logo depois do cadastro ou, para contas antigas, a partir do Perfil.
export default function VerificarEmail() {
  const router = useRouter();
  const { enviado } = useLocalSearchParams<{ enviado?: string }>();
  const { usuario, atualizarUsuario } = useSessao();
  const [codigo, setCodigo] = useState('');
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [confirmado, setConfirmado] = useState(false);
  const reenvio = useContagem();
  const email = usuario?.email ?? '';

  // Código recém-enviado no cadastro: respeita o intervalo antes de liberar o reenvio.
  const { iniciar } = reenvio;
  useEffect(() => {
    if (enviado === '1') iniciar(INTERVALO_REENVIO);
  }, [enviado, iniciar]);

  async function confirmar(valor = codigo) {
    setErro(null);
    if (valor.length !== DIGITOS_DO_CODIGO) {
      setErro('Digite os 5 dígitos do código.');
      return;
    }
    setCarregando(true);
    try {
      const { data } = await confirmarEmail(email, valor);
      atualizarUsuario(data.usuario);
      setConfirmado(true);
    } catch (e) {
      setErro(mensagemDoCodigo(e) + (codigoPerdido(e) ? ' Toque em "Reenviar código".' : ''));
      setCodigo('');
    } finally {
      setCarregando(false);
    }
  }

  async function reenviar() {
    setErro(null);
    setCodigo('');
    setCarregando(true);
    try {
      const { data } = await enviarCodigoDeVerificacao(email);
      setAviso(data.mensagem);
      reenvio.iniciar(INTERVALO_REENVIO);
    } catch (e) {
      setErro(mensagemDeErro(e));
      const espera = segundosParaTentarDeNovo(e);
      if (espera) reenvio.iniciar(espera);
    } finally {
      setCarregando(false);
    }
  }

  function sair() {
    if (router.canGoBack()) router.back();
    else router.replace('/');
  }

  if (confirmado || usuario?.email_verificado) {
    return (
      <TelaPerfil usuario={usuario} onVoltar={sair}>
        <View style={styles.icone}>
          <MaterialIcons name="check-circle" size={64} color={cores.sucesso} />
        </View>
        <Text style={[tipografia.subtitulo, styles.titulo]} accessibilityRole="header">
          E-mail confirmado!
        </Text>
        <Text style={styles.texto}>Sua conta está pronta para recuperar a senha por e-mail quando precisar.</Text>
        <Botao titulo="Continuar" variante="destaque" onPress={sair} />
      </TelaPerfil>
    );
  }

  return (
    <TelaPerfil usuario={usuario} onVoltar={sair}>
      <Text style={[tipografia.subtitulo, styles.titulo]} accessibilityRole="header">
        Confirme seu e-mail
      </Text>
      <Text style={styles.texto}>
        Digite o código de 5 dígitos que enviamos para {email}. Ele vale por 30 minutos.
      </Text>
      <CampoCodigo valor={codigo} onChange={setCodigo} onCompleto={confirmar} desabilitado={carregando} autoFocus />
      {!!aviso && (
        <Text style={styles.aviso} accessibilityLiveRegion="polite">
          {aviso}
        </Text>
      )}
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      <Botao titulo="Confirmar" onPress={() => confirmar()} carregando={carregando} />
      <Botao
        titulo={reenvio.restante > 0 ? `Reenviar código em ${reenvio.restante} s` : 'Reenviar código'}
        variante="texto"
        onPress={reenviar}
        desabilitado={reenvio.restante > 0 || carregando}
      />
      <Botao titulo="Confirmar depois" variante="texto" onPress={sair} />
    </TelaPerfil>
  );
}

const styles = StyleSheet.create({
  icone: { alignItems: 'center', marginTop: espaco.md },
  titulo: { color: cores.roxoEscuro, textAlign: 'center' },
  texto: { ...tipografia.corpo, color: cores.textoSuave, textAlign: 'center' },
  aviso: { ...tipografia.corpo, color: cores.textoSuave, textAlign: 'center' },
  erro: { ...tipografia.corpo, color: cores.erro, textAlign: 'center' },
});
