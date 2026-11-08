import { useRouter } from 'expo-router';
import { Image, StyleSheet, Text, View } from 'react-native';

import { Botao } from '../../../components/ui/Botao';
import { Tela } from '../../../components/ui/Tela';
import { API_URL } from '../../../config';
import { SOBRE } from '../../../conteudo/institucional';
import { cores, espaco, familias, raio, sombra, tipografia } from '../../../theme/tokens';

// Página "Sobre nós" do site: história, missão, visão, valores e equipe.
export default function Sobre() {
  const router = useRouter();
  return (
    <Tela cabecalho={{ titulo: 'Sobre nós' }}>
      <Text style={styles.chamada}>{SOBRE.chamada}</Text>

      <Titulo>Nossa história e propósito</Titulo>
      {SOBRE.historia.map((p) => (
        <Text key={p.slice(0, 20)} style={[tipografia.descricao, styles.cinza]}>
          {p}
        </Text>
      ))}

      <Cartao titulo="Nossa missão" texto={SOBRE.missao} />
      <Cartao titulo="Nossa visão" texto={SOBRE.visao} />

      <Titulo>Nossos valores</Titulo>
      {SOBRE.valores.map(([nome, texto]) => (
        <Cartao key={nome} titulo={nome} texto={texto} />
      ))}

      <Titulo>Conheça nossa equipe</Titulo>
      <Text style={[tipografia.descricao, styles.cinza]}>{SOBRE.equipeIntro}</Text>
      <View style={styles.equipe}>
        {SOBRE.equipe.map((m) => (
          <View key={m.nome} style={styles.membro} accessible accessibilityLabel={`${m.nome}, ${m.cargo}`}>
            <Image source={{ uri: `${API_URL}${m.foto}` }} style={styles.foto} accessibilityIgnoresInvertColors />
            <Text style={styles.nome}>{m.nome}</Text>
            <Text style={styles.cargo}>{m.cargo}</Text>
          </View>
        ))}
      </View>

      <Titulo>Pronto para começar sua jornada?</Titulo>
      <Text style={[tipografia.descricao, styles.cinza]}>
        Explore os cursos disponíveis ou faça o teste vocacional para descobrir as áreas que combinam com você.
      </Text>
      <Botao titulo="Explorar cursos" variante="secundario" tamanho="compacto" onPress={() => router.navigate('/cursos')} />
      <Botao titulo="Fazer o teste vocacional" variante="destaque" onPress={() => router.navigate('/teste-vocacional')} />
    </Tela>
  );
}

function Titulo({ children }: { children: string }) {
  return (
    <Text style={[tipografia.tituloBloco, styles.roxo]} accessibilityRole="header">
      {children}
    </Text>
  );
}

function Cartao({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <View style={styles.cartao}>
      <Text style={[tipografia.rotulo, styles.roxo]}>{titulo}</Text>
      <Text style={[tipografia.descricao, styles.cinza]}>{texto}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chamada: { fontFamily: familias.interSemi, fontSize: 18, lineHeight: 25, color: cores.roxo },
  roxo: { color: cores.roxoEscuro },
  cinza: { color: cores.textoSuave },
  cartao: { backgroundColor: cores.superficie, borderRadius: raio.linha, padding: espaco.md, gap: espaco.xs, ...sombra },
  equipe: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', rowGap: espaco.md },
  membro: { width: '31%', alignItems: 'center', gap: espaco.xs },
  foto: { width: 88, height: 88, borderRadius: 44, backgroundColor: cores.borda },
  nome: { ...tipografia.rotulo, fontSize: 14, color: cores.roxoEscuro, textAlign: 'center' },
  cargo: { ...tipografia.legenda, color: cores.textoSuave, textAlign: 'center' },
});
