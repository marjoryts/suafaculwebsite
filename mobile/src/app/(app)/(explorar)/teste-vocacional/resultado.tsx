import { useLocalSearchParams, useRouter } from 'expo-router';
import { Image, StyleSheet, Text, View } from 'react-native';

import { ApiError } from '../../../../api/client';
import { historico, recomendacoes } from '../../../../api/testeVocacional';
import type { PontuacaoPerfil } from '../../../../api/tipos';
import { useSessao } from '../../../../auth/SessaoProvider';
import { Avatar } from '../../../../components/ui/Avatar';
import { Botao } from '../../../../components/ui/Botao';
import { Carregando, EstadoErro, EstadoVazio } from '../../../../components/ui/Estados';
import { Tela } from '../../../../components/ui/Tela';
import { useConsulta } from '../../../../hooks/useConsulta';
import { cores, espaco, familias, raio, sombra, tipografia } from '../../../../theme/tokens';

const TROFEU = require('../../../../../assets/figma/trofeu.png');

// Cores dos cartões de "Resultados recentes" do Figma (fundo, barra), em ordem.
const TONS: [string, string][] = [
  ['#f0dcf7', '#bf93ea'],
  ['#bde0f4', '#7fc4eb'],
  ['#d7e689', '#7bc142'],
  ['#f5c0d2', 'rgba(194, 75, 116, 0.69)'],
];

// Resultado do teste (Figma "Resultados" + conteúdo da página de resultado do site).
export default function Resultado() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const router = useRouter();
  const { usuario } = useSessao();
  const resultadoId = id ? Number(id) : undefined;

  const consulta = useConsulta(async () => {
    try {
      // Perfil + total de cursos compatíveis (limite pequeno: a lista completa fica na próxima tela)
      // e as porcentagens de cada perfil (histórico).
      const [rec, hist] = await Promise.all([recomendacoes(resultadoId, 1), historico(50)]);
      const item = hist.data.find((h) => h.id === rec.data.resultado_id);
      return { rec: rec.data, pontuacoes: item?.pontuacoes ?? [] };
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null; // ainda não fez o teste
      throw e;
    }
  }, [resultadoId]);

  if (consulta.carregando && consulta.dados === null && !consulta.erro) {
    return (
      <Tela cabecalho={{ titulo: 'Resultado' }}>
        <Carregando />
      </Tela>
    );
  }
  if (consulta.erro) {
    return (
      <Tela cabecalho={{ titulo: 'Resultado' }}>
        <EstadoErro mensagem={consulta.erro} onTentarNovamente={consulta.recarregar} />
      </Tela>
    );
  }
  if (!consulta.dados) {
    return (
      <Tela cabecalho={{ titulo: 'Resultado' }}>
        <EstadoVazio icone="psychology" titulo="Você ainda não fez o teste" mensagem="Responda 10 perguntas e veja os cursos que combinam com você." />
        <Botao titulo="Iniciar Teste" variante="destaque" onPress={() => router.replace('/teste-vocacional/perguntas')} />
      </Tela>
    );
  }

  const { rec, pontuacoes } = consulta.dados;
  return (
    <Tela cabecalho={{ titulo: 'Resultado' }}>
      <View style={styles.saudacao}>
        <Avatar nome={usuario?.nome_usuario} url={usuario?.avatar_url} />
        <View style={styles.flex}>
          <Text style={[tipografia.saudacao, styles.roxo]} numberOfLines={1}>
            Olá {usuario?.nome_usuario},
          </Text>
          <Text style={styles.subtitulo}>Que bom te ver de novo!</Text>
        </View>
      </View>

      <View style={styles.concluido} accessible accessibilityLabel="Você finalizou o Teste Vocacional">
        <Image source={TROFEU} style={styles.trofeu} />
        <Text style={styles.concluidoTexto}>Você finalizou o Teste Vocacional</Text>
      </View>

      <View style={styles.perfil}>
        <Text style={styles.perfilRotulo}>Seu perfil principal</Text>
        <Text style={[tipografia.tituloBloco, styles.roxo]}>{rec.perfil_nome}</Text>
        {!!rec.perfil_descricao && <Text style={[tipografia.descricao, styles.cinza]}>{rec.perfil_descricao}</Text>}
      </View>

      {pontuacoes.length > 0 && (
        <>
          <Text style={[tipografia.subtitulo, styles.secao]} accessibilityRole="header">
            Resultados recentes
          </Text>
          {pontuacoes
            .filter((p) => p.percentual > 0)
            .map((p, i) => (
              <CartaoPerfil key={p.chave} posicao={i + 1} pontuacao={p} tons={TONS[i % TONS.length]} />
            ))}
        </>
      )}

      <Text style={[tipografia.descricao, styles.cinza, styles.centro]}>
        {rec.total_compativeis === 1
          ? '1 curso combina com o seu perfil.'
          : `${rec.total_compativeis} cursos combinam com o seu perfil.`}
      </Text>
      <Botao
        titulo="Ver cursos recomendados"
        onPress={() =>
          router.push({ pathname: '/teste-vocacional/recomendados', params: { id: String(rec.resultado_id) } })
        }
      />
      <Botao titulo="Refazer o teste" variante="texto" onPress={() => router.replace('/teste-vocacional/perguntas')} />
    </Tela>
  );
}

