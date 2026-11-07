import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { atualizarUsuario, criarUsuario, excluirUsuario } from '../../../../api/admin';
import { ExigirAdmin } from '../../../../components/admin/ExigirAdmin';
import { confirmar } from '../../../../components/admin/confirmar';
import { GrupoFiltro } from '../../../../components/catalogo/GrupoFiltro';
import { Botao } from '../../../../components/ui/Botao';
import { CampoTexto } from '../../../../components/ui/CampoTexto';
import { Tela } from '../../../../components/ui/Tela';
import { mensagemDeErro } from '../../../../hooks/useConsulta';
import { cores, tipografia } from '../../../../theme/tokens';

const TIPOS = [
  { rotulo: 'Aluno', valor: 'aluno' },
  { rotulo: 'Administrador', valor: 'admin' },
];

type Params = { id?: string; nome_usuario?: string; email?: string; tipo?: string };

// Formulário "Adicionar/Editar usuário" do painel. Regras (e-mail válido, senha mínima,
// duplicidade, não remover o próprio acesso, não se excluir) ficam no servidor.
export default function FormUsuario() {
  return (
    <ExigirAdmin titulo="Usuário">
      <Conteudo />
    </ExigirAdmin>
  );
}

function Conteudo() {
  const router = useRouter();
  const p = useLocalSearchParams<Params>();
  const id = p.id ? Number(p.id) : null;
  const [nome, setNome] = useState(p.nome_usuario ?? '');
  const [email, setEmail] = useState(p.email ?? '');
  const [senha, setSenha] = useState('');
  const [tipo, setTipo] = useState<'aluno' | 'admin'>(p.tipo === 'admin' ? 'admin' : 'aluno');
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function executar(acao: () => Promise<unknown>) {
    setErro(null);
    setOcupado(true);
    try {
      await acao();
      router.back();
    } catch (e) {
      setErro(mensagemDeErro(e));
      setOcupado(false);
    }
  }

  function salvar() {
    const dados = { nome_usuario: nome.trim(), email: email.trim(), tipo, ...(senha ? { password: senha } : {}) };
    void executar(() => (id ? atualizarUsuario(id, dados) : criarUsuario({ ...dados, password: senha })));
  }

  return (
    <Tela cabecalho={{ titulo: id ? 'Editar usuário' : 'Adicionar usuário' }}>
      <CampoTexto rotulo="Nome de usuário" value={nome} onChangeText={setNome} autoCapitalize="none" autoCorrect={false} />
      <CampoTexto rotulo="E-mail" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoCorrect={false} />
      <CampoTexto
        rotulo={id ? 'Nova senha (deixe em branco para manter)' : 'Senha'}
        value={senha}
        onChangeText={setSenha}
        secureTextEntry
        autoCapitalize="none"
      />
      <GrupoFiltro rotulo="Tipo de acesso" opcoes={TIPOS} selecionados={[tipo]} onAlternar={(v) => setTipo(v as 'aluno' | 'admin')} />
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      <Botao titulo={id ? 'Salvar alterações' : 'Criar usuário'} onPress={salvar} carregando={ocupado} />
      {!!id && (
        <Botao
          titulo="Excluir usuário"
          variante="secundario"
          tamanho="compacto"
          icone="delete"
          desabilitado={ocupado}
          onPress={() =>
            confirmar('Excluir usuário', `Excluir ${nome}? Esta ação não pode ser desfeita.`, () =>
              void executar(() => excluirUsuario(id)),
            )
          }
        />
      )}
    </Tela>
  );
}

const styles = StyleSheet.create({ erro: { ...tipografia.corpo, color: cores.erro } });
