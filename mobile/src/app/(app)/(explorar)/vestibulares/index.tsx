import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { listarCursos, listarVestibulares, type FiltrosVestibulares } from '../../../../api/catalogo';
import type { Vestibular } from '../../../../api/tipos';
import { dataPorExtenso, resumoProva } from '../../../../catalogo/datas';
import { alternarValor, INSTITUICOES_VESTIBULAR, MESES, REGIOES } from '../../../../catalogo/filtros';
import { plural } from '../../../../catalogo/formatar';
import { BotaoFavorito } from '../../../../components/catalogo/BotaoFavorito';
import { GrupoFiltro } from '../../../../components/catalogo/GrupoFiltro';
import { ListaPaginada } from '../../../../components/catalogo/ListaPaginada';
import { SemanaCalendario } from '../../../../components/catalogo/SemanaCalendario';
import { Botao } from '../../../../components/ui/Botao';
import { CampoBusca } from '../../../../components/ui/CampoBusca';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useAtrasado } from '../../../../hooks/useAtrasado';
import { useConsulta } from '../../../../hooks/useConsulta';
import { usePaginacao } from '../../../../hooks/usePaginacao';
import { cores, espaco, tipografia } from '../../../../theme/tokens';

const CALENDARIO_LIMITE = 100; // o catálogo tem dezenas de vestibulares: cabe numa página

// Calendário de vestibulares (Figma "Vestibulares" + filtros da página /vestibulares do site).
export default function Vestibulares() {
  const router = useRouter();
  const hoje = useMemo(() => new Date(), []);
  const [referencia, setReferencia] = useState(hoje);
  const [diaSelecionado, setDiaSelecionado] = useState<string | null>(null);
  const [texto, setTexto] = useState('');
  const [instituicao, setInstituicao] = useState<string[]>(['Todas']);
  const [regioes, setRegioes] = useState<string[]>([]);
  const [meses, setMeses] = useState<string[]>([]);
  const [curso, setCurso] = useState<string[]>([]);
  const busca = useAtrasado(texto.trim());

  const filtros: FiltrosVestibulares = {
    busca,
    instituicao: (instituicao[0] ?? 'Todas') as FiltrosVestibulares['instituicao'],
    regiao: regioes,
    mes: meses.map(Number),
    curso: curso[0],
  };
  const pagina = usePaginacao((p) => listarVestibulares(filtros, p), [
    busca, instituicao.join(), regioes.join(), meses.join(), curso.join(),
  ]);

  // Calendário: todas as provas (sem filtros) para marcar os dias da semana.
  const calendario = useConsulta(() => listarVestibulares({}, 1, CALENDARIO_LIMITE), []);
  const porDia = useMemo(() => {
    const mapa = new Map<string, Vestibular[]>();
    for (const v of calendario.dados?.data ?? []) {
      if (!v.data_prova) continue;
      mapa.set(v.data_prova, [...(mapa.get(v.data_prova) ?? []), v]);
    }
    return mapa;
  }, [calendario.dados]);

  // Cursos reais do banco para o filtro "Curso" (como o site faz).
  const cursos = useConsulta(() => listarCursos({}, 1, 50), []);
  const opcoesCurso = useMemo(
    () =>
      [...new Set((cursos.dados?.data ?? []).map((c) => c.nome))]
        .sort((a, b) => a.localeCompare(b, 'pt-BR'))
        .map((nome) => ({ rotulo: nome, valor: nome })),
    [cursos.dados],
  );

  const temFiltro = !!texto || instituicao[0] !== 'Todas' || regioes.length + meses.length + curso.length > 0;
  function limpar() {
    setTexto('');
    setInstituicao(['Todas']);
    setRegioes([]);
    setMeses([]);
    setCurso([]);
  }

  function mudarSemana(delta: -1 | 1) {
    setReferencia((r) => new Date(r.getFullYear(), r.getMonth(), r.getDate() + delta * 7));
    setDiaSelecionado(null);
  }

  const doDia = diaSelecionado ? (porDia.get(diaSelecionado) ?? []) : [];
  const abrir = (v: Vestibular) => router.push(`/vestibulares/${v.id}`);

  return (
    <Tela cabecalho={{ titulo: 'Vestibulares' }} rolar={false}>
      <ListaPaginada<Vestibular>
        pagina={pagina}
        chave={(v) => String(v.id)}
        contagem={(n) => plural(n, 'vestibular encontrado', 'vestibulares encontrados')}
        vazio={{ titulo: 'Nenhum vestibular encontrado', mensagem: 'Tente outra busca ou remova filtros.' }}
        cabecalho={
          <>
            <Text style={styles.hoje}>{dataPorExtenso(hoje)}</Text>
            <SemanaCalendario
              referencia={referencia}
              hoje={hoje}
              selecionado={diaSelecionado}
              marcados={new Set(porDia.keys())}
              onSelecionar={setDiaSelecionado}
              onMudarSemana={mudarSemana}
            />
            {!!diaSelecionado && (
              <View style={styles.doDia}>
                {doDia.length === 0 ? (
                  <Text style={styles.aviso}>Nenhuma prova neste dia.</Text>
                ) : (
                  doDia.map((v) => (
                    <LinhaLista key={v.id} titulo={v.nome} subtitulo={v.instituicao ?? undefined} icone="event" onPress={() => abrir(v)} />
                  ))
                )}
              </View>
            )}

            <Text style={[tipografia.tituloBloco, styles.titulo]} accessibilityRole="header">
              Próximos vestibulares
            </Text>
            <CampoBusca
              placeholder="Vestibular, instituição, cidade ou curso..."
              value={texto}
              onChangeText={setTexto}
              autoCapitalize="none"
            />
            <GrupoFiltro
              rotulo="Instituição"
              opcoes={INSTITUICOES_VESTIBULAR}
              selecionados={instituicao}
              onAlternar={(v) => setInstituicao([v])}
            />
            <GrupoFiltro rotulo="Região" opcoes={REGIOES} selecionados={regioes} onAlternar={(v) => setRegioes((r) => alternarValor(r, v))} />
            <GrupoFiltro rotulo="Mês da prova" opcoes={MESES} selecionados={meses} onAlternar={(v) => setMeses((m) => alternarValor(m, v))} />
            {opcoesCurso.length > 0 && (
              <GrupoFiltro
                rotulo="Curso"
                opcoes={opcoesCurso}
                selecionados={curso}
                onAlternar={(v) => setCurso((c) => (c[0] === v ? [] : [v]))}
              />
            )}
            {temFiltro && <Botao titulo="Limpar filtros" variante="texto" onPress={limpar} />}
          </>
        }
        renderItem={(v) => (
          <LinhaLista
            titulo={v.nome}
            subtitulo={resumoProva(v, hoje)}
            icone="event"
            onPress={() => abrir(v)}
            acessorio={<BotaoFavorito tipo="vestibular" id={v.id} nome={v.nome} />}
          />
        )}
      />
    </Tela>
  );
}

const styles = StyleSheet.create({
  hoje: { ...tipografia.legenda, fontSize: 14, color: cores.textoSuave, marginTop: -espaco.sm },
  doDia: { gap: espaco.smd },
  aviso: { ...tipografia.descricao, color: cores.textoSuave },
  titulo: { color: cores.roxoEscuro, marginTop: espaco.sm },
});
