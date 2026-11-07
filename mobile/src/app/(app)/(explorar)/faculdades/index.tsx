import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { listarFaculdades } from '../../../../api/catalogo';
import type { Faculdade } from '../../../../api/tipos';
import { alternarValor, MODALIDADES_FACULDADE, TIPOS_INSTITUICAO } from '../../../../catalogo/filtros';
import { juntar, local, plural } from '../../../../catalogo/formatar';
import { BotaoFavorito } from '../../../../components/catalogo/BotaoFavorito';
import { GrupoFiltro } from '../../../../components/catalogo/GrupoFiltro';
import { ListaPaginada } from '../../../../components/catalogo/ListaPaginada';
import { Botao } from '../../../../components/ui/Botao';
import { CampoBusca } from '../../../../components/ui/CampoBusca';
import { Chip } from '../../../../components/ui/Chip';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useAtrasado } from '../../../../hooks/useAtrasado';
import { usePaginacao } from '../../../../hooks/usePaginacao';
import { espaco } from '../../../../theme/tokens';

type Params = { busca?: string; cidade?: string; curso?: string; tipo?: string };

// Lista de faculdades (GET /faculdades) com os filtros da página /faculdades do website.
// "cidade" (cidade, UF ou região) e "curso" chegam da busca e aparecem como chips removíveis.
export default function Faculdades() {
  const router = useRouter();
  const params = useLocalSearchParams<Params>();
  const [texto, setTexto] = useState(params.busca ?? '');
  const [tipo, setTipo] = useState<string[]>(params.tipo ? [params.tipo] : []);
  const [modalidades, setModalidades] = useState<string[]>([]);
  const [cidade, setCidade] = useState(params.cidade ?? '');
  const [curso, setCurso] = useState(params.curso ?? '');
  const busca = useAtrasado(texto.trim());

  const pagina = usePaginacao(
    (p) =>
      listarFaculdades({ busca, tipo_instituicao: tipo[0], modalidade: modalidades, cidade, curso }, p),
    [busca, tipo.join(), modalidades.join(), cidade, curso],
  );
  const temFiltro = !!(texto || cidade || curso) || tipo.length + modalidades.length > 0;

  function limpar() {
    setTexto('');
    setTipo([]);
    setModalidades([]);
    setCidade('');
    setCurso('');
  }

  return (
    <Tela cabecalho={{ titulo: 'Faculdades' }} rolar={false}>
      <ListaPaginada<Faculdade>
        pagina={pagina}
        chave={(f) => String(f.id)}
        contagem={(n) => plural(n, 'faculdade encontrada', 'faculdades encontradas')}
        vazio={{ titulo: 'Nenhuma faculdade encontrada', mensagem: 'Tente outra busca ou remova filtros.' }}
        cabecalho={
          <>
            <CampoBusca
              placeholder="Nome, sigla ou cidade..."
              value={texto}
              onChangeText={setTexto}
              autoCapitalize="none"
            />
            {(!!cidade || !!curso) && (
              <View style={styles.ativos}>
                {!!cidade && (
                  <Chip titulo={`Local: ${cidade}`} icone="close" onPress={() => setCidade('')} />
                )}
                {!!curso && <Chip titulo={`Curso: ${curso}`} icone="close" onPress={() => setCurso('')} />}
              </View>
            )}
            <GrupoFiltro
              rotulo="Instituição"
              opcoes={TIPOS_INSTITUICAO}
              selecionados={tipo}
              onAlternar={(v) => setTipo((t) => (t[0] === v ? [] : [v]))}
            />
            <GrupoFiltro
              rotulo="Modalidade dos cursos"
              opcoes={MODALIDADES_FACULDADE}
              selecionados={modalidades}
              onAlternar={(v) => setModalidades((m) => alternarValor(m, v))}
            />
            {temFiltro && <Botao titulo="Limpar filtros" variante="texto" onPress={limpar} />}
          </>
        }
        renderItem={(f) => (
          <LinhaLista
            titulo={f.nome}
            subtitulo={juntar(local(f.cidade, f.uf), f.tipo_instituicao)}
            icone="school"
            onPress={() => router.push(`/faculdades/${f.id}`)}
            acessorio={<BotaoFavorito tipo="faculdade" id={f.id} nome={f.nome} />}
          />
        )}
      />
    </Tela>
  );
}

const styles = StyleSheet.create({
  ativos: { flexDirection: 'row', flexWrap: 'wrap', gap: espaco.sm },
});
