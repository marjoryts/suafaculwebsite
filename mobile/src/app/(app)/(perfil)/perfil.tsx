import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { meuPainel } from '../../../api/perfil';
import type { Painel } from '../../../api/tipos';
import { useSessao } from '../../../auth/SessaoProvider';
import { resumoProva } from '../../../catalogo/datas';
import { Botao } from '../../../components/ui/Botao';
import { LinhaLista } from '../../../components/ui/LinhaLista';
import { OpcaoMenu } from '../../../components/ui/OpcaoMenu';
import { TelaPerfil } from '../../../components/ui/TelaPerfil';
import { useConsulta } from '../../../hooks/useConsulta';
import { cores, espaco, familias, raio, sombra, tipografia } from '../../../theme/tokens';

// Figma "Perfil" (cabeçalho roxo, folha com "Configurações") + o "Meu painel" do site:
// contadores, próximas provas dos vestibulares salvos e o perfil vocacional.
export default function Perfil() {
  const { usuario, sair } = useSessao();
  const router = useRouter();
  const [saindo, setSaindo] = useState(false);
  const painel = useConsulta(async () => (await meuPainel()).data, []);

  // Recarrega o painel ao voltar para a aba (favoritos e testes podem ter mudado).
  const { recarregar } = painel;
  useFocusEffect(
    useCallback(() => {
      void recarregar();
    }, [recarregar]),
  );

  async function aoSair() {
    setSaindo(true);
    await sair(); // o porteiro da raiz leva para o login
  }

  return (
    <TelaPerfil
      usuario={usuario}
      detalhe={usuario?.tipo === 'admin' ? 'Administrador' : 'Estudante'}
      acao={<Botao titulo="Editar Perfil" variante="texto" sobreCor onPress={() => router.push('/editar')} />}
    >
      <Text style={[tipografia.subtitulo, styles.titulo]} accessibilityRole="header">
        Meu painel
      </Text>
      {painel.dados ? (
        <ConteudoPainel painel={painel.dados} />
      ) : painel.erro ? (
        <View style={styles.aviso}>
          <Text style={[tipografia.descricao, styles.cinza]}>{painel.erro}</Text>
          <Botao titulo="Tentar novamente" variante="texto" onPress={painel.recarregar} />
        </View>
      ) : (
        <ActivityIndicator color={cores.roxo} style={styles.carregando} />
      )}

      <Text style={[tipografia.subtitulo, styles.titulo]} accessibilityRole="header">
        Configurações
      </Text>
      <OpcaoMenu titulo="Favoritos" icone="favorite" onPress={() => router.navigate('/salvos')} />
      <OpcaoMenu titulo="Conta" icone="person" onPress={() => router.push('/editar')} />
      <OpcaoMenu titulo="Alterar senha" icone="lock" onPress={() => router.push('/alterar-senha')} />
      {usuario?.tipo === 'admin' && (
        <OpcaoMenu titulo="Painel administrativo" icone="admin-panel-settings" onPress={() => router.push('/admin')} />
      )}
      <OpcaoMenu titulo="Ajuda" icone="help" onPress={() => router.push('/ajuda')} />
      <OpcaoMenu titulo="Sobre nós" icone="info" onPress={() => router.push('/sobre')} />
      <OpcaoMenu titulo="Sair" icone="logout" destaque onPress={aoSair} carregando={saindo} />
    </TelaPerfil>
  );
}

function ConteudoPainel({ painel }: { painel: Painel }) {
  const router = useRouter();
  const { contagem_favoritos: c, proximas_provas: provas, ultimo_teste: teste } = painel;
  const totalTestes = painel.testes_vocacionais.length;
  const contadores: [number, string, string][] = [
    [c.cursos, 'Cursos favoritos', '/salvos'],
    [c.faculdades, 'Faculdades favoritas', '/salvos'],
    [c.vestibulares, 'Vestibulares salvos', '/salvos'],
    [totalTestes, totalTestes === 1 ? 'Teste vocacional' : 'Testes vocacionais', '/teste-vocacional'],
  ];

  return (
    <>
      <View style={styles.contadores}>
        {contadores.map(([n, rotulo, rota]) => (
          <Pressable
            key={rotulo}
            accessibilityRole="button"
            accessibilityLabel={`${n} ${rotulo}`}
            onPress={() => router.navigate(rota)}
            style={({ pressed }) => [styles.contador, pressed && { opacity: 0.85 }]}
          >
            <Text style={styles.contadorNumero}>{n}</Text>
            <Text style={styles.contadorRotulo}>{rotulo}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={[tipografia.tituloBloco, styles.titulo]}>Próximas provas</Text>
      {provas.length === 0 ? (
        <Text style={[tipografia.descricao, styles.cinza]}>
          Salve vestibulares nos favoritos para acompanhar as datas das provas aqui.
        </Text>
      ) : (
        provas.map((v) => (
          <LinhaLista
            key={v.id}
            titulo={v.nome}
            subtitulo={resumoProva(v)}
            icone="event"
            onPress={() => router.push(`/vestibulares/${v.id}`)}
          />
        ))
      )}

      <Text style={[tipografia.tituloBloco, styles.titulo]}>Perfil vocacional</Text>
      {teste ? (
        <View style={styles.teste}>
          <Text style={[tipografia.rotulo, styles.titulo]}>{teste.perfil_nome}</Text>
          {teste.pontuacoes
            .filter((p) => p.percentual > 0)
            .slice(0, 3)
            .map((p) => (
              <Text key={p.chave} style={[tipografia.descricao, styles.cinza]}>
                {p.nome}: {p.percentual}%
              </Text>
            ))}
          <Botao
            titulo="Ver resultado completo"
            variante="texto"
            onPress={() => router.navigate({ pathname: '/teste-vocacional/resultado', params: { id: String(teste.id) } })}
          />
        </View>
      ) : (
        <View style={styles.teste}>
          <Text style={[tipografia.descricao, styles.cinza]}>
            Responda algumas perguntas e veja quais áreas e cursos combinam com seu perfil.
          </Text>
          <Botao titulo="Fazer teste agora" variante="texto" onPress={() => router.navigate('/teste-vocacional')} />
        </View>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  titulo: { color: cores.roxoEscuro },
  cinza: { color: cores.textoSuave },
  aviso: { alignItems: 'flex-start' },
  carregando: { marginVertical: espaco.lg },
  contadores: { flexDirection: 'row', flexWrap: 'wrap', gap: espaco.smd },
  contador: {
    flexBasis: '47%',
    flexGrow: 1,
    backgroundColor: cores.superficie,
    borderRadius: raio.linha,
    padding: espaco.md,
    ...sombra,
  },
  contadorNumero: { fontFamily: familias.interNegrito, fontSize: 28, color: cores.roxo },
  contadorRotulo: { ...tipografia.legenda, fontSize: 13, color: cores.textoSuave },
  teste: { gap: espaco.xs, alignItems: 'flex-start' },
});
