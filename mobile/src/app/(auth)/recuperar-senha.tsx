import { useRouter } from 'expo-router';
import { useRef, useState } from 'react';
import { StyleSheet, Text, TextInput } from 'react-native';

import { ApiError } from '../../api/client';
import {
  codigoPerdido,
  mensagemDoCodigo,
  redefinirSenha,
  segundosParaTentarDeNovo,
  solicitarRecuperacao,
  validarCodigoDeRecuperacao,
} from '../../api/conta';
import { Botao } from '../../components/ui/Botao';
import { CampoCodigo, DIGITOS_DO_CODIGO } from '../../components/ui/CampoCodigo';
import { CampoTexto } from '../../components/ui/CampoTexto';
import { TelaAuth } from '../../components/ui/TelaAuth';
import { mensagemDeErro } from '../../hooks/useConsulta';
import { useContagem } from '../../hooks/useContagem';
import { cores, tipografia } from '../../theme/tokens';

const INTERVALO_REENVIO = 60;
type Passo = 'email' | 'codigo' | 'senha';

// Figma "Verificar" (e-mail) → "Esqueceu Senha" (código de 5 dígitos) → nova senha →
// "Senha alterada". Tudo é validado pelo servidor; as respostas de envio são genéricas.
export default function RecuperarSenha() {
  const router = useRouter();
  const [passo, setPasso] = useState<Passo>('email');
  const [email, setEmail] = useState('');
  const [codigo, setCodigo] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const reenvio = useContagem();
  const campoConfirmacao = useRef<TextInput>(null);

  async function pedirCodigo(): Promise<boolean> {
    try {
      const { data } = await solicitarRecuperacao(email.trim());
      setAviso(data.mensagem);
      reenvio.iniciar(INTERVALO_REENVIO);
      return true;
    } catch (e) {
      setErro(mensagemDeErro(e));
      const espera = segundosParaTentarDeNovo(e);
      if (espera) reenvio.iniciar(espera);
      return false;
    }
  }

  async function enviarEmail() {
    setErro(null);
    if (!email.trim()) {
      setErro('Informe o e-mail da sua conta.');
      return;
    }
    setCarregando(true);
    const ok = await pedirCodigo();
    setCarregando(false);
    if (ok) setPasso('codigo');
  }

  async function reenviar() {
    setErro(null);
    setCodigo('');
    setCarregando(true);
    await pedirCodigo();
    setCarregando(false);
  }

  async function conferirCodigo(valor = codigo) {
    setErro(null);
    if (valor.length !== DIGITOS_DO_CODIGO) {
      setErro('Digite os 5 dígitos do código.');
      return;
    }
    setCarregando(true);
    try {
      await validarCodigoDeRecuperacao(email.trim(), valor);
      setAviso(null);
      setPasso('senha');
    } catch (e) {
      setErro(mensagemDoCodigo(e));
      setCodigo('');
    } finally {
      setCarregando(false);
    }
  }

  async function salvarSenha() {
    setErro(null);
    if (!senha) {
      setErro('Informe a nova senha.');
      return;
    }
    if (senha !== confirmacao) {
      setErro('A confirmação não confere com a nova senha.');
      return;
    }
    setCarregando(true);
    try {
      await redefinirSenha(email.trim(), codigo, senha, confirmacao);
      router.replace('/senha-alterada');
    } catch (e) {
      setErro(mensagemDoCodigo(e));
      // Código vencido/usado no meio do caminho: volta para pedir outro.
      if (codigoPerdido(e) || (e instanceof ApiError && e.code === 'INVALID_CODE')) {
        setCodigo('');
        setPasso('codigo');
      }
      setCarregando(false);
    }
  }

  function trocarEmail() {
    setErro(null);
    setAviso(null);
    setCodigo('');
    setPasso('email');
  }

  const mensagens = (
    <>
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
    </>
  );

  if (passo === 'codigo') {
    return (
      <TelaAuth variante="roxo" titulo="Digite o código">
        <Text style={styles.texto}>Enviamos um código de 5 dígitos para {email.trim()}. Ele vale por 15 minutos.</Text>
        <CampoCodigo valor={codigo} onChange={setCodigo} onCompleto={conferirCodigo} desabilitado={carregando} autoFocus />
        {mensagens}
        <Botao titulo="Continuar" variante="destaque" onPress={() => conferirCodigo()} carregando={carregando} />
        <Botao
          titulo={reenvio.restante > 0 ? `Reenviar código em ${reenvio.restante} s` : 'Reenviar código'}
          variante="texto"
          onPress={reenviar}
          desabilitado={reenvio.restante > 0 || carregando}
        />
        <Botao titulo="Usar outro e-mail" variante="texto" onPress={trocarEmail} />
      </TelaAuth>
    );
  }

  if (passo === 'senha') {
    return (
      <TelaAuth variante="roxo" titulo="Nova senha">
        <Text style={styles.texto}>
          Use pelo menos 8 caracteres, com letras e números. As sessões abertas da conta serão encerradas.
        </Text>
        <CampoTexto
          rotulo="Nova senha"
          placeholder="Insira a nova senha"
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
          placeholder="Insira a nova senha"
          value={confirmacao}
          onChangeText={setConfirmacao}
          secureTextEntry
          autoCapitalize="none"
          autoComplete="new-password"
          returnKeyType="go"
          onSubmitEditing={salvarSenha}
        />
        {mensagens}
        <Botao titulo="Salvar nova senha" variante="destaque" onPress={salvarSenha} carregando={carregando} />
      </TelaAuth>
    );
  }

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
        autoComplete="email"
        autoCorrect={false}
        returnKeyType="go"
        onSubmitEditing={enviarEmail}
      />
      {mensagens}
      <Botao titulo="Enviar" variante="destaque" onPress={enviarEmail} carregando={carregando} />
      <Botao titulo="Cancelar" variante="texto" onPress={() => router.back()} />
    </TelaAuth>
  );
}

const styles = StyleSheet.create({
  texto: { ...tipografia.rotulo, color: cores.roxoEscuro, textAlign: 'center' },
  aviso: { ...tipografia.corpo, color: cores.textoSuave, textAlign: 'center' },
  erro: { ...tipografia.corpo, color: cores.erro, textAlign: 'center' },
});
