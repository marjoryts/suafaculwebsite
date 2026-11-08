import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';

import { listarCursos } from '../../../../api/catalogo';
import type { Curso } from '../../../../api/tipos';
import { AREAS, alternarValor, MODALIDADES_CURSO, TIPOS_INSTITUICAO } from '../../../../catalogo/filtros';
import { juntar, modalidade, plural } from '../../../../catalogo/formatar';
import { BotaoFavorito } from '../../../../components/catalogo/BotaoFavorito';
import { GrupoFiltro } from '../../../../components/catalogo/GrupoFiltro';
import { ListaPaginada } from '../../../../components/catalogo/ListaPaginada';
import { Botao } from '../../../../components/ui/Botao';
import { CampoBusca } from '../../../../components/ui/CampoBusca';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useAtrasado } from '../../../../hooks/useAtrasado';
import { usePaginacao } from '../../../../hooks/usePaginacao';

// Lista de cursos (GET /cursos) com os mesmos filtros da página /cursos do website.
export default function Cursos() {
  const router = useRouter();
  const params = useLocalSearchParams<{ busca?: string; area?: string }>();
  const [texto, setTexto] = useState(params.busca ?? '');
  const [area, setArea] = useState<string[]>(params.area ? [params.area] : []);
  const [modalidades, setModalidades] = useState<string[]>([]);
  const [tipos, setTipos] = useState<string[]>([]);
  const busca = useAtrasado(texto.trim());

  const pagina = usePaginacao(
    (p) => listarCursos({ busca, area: area[0], modalidade: modalidades, tipo_instituicao: tipos }, p),
    [busca, area.join(), modalidades.join(), tipos.join()],
  );
  const temFiltro = !!texto || area.length + modalidades.length + tipos.length > 0;

  function limpar() {
    setTexto('');
    setArea([]);
    setModalidades([]);
    setTipos([]);
  }

  return (
    <Tela cabecalho={{ titulo: 'Cursos' }} rolar={false}>
      <ListaPaginada<Curso>
        pagina={pagina}
        chave={(c) => String(c.id)}
        contagem={(n) => plural(n, 'curso encontrado', 'cursos encontrados')}
        vazio={{ titulo: 'Nenhum curso encontrado', mensagem: 'Tente outra busca ou remova filtros.' }}
        cabecalho={
          <>
            <CampoBusca
              placeholder="Pesquise cursos..."
              value={texto}
              onChangeText={setTexto}
              autoCapitalize="none"
            />
            {/* Área é escolha única, como no site ("Todas as áreas" = nenhuma). */}
            <GrupoFiltro
              rotulo="Área"
              opcoes={AREAS}
              selecionados={area}
              onAlternar={(v) => setArea((a) => (a[0] === v ? [] : [v]))}
            />
            <GrupoFiltro
              rotulo="Modalidade"
              opcoes={MODALIDADES_CURSO}
              selecionados={modalidades}
              onAlternar={(v) => setModalidades((m) => alternarValor(m, v))}
            />
            <GrupoFiltro
              rotulo="Instituição"
              opcoes={TIPOS_INSTITUICAO}
              selecionados={tipos}
              onAlternar={(v) => setTipos((t) => alternarValor(t, v))}
            />
            {temFiltro && <Botao titulo="Limpar filtros" variante="texto" onPress={limpar} />}
          </>
        }
        renderItem={(c) => (
          <LinhaLista
            titulo={c.nome}
            subtitulo={juntar(c.instituicao, modalidade(c.modalidade), c.grau)}
            icone="menu-book"
            onPress={() => router.push(`/cursos/${c.id}`)}
            acessorio={<BotaoFavorito tipo="curso" id={c.id} nome={c.nome} />}
          />
        )}
      />
    </Tela>
  );
}
