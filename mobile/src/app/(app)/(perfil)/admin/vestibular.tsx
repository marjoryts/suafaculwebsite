import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { criarVestibular, type DadosVestibular } from '../../../../api/admin';
import { REGIOES, TIPOS_INSTITUICAO } from '../../../../catalogo/filtros';
import { ExigirAdmin } from '../../../../components/admin/ExigirAdmin';
import { GrupoFiltro } from '../../../../components/catalogo/GrupoFiltro';
import { Botao } from '../../../../components/ui/Botao';
import { CampoTexto } from '../../../../components/ui/CampoTexto';
import { Tela } from '../../../../components/ui/Tela';
import { mensagemDeErro } from '../../../../hooks/useConsulta';
import { cores, tipografia } from '../../../../theme/tokens';

type Texto = Exclude<keyof DadosVestibular, 'tipo_instituicao' | 'regiao'>;

// Campos do formulário "Cadastrar vestibular" do painel do site (com taxa, cursos e requisitos).
const CAMPOS: [Texto, string, boolean?][] = [
  ['nome', 'Nome do vestibular *'],
  ['instituicao', 'Instituição *'],
  ['cidade', 'Cidade'],
  ['periodo_inscricao', 'Período de inscrição'],
  ['data_prova', 'Data da prova (AAAA-MM-DD)'],
  ['taxa_inscricao', 'Taxa de inscrição'],
  ['link_edital', 'Link do edital'],
  ['descricao', 'Descrição', true],
  ['cursos_oferecidos', 'Cursos e vagas', true],
  ['requisitos', 'Requisitos', true],
];

export default function FormVestibular() {
  return (
    <ExigirAdmin titulo="Cadastrar vestibular">
      <Conteudo />
    </ExigirAdmin>
  );
}

function Conteudo() {
  const router = useRouter();
  const [dados, setDados] = useState<DadosVestibular>({ tipo_instituicao: 'Pública', regiao: 'Sudeste' });
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function salvar() {
    setErro(null);
    setOcupado(true);
    try {
      await criarVestibular(dados);
      router.back();
    } catch (e) {
      setErro(mensagemDeErro(e));
      setOcupado(false);
    }
  }

  const definir = (campo: keyof DadosVestibular) => (v: string) => setDados((d) => ({ ...d, [campo]: v }));

  return (
    <Tela cabecalho={{ titulo: 'Cadastrar vestibular' }}>
      {CAMPOS.map(([campo, rotulo, longo]) => (
        <CampoTexto
          key={campo}
          rotulo={rotulo}
          value={dados[campo] ?? ''}
          onChangeText={definir(campo)}
          multiline={!!longo}
          autoCapitalize={campo === 'link_edital' ? 'none' : 'sentences'}
          keyboardType={campo === 'link_edital' ? 'url' : campo === 'data_prova' ? 'numbers-and-punctuation' : 'default'}
        />
      ))}
      <GrupoFiltro rotulo="Tipo de instituição" opcoes={TIPOS_INSTITUICAO} selecionados={[dados.tipo_instituicao ?? '']} onAlternar={definir('tipo_instituicao')} />
      <GrupoFiltro rotulo="Região" opcoes={REGIOES} selecionados={[dados.regiao ?? '']} onAlternar={definir('regiao')} />
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      <Botao titulo="Cadastrar vestibular" onPress={salvar} carregando={ocupado} />
    </Tela>
  );
}

const styles = StyleSheet.create({ erro: { ...tipografia.corpo, color: cores.erro } });
