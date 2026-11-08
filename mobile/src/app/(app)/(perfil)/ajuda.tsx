import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { CampoBusca } from '../../../components/ui/CampoBusca';
import { EstadoVazio } from '../../../components/ui/Estados';
import { LinhaLista } from '../../../components/ui/LinhaLista';
import { Tela } from '../../../components/ui/Tela';
import { filtrarFaq } from '../../../conteudo/institucional';
import { cores, espaco, raio, sombra, tipografia } from '../../../theme/tokens';

// Página Ajuda do site: perguntas frequentes por grupo, com busca (sem acentos) que
// abre as respostas que combinam, e atalhos para Sobre nós, Vestibulares e o teste.
export default function Ajuda() {
  const router = useRouter();
  const [busca, setBusca] = useState('');
  const [abertas, setAbertas] = useState<Set<string>>(new Set());
  const grupos = filtrarFaq(busca);
  const buscando = busca.trim().length > 0;

  function alternar(pergunta: string) {
    setAbertas((a) => {
      const nova = new Set(a);
      if (nova.has(pergunta)) nova.delete(pergunta);
      else nova.add(pergunta);
      return nova;
    });
  }

  return (
    <Tela cabecalho={{ titulo: 'Ajuda' }}>
      <Text style={[tipografia.descricao, styles.cinza]}>
        Respostas para as dúvidas mais comuns sobre a conta, o teste vocacional e as buscas.
      </Text>
      <CampoBusca placeholder="Busque uma dúvida..." value={busca} onChangeText={setBusca} autoCapitalize="none" />

      {grupos.length === 0 ? (
        <EstadoVazio icone="search-off" titulo="Nenhuma pergunta encontrada" mensagem="Tente outras palavras ou veja os links abaixo." />
      ) : (
        grupos.map((g) => (
          <View key={g.titulo} style={styles.grupo}>
            <Text style={[tipografia.tituloBloco, styles.roxo]} accessibilityRole="header">
              {g.titulo}
            </Text>
            {g.perguntas.map((p) => {
              // Na busca, as respostas que combinam ficam abertas (como no site).
              const aberta = buscando || abertas.has(p.pergunta);
              return (
                <View key={p.pergunta} style={styles.item}>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ expanded: aberta }}
                    accessibilityLabel={p.pergunta}
                    onPress={() => alternar(p.pergunta)}
                    style={styles.pergunta}
                  >
                    <Text style={[tipografia.rotulo, styles.textoPergunta]}>{p.pergunta}</Text>
                    <MaterialIcons name={aberta ? 'expand-less' : 'expand-more'} size={24} color={cores.roxo} />
                  </Pressable>
                  {aberta && <Text style={[tipografia.descricao, styles.cinza]}>{p.resposta}</Text>}
                </View>
              );
            })}
          </View>
        ))
      )}

      <Text style={[tipografia.tituloBloco, styles.roxo]} accessibilityRole="header">
        Ainda com dúvidas?
      </Text>
      <LinhaLista titulo="Conheça o SuaFacul" subtitulo="Nossa missão e equipe" icone="info" onPress={() => router.push('/sobre')} />
      <LinhaLista titulo="Explore os vestibulares" subtitulo="Datas e informações" icone="event" onPress={() => router.navigate('/vestibulares')} />
      <LinhaLista titulo="Faça o teste vocacional" subtitulo="Cursos para o seu perfil" icone="psychology" onPress={() => router.navigate('/teste-vocacional')} />
    </Tela>
  );
}

const styles = StyleSheet.create({
  cinza: { color: cores.textoSuave },
  roxo: { color: cores.roxoEscuro },
  grupo: { gap: espaco.smd },
  item: { backgroundColor: cores.superficie, borderRadius: raio.linha, padding: espaco.md, gap: espaco.sm, ...sombra },
  pergunta: { flexDirection: 'row', alignItems: 'center', gap: espaco.sm, minHeight: 32 },
  textoPergunta: { flex: 1, color: cores.texto },
});
