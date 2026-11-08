import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { enviarRespostas, perguntas as buscarPerguntas } from '../../../../api/testeVocacional';
import { Botao } from '../../../../components/ui/Botao';
import { Carregando, EstadoErro } from '../../../../components/ui/Estados';
import { Tela } from '../../../../components/ui/Tela';
import { mensagemDeErro, useConsulta } from '../../../../hooks/useConsulta';
import { cores, espaco, familias, raio, sombra, tipografia } from '../../../../theme/tokens';

// Uma pergunta por vez, como a página do site, no layout do Figma "Teste Vocacional"
// (barra de progresso + pergunta + alternativas). O Figma desenha uma escala
// "Concordo/Discordo" colorida; as perguntas reais têm alternativas descritivas,
// então todas usam o mesmo estilo e a escolhida fica roxa.
export default function Perguntas() {
  const router = useRouter();
  const questionario = useConsulta(async () => (await buscarPerguntas()).data, []);
  const lista = useMemo(
    () =>
      (questionario.dados?.secoes ?? []).flatMap((s) => s.perguntas.map((p) => ({ ...p, categoria: s.titulo }))),
    [questionario.dados],
  );
  const [indice, setIndice] = useState(0);
  const [respostas, setRespostas] = useState<Record<string, string>>({});
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  if (!questionario.dados) {
    return (
      <Tela cabecalho={{ titulo: 'Teste Vocacional' }}>
        {questionario.carregando ? (
          <Carregando />
        ) : (
          <EstadoErro mensagem={questionario.erro ?? 'Não foi possível carregar.'} onTentarNovamente={questionario.recarregar} />
        )}
      </Tela>
    );
  }

  const pergunta = lista[indice];
  const ultima = indice === lista.length - 1;
  const escolhida = respostas[pergunta.id];

  async function concluir() {
    setErro(null);
    setEnviando(true);
    try {
      const { data } = await enviarRespostas(respostas);
      router.replace({
        pathname: '/teste-vocacional/resultado',
        params: data.resultado_id ? { id: String(data.resultado_id) } : {},
      });
    } catch (e) {
      setErro(mensagemDeErro(e));
      setEnviando(false);
    }
  }

  return (
    <Tela cabecalho={{ titulo: 'Teste Vocacional' }}>
      <View
        style={styles.trilha}
        accessibilityRole="progressbar"
        accessibilityLabel={`Pergunta ${indice + 1} de ${lista.length}`}
        accessibilityValue={{ min: 0, max: lista.length, now: indice + 1 }}
      >
        <View style={[styles.progresso, { width: `${((indice + 1) / lista.length) * 100}%` }]} />
      </View>
      <Text style={styles.contador}>
        {pergunta.categoria} · Pergunta {indice + 1} de {lista.length}
      </Text>
      <Text style={styles.pergunta} accessibilityRole="header">
        {pergunta.texto}
      </Text>

      <View style={styles.opcoes} accessibilityRole="radiogroup">
        {pergunta.opcoes.map((o) => {
          const ativa = escolhida === o.id;
          return (
            <Pressable
              key={o.id}
              accessibilityRole="radio"
              accessibilityState={{ checked: ativa }}
              accessibilityLabel={o.texto}
              onPress={() => setRespostas((r) => ({ ...r, [pergunta.id]: o.id }))}
              style={({ pressed }) => [styles.opcao, ativa && styles.opcaoAtiva, pressed && { opacity: 0.85 }]}
            >
              <Text style={[styles.opcaoTexto, ativa && styles.opcaoTextoAtiva]}>{o.texto}</Text>
            </Pressable>
          );
        })}
      </View>

      {!!erro && (
        <Text style={styles.erro} accessibilityLiveRegion="polite">
          {erro}
        </Text>
      )}

      <View style={styles.navegacao}>
        {indice > 0 && (
          <View style={styles.metade}>
            <Botao titulo="Anterior" variante="secundario" tamanho="compacto" onPress={() => setIndice((i) => i - 1)} />
          </View>
        )}
        <View style={styles.metade}>
          {ultima ? (
            <Botao titulo="Ver resultado" onPress={concluir} carregando={enviando} desabilitado={!escolhida} />
          ) : (
            <Botao titulo="Próxima" tamanho="compacto" onPress={() => setIndice((i) => i + 1)} desabilitado={!escolhida} />
          )}
        </View>
      </View>
    </Tela>
  );
}

const styles = StyleSheet.create({
  // Barra do Figma: trilha #d9d9d9 de 10px, preenchimento laranja, cantos 20.
  trilha: { height: 10, borderRadius: raio.linha, backgroundColor: cores.borda, overflow: 'hidden' },
  progresso: { height: '100%', borderRadius: raio.linha, backgroundColor: cores.laranja },
  contador: { ...tipografia.legenda, fontSize: 14, color: cores.textoSuave },
  pergunta: { fontFamily: familias.interNegrito, fontSize: 24, lineHeight: 27, color: cores.roxoEscuro },
  opcoes: { gap: espaco.md },
  // Botões das alternativas do Figma: 60 de altura, cantos 20, sombra.
  opcao: {
    minHeight: 60,
    borderRadius: raio.linha,
    backgroundColor: cores.superficie,
    paddingHorizontal: espaco.md,
    paddingVertical: espaco.smd,
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: 'transparent',
    ...sombra,
  },
  opcaoAtiva: { backgroundColor: cores.roxoMedio, borderColor: cores.roxoMedio },
  opcaoTexto: { fontFamily: familias.interMedio, fontSize: 17, lineHeight: 22, color: cores.texto, textAlign: 'center' },
  opcaoTextoAtiva: { color: cores.branco },
  erro: { ...tipografia.corpo, color: cores.erro, textAlign: 'center' },
  navegacao: { flexDirection: 'row', gap: espaco.md, marginTop: espaco.sm },
  metade: { flex: 1 },
});
