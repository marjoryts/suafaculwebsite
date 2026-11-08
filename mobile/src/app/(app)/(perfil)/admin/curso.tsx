import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { criarCurso, type DadosCurso } from '../../../../api/admin';
import { listarFaculdades } from '../../../../api/catalogo';
import type { Faculdade } from '../../../../api/tipos';
import { AREAS, MODALIDADES_CURSO, TIPOS_INSTITUICAO } from '../../../../catalogo/filtros';
import { juntar, local } from '../../../../catalogo/formatar';
import { ExigirAdmin } from '../../../../components/admin/ExigirAdmin';
import { GrupoFiltro } from '../../../../components/catalogo/GrupoFiltro';
import { Botao } from '../../../../components/ui/Botao';
import { CampoBusca } from '../../../../components/ui/CampoBusca';
import { CampoTexto } from '../../../../components/ui/CampoTexto';
import { Chip } from '../../../../components/ui/Chip';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useAtrasado } from '../../../../hooks/useAtrasado';
import { mensagemDeErro, useConsulta } from '../../../../hooks/useConsulta';
import { cores, espaco, tipografia } from '../../../../theme/tokens';

type Texto = Exclude<keyof DadosCurso, 'faculdade_id' | 'area' | 'modalidade' | 'tipo_instituicao'>;
const CAMPOS: [Texto, string][] = [
  ['nome', 'Nome do curso *'],
  ['instituicao', 'Instituição *'],
  ['grau', 'Grau (ex.: Bacharelado)'],
  ['duracao', 'Duração (ex.: 4 anos)'],
  ['descricao', 'Descrição'],
];

// Formulário "Cadastrar curso" do painel: vinculado a uma faculdade (busca), com
// área, modalidade e tipo de instituição nas mesmas opções do site.
export default function FormCurso() {
  return (
    <ExigirAdmin titulo="Cadastrar curso">
      <Conteudo />
    </ExigirAdmin>
  );
}

function Conteudo() {
  const router = useRouter();
  const [dados, setDados] = useState<DadosCurso>({ area: 'Tecnologia', modalidade: 'presencial', tipo_instituicao: 'Pública' });
  const [faculdade, setFaculdade] = useState<Faculdade | null>(null);
  const [busca, setBusca] = useState('');
  const termo = useAtrasado(busca.trim());
  const resultados = useConsulta(
    async () => (termo.length >= 2 ? (await listarFaculdades({ busca: termo }, 1, 5)).data : []),
    [termo],
  );
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  function vincular(f: Faculdade) {
    setFaculdade(f);
    setBusca('');
    // Como no site: a instituição e o tipo seguem a faculdade escolhida.
    setDados((d) => ({ ...d, instituicao: d.instituicao || f.nome, tipo_instituicao: f.tipo_instituicao ?? d.tipo_instituicao }));
  }

  async function salvar() {
    setErro(null);
    setOcupado(true);
    try {
      await criarCurso({ ...dados, faculdade_id: faculdade?.id ?? null });
      router.back();
    } catch (e) {
      setErro(mensagemDeErro(e));
      setOcupado(false);
    }
  }

  const definir = (campo: keyof DadosCurso) => (v: string) => setDados((d) => ({ ...d, [campo]: v }));

  return (
    <Tela cabecalho={{ titulo: 'Cadastrar curso' }}>
      <Text style={[tipografia.rotulo, styles.roxo]}>Faculdade vinculada</Text>
      {faculdade ? (
        <View style={styles.linha}>
          <Chip titulo={faculdade.nome} icone="close" onPress={() => setFaculdade(null)} />
        </View>
      ) : (
        <>
          <CampoBusca placeholder="Busque a faculdade..." value={busca} onChangeText={setBusca} autoCapitalize="none" />
          {(resultados.dados ?? []).map((f) => (
            <LinhaLista key={f.id} titulo={f.nome} subtitulo={juntar(local(f.cidade, f.uf), f.tipo_instituicao)} icone="school" onPress={() => vincular(f)} />
          ))}
        </>
      )}
      {CAMPOS.map(([campo, rotulo]) => (
        <CampoTexto key={campo} rotulo={rotulo} value={dados[campo] ?? ''} onChangeText={definir(campo)} multiline={campo === 'descricao'} />
      ))}
      <GrupoFiltro rotulo="Área" opcoes={AREAS} selecionados={[dados.area ?? '']} onAlternar={definir('area')} />
      <GrupoFiltro rotulo="Modalidade" opcoes={MODALIDADES_CURSO} selecionados={[dados.modalidade ?? '']} onAlternar={definir('modalidade')} />
      <GrupoFiltro rotulo="Tipo de instituição" opcoes={TIPOS_INSTITUICAO} selecionados={[dados.tipo_instituicao ?? '']} onAlternar={definir('tipo_instituicao')} />
      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}
      <Botao titulo="Cadastrar curso" onPress={salvar} carregando={ocupado} />
    </Tela>
  );
}

const styles = StyleSheet.create({
  roxo: { color: cores.roxoEscuro },
  linha: { flexDirection: 'row', gap: espaco.sm },
  erro: { ...tipografia.corpo, color: cores.erro },
});
