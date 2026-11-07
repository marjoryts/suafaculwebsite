import { useFocusEffect, useRouter } from 'expo-router';
import { ComponentProps, useCallback } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type MaterialIcons from '@expo/vector-icons/MaterialIcons';

import type { Favorito, TipoFavorito } from '../../../api/tipos';
import { useSessao } from '../../../auth/SessaoProvider';
import { resumoProva } from '../../../catalogo/datas';
import { juntar, local, modalidade } from '../../../catalogo/formatar';
import { BotaoFavorito } from '../../../components/catalogo/BotaoFavorito';
import { Avatar } from '../../../components/ui/Avatar';
import { Botao } from '../../../components/ui/Botao';
import { Carregando, EstadoErro, EstadoVazio } from '../../../components/ui/Estados';
import { LinhaLista } from '../../../components/ui/LinhaLista';
import { Tela } from '../../../components/ui/Tela';
import { useFavoritos } from '../../../favoritos/FavoritosProvider';
import { cores, espaco, tipografia } from '../../../theme/tokens';

type Secao = {
  tipo: TipoFavorito;
  titulo: string;
  icone: ComponentProps<typeof MaterialIcons>['name'];
  rota: string;
  vazio: string;
  explorar: string;
};

// Mesmos grupos e textos do painel do site ("Cursos favoritos", "Faculdades favoritas", "Vestibulares salvos").
const SECOES: Secao[] = [
  { tipo: 'faculdade', titulo: 'Faculdades favoritas', icone: 'school', rota: 'faculdades', vazio: 'As instituições que você está considerando.', explorar: 'Buscar faculdades' },
  { tipo: 'curso', titulo: 'Cursos favoritos', icone: 'menu-book', rota: 'cursos', vazio: 'Os cursos que você salvou para comparar depois.', explorar: 'Explorar cursos' },
  { tipo: 'vestibular', titulo: 'Vestibulares salvos', icone: 'event', rota: 'vestibulares', vazio: 'Acompanhe inscrições, provas e editais.', explorar: 'Ver vestibulares' },
];

/** Linha de apoio a partir do resumo que GET /favoritos traz em `item`. */
function resumo(f: Favorito): string | undefined {
  const i = (f.item ?? {}) as Record<string, string | null>;
  if (f.tipo === 'curso') return juntar(i.instituicao, modalidade(i.modalidade));
  if (f.tipo === 'faculdade') return juntar(local(i.cidade, i.uf), i.tipo_instituicao);
  return resumoProva({ data_prova: i.data_prova ?? null, instituicao: i.instituicao ?? null });
}

// Aba Salvos (Figma "Página Favoritos" + listas de favoritos do painel do site).
export default function Salvos() {
  const router = useRouter();
  const { usuario } = useSessao();
  const { favoritos, carregando, erro, recarregar } = useFavoritos();

  // Atualiza ao entrar na aba: itens salvos em outras telas ganham o resumo do servidor.
  useFocusEffect(
    useCallback(() => {
      void recarregar();
    }, [recarregar]),
  );

  let conteudo;
  if (carregando && favoritos.length === 0) conteudo = <Carregando />;
  else if (erro && favoritos.length === 0) conteudo = <EstadoErro mensagem={erro} onTentarNovamente={recarregar} />;
  else if (favoritos.length === 0)
    conteudo = (
      <EstadoVazio
        icone="favorite-border"
        titulo="Nada salvo ainda"
        mensagem="Toque no coração em cursos, faculdades e vestibulares para guardá-los aqui."
      />
    );
  else
    conteudo = SECOES.map((s) => {
      const itens = favoritos.filter((f) => f.tipo === s.tipo);
      return (
        <View key={s.tipo} style={styles.secao}>
          <Text style={[tipografia.subtitulo, styles.titulo]} accessibilityRole="header">
            {s.titulo} ({itens.length})
          </Text>
          {itens.length === 0 ? (
            <View style={styles.vazio}>
              <Text style={[tipografia.descricao, styles.cinza]}>{s.vazio}</Text>
              <Botao titulo={s.explorar} variante="texto" onPress={() => router.navigate(`/${s.rota}`)} />
            </View>
          ) : (
            itens.map((f) => {
              const removido = f.item === null; // apagado do catálogo depois de salvo
              return (
                <LinhaLista
                  key={`${f.tipo}:${f.item_id}`}
                  titulo={f.nome_item}
                  subtitulo={removido ? 'Não está mais disponível no catálogo' : resumo(f)}
                  icone={s.icone}
                  onPress={removido ? undefined : () => router.push(`/${s.rota}/${f.item_id}`)}
                  acessorio={<BotaoFavorito tipo={f.tipo} id={f.item_id} nome={f.nome_item} />}
                />
              );
            })
          )}
        </View>
      );
    });

  return (
    <Tela cabecalho={{ titulo: 'Salvos', voltar: false }}>
      <View style={styles.usuario}>
        <Avatar nome={usuario?.nome_usuario} url={usuario?.avatar_url} />
        <Text style={[tipografia.saudacao, styles.nome]} numberOfLines={1}>
          {usuario?.nome_usuario}
        </Text>
      </View>
      {conteudo}
    </Tela>
  );
}

const styles = StyleSheet.create({
  usuario: { flexDirection: 'row', alignItems: 'center', gap: espaco.md },
  nome: { flex: 1, color: cores.roxoEscuro },
  secao: { gap: espaco.smd },
  titulo: { color: cores.roxoEscuro },
  vazio: { alignItems: 'flex-start' },
  cinza: { color: cores.textoSuave },
});
