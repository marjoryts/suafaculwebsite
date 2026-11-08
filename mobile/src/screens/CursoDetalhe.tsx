import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { obterCurso } from '../api/catalogo';
import { limpo, modalidade } from '../catalogo/formatar';
import { BotaoFavorito } from '../components/catalogo/BotaoFavorito';
import { InfoItem } from '../components/catalogo/InfoItem';
import { Botao } from '../components/ui/Botao';
import { Carregando, EstadoErro } from '../components/ui/Estados';
import { Tela } from '../components/ui/Tela';
import { useConsulta } from '../hooks/useConsulta';
import { cores, espaco, tipografia } from '../theme/tokens';

// Detalhe do curso (Figma "Cursos"), compartilhado pelas pilhas Explorar e Salvos.
// O Figma mostra foto e "Disciplinas", que não existem no banco: ficam de fora.
export default function CursoDetalhe() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { dados: curso, erro, carregando, recarregar } = useConsulta(
    async () => (await obterCurso(Number(id))).data,
    [id],
  );

  if (!curso) {
    return (
      <Tela cabecalho={{ titulo: 'Curso' }}>
        {carregando ? <Carregando /> : <EstadoErro mensagem={erro ?? 'Curso não encontrado.'} onTentarNovamente={recarregar} />}
      </Tela>
    );
  }

  const descricao = limpo(curso.descricao);
  const instituicao = limpo(curso.instituicao);
  const duracao = limpo(curso.duracao);
  const mod = modalidade(curso.modalidade);
  const grau = limpo(curso.grau);
  const area = limpo(curso.area);
  const tipo = limpo(curso.tipo_instituicao);
  return (
    <Tela
      cabecalho={{
        titulo: curso.nome,
        grande: true,
        acao: <BotaoFavorito tipo="curso" id={curso.id} nome={curso.nome} />,
      }}
    >
      {!!descricao && (
        <View style={styles.bloco}>
          <Text style={[tipografia.tituloBloco, styles.titulo]} accessibilityRole="header">
            O que você vai aprender?
          </Text>
          <Text style={[tipografia.descricao, styles.texto]}>{descricao}</Text>
        </View>
      )}
      <View style={styles.infos}>
        {!!duracao && <InfoItem icone="schedule" texto={`Duração: ${duracao}`} />}
        {!!mod && <InfoItem icone="menu-book" texto={mod} />}
        {!!grau && <InfoItem icone="workspace-premium" texto={grau} />}
        {!!area && <InfoItem icone="category" texto={`Área: ${area}`} />}
        {!!instituicao && (
          <InfoItem
            icone="account-balance"
            texto={tipo ? `${instituicao} (${tipo})` : instituicao}
            onPress={curso.faculdade_id ? () => router.push(`/faculdades/${curso.faculdade_id}`) : undefined}
            rotuloAcessivel={curso.faculdade_id ? `Ver a faculdade ${instituicao}` : undefined}
          />
        )}
      </View>
      <View style={styles.acao}>
        <Botao
          titulo="Faça o Teste Vocacional!"
          variante="destaque"
          onPress={() => router.navigate('/teste-vocacional')}
        />
      </View>
    </Tela>
  );
}

const styles = StyleSheet.create({
  bloco: { gap: espaco.smd },
  titulo: { color: cores.roxoEscuro },
  texto: { color: cores.textoSuave },
  infos: { gap: espaco.md },
  acao: { marginTop: espaco.sm },
});
