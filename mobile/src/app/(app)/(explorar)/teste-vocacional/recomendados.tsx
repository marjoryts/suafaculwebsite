import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { recomendacoes } from '../../../../api/testeVocacional';
import { juntar, plural } from '../../../../catalogo/formatar';
import { BotaoFavorito } from '../../../../components/catalogo/BotaoFavorito';
import { Carregando, EstadoErro, EstadoVazio } from '../../../../components/ui/Estados';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useConsulta } from '../../../../hooks/useConsulta';
import { cores, espaco, familias, raio, tipografia } from '../../../../theme/tokens';

const LIMITE = 50; // mesmo padrão da página de resultado do site

// "Cursos com maior compatibilidade" da página de resultado do site.
export default function Recomendados() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const router = useRouter();
  const consulta = useConsulta(async () => (await recomendacoes(id ? Number(id) : undefined, LIMITE)).data, [id]);

  const rec = consulta.dados;
  return (
    <Tela cabecalho={{ titulo: 'Cursos recomendados' }}>
      {!rec ? (
        consulta.carregando ? (
          <Carregando />
        ) : (
          <EstadoErro mensagem={consulta.erro ?? 'Não foi possível carregar.'} onTentarNovamente={consulta.recarregar} />
        )
      ) : rec.cursos.length === 0 ? (
        <EstadoVazio
          icone="school"
          titulo="Nenhum curso compatível ainda"
          mensagem="Ainda não há cursos cadastrados que combinem com o seu perfil."
        />
      ) : (
        <>
          <Text style={[tipografia.descricao, styles.cinza]}>
            Perfil {rec.perfil_nome}: {plural(rec.total_compativeis, 'curso compatível', 'cursos compatíveis')}, do mais
            ao menos compatível.
          </Text>
          {rec.cursos.map((c) => (
            <LinhaLista
              key={c.id}
              titulo={c.nome}
              subtitulo={juntar(
                c.area,
                c.grau,
                c.total_instituicoes > 1 ? `${c.total_instituicoes} instituições` : undefined,
              )}
              icone="menu-book"
              onPress={() => router.push(`/cursos/${c.id}`)}
              acessorio={
                <View style={styles.lado}>
                  <View style={styles.selo} accessible accessibilityLabel={`${c.compatibilidade}% compatível`}>
                    <Text style={styles.seloTexto}>{c.compatibilidade}%</Text>
                  </View>
                  <BotaoFavorito tipo="curso" id={c.id} nome={c.nome} tamanho={24} />
                </View>
              }
            />
          ))}
          {rec.sem_dados_suficientes > 0 && (
            <Text style={[tipografia.descricao, styles.cinza]}>
              {plural(rec.sem_dados_suficientes, 'curso ficou', 'cursos ficaram')} de fora por falta de dados para
              calcular a compatibilidade.
            </Text>
          )}
        </>
      )}
    </Tela>
  );
}

const styles = StyleSheet.create({
  cinza: { color: cores.textoSuave },
  lado: { alignItems: 'center', gap: espaco.xs },
  selo: { minWidth: 48, paddingHorizontal: espaco.sm, paddingVertical: espaco.xs, borderRadius: raio.pilula, backgroundColor: cores.roxo, alignItems: 'center' },
  seloTexto: { fontFamily: familias.interNegrito, fontSize: 13, color: cores.branco },
});
