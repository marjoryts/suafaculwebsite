import { useRouter } from 'expo-router';
import { Image, StyleSheet, Text, View } from 'react-native';

import { historico } from '../../../../api/testeVocacional';
import { Botao } from '../../../../components/ui/Botao';
import { Tela } from '../../../../components/ui/Tela';
import { useConsulta } from '../../../../hooks/useConsulta';
import { cores, espaco, familias, raio, sombra, tipografia } from '../../../../theme/tokens';

const ILUSTRACAO = require('../../../../../assets/figma/teste-ilustracao.png');

// Mesmo conteúdo do "Como funciona" da página /testevocacional do site.
const PASSOS = [
  ['Perguntas Interativas', 'Responda a uma série de perguntas sobre suas preferências, hobbies e o que te motiva.'],
  ['Análise Personalizada', 'Nosso sistema analisa suas respostas para identificar padrões e áreas de maior compatibilidade.'],
  ['Resultados e Sugestões', 'Receba sugestões de cursos e áreas profissionais, além de faculdades que oferecem essas opções.'],
  ['Explore e Decida', 'Com base nos resultados, explore os detalhes de cursos e faculdades e dê o próximo passo!'],
];

// Introdução do teste (Figma "Teste Vocacional Inicial").
export default function TesteVocacional() {
  const router = useRouter();
  const ultimo = useConsulta(async () => (await historico(1)).data[0] ?? null, []);

  return (
    <Tela cabecalho={{ titulo: 'Teste Vocacional' }}>
      <Image source={ILUSTRACAO} style={styles.ilustracao} resizeMode="cover" accessibilityIgnoresInvertColors />
      <Text style={styles.chamada}>Escolha as opções que mais combinam com você.</Text>
      <Text style={styles.selos}>10 perguntas · Resultado na hora · Gratuito</Text>
      <View style={styles.botao}>
        <Botao titulo="Iniciar Teste" variante="destaque" onPress={() => router.push('/teste-vocacional/perguntas')} />
      </View>
      {!!ultimo.dados && (
        <Botao
          titulo="Ver meu último resultado"
          variante="texto"
          onPress={() =>
            router.push({ pathname: '/teste-vocacional/resultado', params: { id: String(ultimo.dados!.id) } })
          }
        />
      )}

      <Text style={[tipografia.tituloBloco, styles.titulo]} accessibilityRole="header">
        Como funciona o Teste Vocacional?
      </Text>
      {PASSOS.map(([titulo, texto], i) => (
        <View key={titulo} style={styles.passo}>
          <View style={styles.numero}>
            <Text style={styles.numeroTexto}>{i + 1}</Text>
          </View>
          <View style={styles.passoTextos}>
            <Text style={styles.passoTitulo}>{titulo}</Text>
            <Text style={[tipografia.descricao, styles.cinza]}>{texto}</Text>
          </View>
        </View>
      ))}
      <Text style={[tipografia.descricao, styles.cinza]}>
        O teste é gratuito e leva apenas alguns minutos para ser concluído. Suas respostas são confidenciais.
      </Text>
    </Tela>
  );
}

const styles = StyleSheet.create({
  // Ilustração do Figma (255×329, recortada ao centro).
  ilustracao: { width: 255, height: 329, alignSelf: 'center' },
  chamada: { fontFamily: familias.interNegrito, fontSize: 24, lineHeight: 27, color: cores.roxo, textAlign: 'center' },
  selos: { ...tipografia.legenda, fontSize: 14, color: cores.textoSuave, textAlign: 'center' },
  botao: { alignSelf: 'center', minWidth: 201, marginTop: espaco.sm },
  titulo: { color: cores.roxoEscuro, marginTop: espaco.lg },
  passo: { flexDirection: 'row', gap: espaco.md, backgroundColor: cores.superficie, borderRadius: raio.linha, padding: espaco.md, ...sombra },
  numero: { width: 36, height: 36, borderRadius: raio.pilula, backgroundColor: cores.laranja, alignItems: 'center', justifyContent: 'center' },
  numeroTexto: { fontFamily: familias.interNegrito, fontSize: 18, color: cores.branco },
  passoTextos: { flex: 1, gap: espaco.xxs },
  passoTitulo: { ...tipografia.rotulo, color: cores.roxoEscuro },
  cinza: { color: cores.textoSuave },
});