function CartaoPerfil({ posicao, pontuacao, tons }: { posicao: number; pontuacao: PontuacaoPerfil; tons: [string, string] }) {
  const [fundo, barra] = tons;
  return (
    <View
      style={[styles.cartao, { backgroundColor: fundo }]}
      accessible
      accessibilityLabel={`${posicao}º, ${pontuacao.nome}, ${pontuacao.percentual}%`}
    >
      <View style={[styles.posicao, { borderColor: barra }]}>
        <Text style={styles.posicaoTexto}>{posicao}</Text>
      </View>
      <View style={styles.flex}>
        <Text style={styles.cartaoNome} numberOfLines={2}>
          {pontuacao.nome}
        </Text>
        <View style={styles.trilha}>
          <View style={[styles.preenchido, { width: `${pontuacao.percentual}%`, backgroundColor: barra }]} />
        </View>
      </View>
      <Text style={styles.percentual}>{pontuacao.percentual}%</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  roxo: { color: cores.roxoEscuro },
  cinza: { color: cores.textoSuave },
  centro: { textAlign: 'center' },
  saudacao: { flexDirection: 'row', alignItems: 'center', gap: espaco.smd },
  subtitulo: { fontFamily: familias.interSemi, fontSize: 13, color: cores.textoSuave },
  // Cartão roxo do Figma (#632e97, cantos 20) com o troféu.
  concluido: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espaco.md,
    backgroundColor: cores.roxoMedio,
    borderRadius: raio.linha,
    padding: espaco.lg,
    ...sombra,
  },
  trofeu: { width: 45, height: 45 },
  concluidoTexto: { flex: 1, fontFamily: familias.interMedio, fontSize: 20, color: cores.branco, textAlign: 'center' },
  perfil: { gap: espaco.xs },
  perfilRotulo: { ...tipografia.legenda, fontSize: 14, color: cores.textoSuave },
  secao: { color: cores.roxo, marginTop: espaco.sm },
  // Cartões de "Resultados recentes" do Figma: 80 de altura, cantos 15, sombra.
  cartao: { minHeight: 80, borderRadius: raio.campo, padding: espaco.md, flexDirection: 'row', alignItems: 'center', gap: espaco.md, ...sombra },
  posicao: { width: 50, height: 50, borderRadius: raio.pilula, borderWidth: 2, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(255,255,255,0.5)' },
  posicaoTexto: { fontFamily: familias.interNegrito, fontSize: 20, color: cores.texto },
  cartaoNome: { fontFamily: familias.interNegrito, fontSize: 14, color: cores.texto, marginBottom: espaco.xs },
  trilha: { height: 12, borderRadius: 10, backgroundColor: cores.folha, padding: 2 },
  preenchido: { height: 8, borderRadius: 10 },
  percentual: { fontFamily: familias.interMedio, fontSize: 14, color: cores.texto },
});
