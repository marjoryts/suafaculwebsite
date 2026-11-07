import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { listarCursos, listarFaculdades, listarVestibulares } from '../../../api/catalogo';
import type { Favorito } from '../../../api/tipos';
import { diasAte, resumoProva } from '../../../catalogo/datas';
import { local, nomeCurto } from '../../../catalogo/formatar';
import { CartaoDestaque } from '../../../components/catalogo/CartaoDestaque';
import { SecaoHorizontal } from '../../../components/catalogo/SecaoHorizontal';
import { Avatar } from '../../../components/ui/Avatar';
import { CampoBusca } from '../../../components/ui/CampoBusca';
import { Chip } from '../../../components/ui/Chip';
import { LinhaLista } from '../../../components/ui/LinhaLista';
import { Tela } from '../../../components/ui/Tela';
import { useSessao } from '../../../auth/SessaoProvider';
import { useFavoritos } from '../../../favoritos/FavoritosProvider';
import { useConsulta } from '../../../hooks/useConsulta';
import { cores, espaco, tipografia } from '../../../theme/tokens';

const POR_SECAO = 8;
const CHIPS_SALVOS = 6;

// Home do Explorar (Figma "Primeira/Segunda Tela Inicial"): saudação, busca, atalhos para
// os itens salvos e seções com dados reais do catálogo. O Figma usa fotos nos cards; o
// banco não tem imagens, então os cards usam os tons de roxo do design.
export default function ExplorarHome() {
  const router = useRouter();
  const { usuario } = useSessao();
  const { favoritos } = useFavoritos();

  const publicas = useConsulta(() => listarFaculdades({ tipo_instituicao: 'Pública' }, 1, POR_SECAO), []);
  const privadas = useConsulta(() => listarFaculdades({ tipo_instituicao: 'Privada' }, 1, POR_SECAO), []);
  const cursos = useConsulta(() => listarCursos({}, 1, POR_SECAO), []);
  // Como a página inicial do site: só provas de hoje em diante, da mais próxima para a mais distante.
  const vestibulares = useConsulta(async () => {
    const { data } = await listarVestibulares({}, 1, 40);
    return data.filter((v) => (diasAte(v.data_prova) ?? -1) >= 0).slice(0, POR_SECAO);
  }, []);

  const salvos = favoritos.slice(0, CHIPS_SALVOS);

  function abrirSalvo(f: Favorito) {
    const rota = { curso: 'cursos', faculdade: 'faculdades', vestibular: 'vestibulares' }[f.tipo];
    router.push(`/${rota}/${f.item_id}`);
  }

  return (
    <Tela>
      <View style={styles.saudacao}>
        <Avatar nome={usuario?.nome_usuario} url={usuario?.avatar_url} />
        <Text style={[tipografia.saudacao, styles.ola]} numberOfLines={1}>
          Olá, {usuario?.nome_usuario ?? 'estudante'}!
        </Text>
      </View>
      <CampoBusca onPress={() => router.push('/busca')} />

      {salvos.length > 0 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.rolagem}
          contentContainerStyle={styles.chips}
          accessibilityLabel="Seus salvos"
        >
          {salvos.map((f) => (
            <Chip
              key={`${f.tipo}:${f.item_id}`}
              titulo={f.nome_item}
              icone="favorite"
              selecionado={false}
              onPress={() => abrirSalvo(f)}
            />
          ))}
        </ScrollView>
      )}

      <SecaoHorizontal
        titulo="Faculdades Públicas"
        onVerTodos={() => router.push({ pathname: '/faculdades', params: { tipo: 'Pública' } })}
        carregando={publicas.carregando}
        erro={publicas.erro}
        onTentarNovamente={publicas.recarregar}
      >
        {publicas.dados?.data.map((f, i) => (
          <CartaoDestaque
            key={f.id}
            indice={i}
            titulo={nomeCurto(f)}
            subtitulo={local(f.cidade, f.uf)}
            onPress={() => router.push(`/faculdades/${f.id}`)}
            favorito={{ tipo: 'faculdade', id: f.id }}
          />
        ))}
      </SecaoHorizontal>

      <SecaoHorizontal
        titulo="Faculdades Privadas"
        onVerTodos={() => router.push({ pathname: '/faculdades', params: { tipo: 'Privada' } })}
        carregando={privadas.carregando}
        erro={privadas.erro}
        onTentarNovamente={privadas.recarregar}
      >
        {privadas.dados?.data.map((f, i) => (
          <CartaoDestaque
            key={f.id}
            indice={i + 1}
            titulo={nomeCurto(f)}
            subtitulo={local(f.cidade, f.uf)}
            onPress={() => router.push(`/faculdades/${f.id}`)}
            favorito={{ tipo: 'faculdade', id: f.id }}
          />
        ))}
      </SecaoHorizontal>

      <SecaoHorizontal
        titulo="Cursos"
        onVerTodos={() => router.push('/cursos')}
        carregando={cursos.carregando}
        erro={cursos.erro}
        onTentarNovamente={cursos.recarregar}
        vazio={cursos.dados && cursos.dados.data.length === 0 ? 'Nenhum curso cadastrado ainda.' : undefined}
      >
        {cursos.dados?.data.map((c, i) => (
          <CartaoDestaque
            key={c.id}
            indice={i + 2}
            titulo={c.nome}
            subtitulo={c.instituicao ?? undefined}
            onPress={() => router.push(`/cursos/${c.id}`)}
            favorito={{ tipo: 'curso', id: c.id }}
          />
        ))}
      </SecaoHorizontal>

      <SecaoHorizontal
        titulo="Próximos vestibulares"
        onVerTodos={() => router.push('/vestibulares')}
        carregando={vestibulares.carregando}
        erro={vestibulares.erro}
        onTentarNovamente={vestibulares.recarregar}
        vazio={vestibulares.dados && vestibulares.dados.length === 0 ? 'Nenhuma prova próxima.' : undefined}
      >
        {vestibulares.dados?.map((v, i) => (
          <CartaoDestaque
            key={v.id}
            indice={i}
            titulo={v.nome}
            subtitulo={resumoProva(v)}
            onPress={() => router.push(`/vestibulares/${v.id}`)}
            favorito={{ tipo: 'vestibular', id: v.id }}
          />
        ))}
      </SecaoHorizontal>

      <Text style={[tipografia.secao, styles.titulo]} accessibilityRole="header">
        Mais para você
      </Text>
      <LinhaLista titulo="Vestibulares" icone="event" onPress={() => router.push('/vestibulares')} />
      <LinhaLista titulo="Teste vocacional" icone="psychology" onPress={() => router.push('/teste-vocacional')} />
    </Tela>
  );
}

const styles = StyleSheet.create({
  saudacao: { flexDirection: 'row', alignItems: 'center', gap: espaco.md },
  ola: { flex: 1, color: cores.roxoEscuro },
  rolagem: { marginHorizontal: -espaco.lg },
  chips: { gap: espaco.sm, paddingHorizontal: espaco.lg },
  titulo: { color: cores.roxoEscuro, marginTop: espaco.sm },
});
