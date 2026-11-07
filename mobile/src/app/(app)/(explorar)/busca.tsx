import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { useRouter } from 'expo-router';
import { ComponentProps, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { sugestoes } from '../../../api/catalogo';
import type { Sugestao, Sugestoes } from '../../../api/tipos';
import { detalheSugestao } from '../../../catalogo/formatar';
import { Botao } from '../../../components/ui/Botao';
import { CampoBusca } from '../../../components/ui/CampoBusca';
import { Carregando, EstadoErro, EstadoVazio } from '../../../components/ui/Estados';
import { LinhaLista } from '../../../components/ui/LinhaLista';
import { Tela } from '../../../components/ui/Tela';
import { useAtrasado } from '../../../hooks/useAtrasado';
import { useConsulta } from '../../../hooks/useConsulta';
import { cores, espaco, tipografia } from '../../../theme/tokens';

const MINIMO = 2; // o backend só sugere a partir de 2 letras

const GRUPOS: { tipo: Sugestao['tipo']; titulo: string; icone: ComponentProps<typeof MaterialIcons>['name'] }[] = [
  { tipo: 'local', titulo: 'Locais', icone: 'place' },
  { tipo: 'faculdade', titulo: 'Faculdades', icone: 'school' },
  { tipo: 'curso', titulo: 'Cursos', icone: 'menu-book' },
];

const VAZIO: Sugestoes = { local: [], faculdade: [], curso: [] };

// Busca do Explorar (GET /busca/sugestoes). Como no website: escolher um local filtra as
// faculdades por cidade/UF/região, um curso mostra as faculdades que o oferecem e uma
// faculdade abre o detalhe.
export default function Busca() {
  const router = useRouter();
  const [texto, setTexto] = useState('');
  const termo = useAtrasado(texto.trim(), 300);
  const pronto = termo.length >= MINIMO;

  const consulta = useConsulta(
    async () => (pronto ? (await sugestoes(termo)).data : VAZIO),
    [termo, pronto],
  );

  function abrir(s: Sugestao) {
    if (s.tipo === 'faculdade' && s.id) router.push(`/faculdades/${s.id}`);
    else if (s.tipo === 'local') router.push({ pathname: '/faculdades', params: { cidade: s.valor } });
    else router.push({ pathname: '/faculdades', params: { curso: s.valor } });
  }

  const dados = consulta.dados ?? VAZIO;
  const total = dados.local.length + dados.faculdade.length + dados.curso.length;

  let conteudo;
  if (!pronto)
    conteudo = (
      <EstadoVazio
        icone="search"
        titulo="O que você procura?"
        mensagem="Digite o nome de uma faculdade, curso, cidade ou estado."
      />
    );
  else if (consulta.carregando && total === 0) conteudo = <Carregando mensagem="Buscando..." />;
  else if (consulta.erro) conteudo = <EstadoErro mensagem={consulta.erro} onTentarNovamente={consulta.recarregar} />;
  else if (total === 0)
    conteudo = <EstadoVazio icone="search-off" titulo="Nada encontrado" mensagem={`Nenhum resultado para “${termo}”.`} />;
  else
    conteudo = GRUPOS.filter((g) => dados[g.tipo].length > 0).map((g) => (
      <View key={g.tipo} style={styles.grupo}>
        <Text style={[tipografia.tituloBloco, styles.tituloGrupo]} accessibilityRole="header">
          {g.titulo}
        </Text>
        {dados[g.tipo].map((s) => (
          <LinhaLista
            key={`${s.tipo}:${s.id ?? s.valor}`}
            titulo={s.rotulo}
            subtitulo={detalheSugestao(s.detalhe)}
            icone={g.icone}
            onPress={() => abrir(s)}
          />
        ))}
      </View>
    ));

  return (
    <Tela cabecalho={{ titulo: 'Busca' }}>
      <CampoBusca value={texto} onChangeText={setTexto} autoFocus autoCapitalize="none" />
      {pronto && (
        <View style={styles.atalhos}>
          <Botao
            titulo="Ver cursos"
            variante="secundario"
            tamanho="compacto"
            icone="menu-book"
            onPress={() => router.push({ pathname: '/cursos', params: { busca: termo } })}
          />
          <Botao
            titulo="Ver faculdades"
            variante="secundario"
            tamanho="compacto"
            icone="school"
            onPress={() => router.push({ pathname: '/faculdades', params: { busca: termo } })}
          />
        </View>
      )}
      {conteudo}
    </Tela>
  );
}

const styles = StyleSheet.create({
  atalhos: { flexDirection: 'row', gap: espaco.sm, flexWrap: 'wrap' },
  grupo: { gap: espaco.smd },
  tituloGrupo: { color: cores.roxoEscuro },
});
