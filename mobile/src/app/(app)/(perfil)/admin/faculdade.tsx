import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { atualizarFaculdade, criarFaculdade, excluirFaculdade, type DadosFaculdade } from '../../../../api/admin';
import { obterFaculdade } from '../../../../api/catalogo';
import { TIPOS_INSTITUICAO } from '../../../../catalogo/filtros';
import { limpo } from '../../../../catalogo/formatar';
import { ExigirAdmin } from '../../../../components/admin/ExigirAdmin';
import { confirmar } from '../../../../components/admin/confirmar';
import { GrupoFiltro } from '../../../../components/catalogo/GrupoFiltro';
import { Botao } from '../../../../components/ui/Botao';
import { CampoTexto } from '../../../../components/ui/CampoTexto';
import { Carregando, EstadoErro } from '../../../../components/ui/Estados';
import { Tela } from '../../../../components/ui/Tela';
import { mensagemDeErro, useConsulta } from '../../../../hooks/useConsulta';
import { cores, tipografia } from '../../../../theme/tokens';

type Campo = Exclude<keyof DadosFaculdade, 'tipo_instituicao'>;

// Campos do formulário "Cadastrar faculdade" do painel do site (tipo vai nos chips).
const CAMPOS: [Campo, string][] = [
  ['nome', 'Nome *'],
  ['sigla', 'Sigla'],
  ['codigo_emec', 'Código e-MEC'],
  ['organizacao_academica', 'Organização acadêmica'],
  ['cidade', 'Cidade'],
  ['uf', 'UF'],
  ['endereco', 'Endereço'],
  ['url', 'Site'],
  ['telefone', 'Telefone'],
  ['email', 'E-mail'],
  ['situacao', 'Situação'],
];

export default function FormFaculdade() {
  return (
    <ExigirAdmin titulo="Faculdade">
      <Conteudo />
    </ExigirAdmin>
  );
}

function Conteudo() {
  const router = useRouter();
  const { id: idParam } = useLocalSearchParams<{ id?: string }>();
  const id = idParam ? Number(idParam) : null;
  const atual = useConsulta(async () => (id ? (await obterFaculdade(id)).data : null), [id]);
  const [dados, setDados] = useState<DadosFaculdade>({ tipo_instituicao: 'Pública' });
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  // Preenche com os dados atuais (o "null" gravado pela importação vira vazio).
  useEffect(() => {
    if (!atual.dados) return;
    const f = atual.dados;
    const preenchido: DadosFaculdade = { tipo_instituicao: f.tipo_instituicao ?? 'Pública' };
    for (const [campo] of CAMPOS) preenchido[campo] = limpo((f as Record<string, unknown>)[campo] as string | null) ?? '';
    setDados(preenchido);
  }, [atual.dados]);

  if (id && !atual.dados) {
    return (
      <Tela cabecalho={{ titulo: 'Editar faculdade' }}>
        {atual.carregando ? <Carregando /> : <EstadoErro mensagem={atual.erro ?? 'Erro.'} onTentarNovamente={atual.recarregar} />}
      </Tela>
    );
  }

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

  const salvar = () => void executar(() => (id ? atualizarFaculdade(id, dados) : criarFaculdade(dados)));

  return (
    <Tela cabecalho={{ titulo: id ? 'Editar faculdade' : 'Cadastrar faculdade' }}>
      {CAMPOS.map(([campo, rotulo]) => (
        <CampoTexto
          key={campo}
          rotulo={rotulo}
          value={dados[campo] ?? ''}
          onChangeText={(v) => setDados((d) => ({ ...d, [campo]: v }))}
          autoCapitalize={campo === 'uf' ? 'characters' : campo === 'email' || campo === 'url' ? 'none' : 'sentences'}
          keyboardType={campo === 'email' ? 'email-address' : campo === 'url' ? 'url' : 'default'}
        />
      ))}
      <GrupoFiltro
        rotulo="Tipo de instituição"
        opcoes={TIPOS_INSTITUICAO}
        selecionados={[dados.tipo_instituicao ?? 'Pública']}
        onAlternar={(v) => setDados((d) => ({ ...d, tipo_instituicao: v }))}
      />
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      <Botao titulo={id ? 'Salvar alterações' : 'Cadastrar faculdade'} onPress={salvar} carregando={ocupado} />
      {!!id && (
        <Botao
          titulo="Excluir faculdade"
          variante="secundario"
          tamanho="compacto"
          icone="delete"
          desabilitado={ocupado}
          onPress={() =>
            confirmar('Excluir faculdade', `Excluir ${dados.nome}? Esta ação não pode ser desfeita.`, () =>
              void executar(() => excluirFaculdade(id)),
            )
          }
        />
      )}
    </Tela>
  );
}

const styles = StyleSheet.create({ erro: { ...tipografia.corpo, color: cores.erro } });
