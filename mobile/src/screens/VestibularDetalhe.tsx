import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { obterVestibular } from '../api/catalogo';
import { dataCurta, diasAte, rotuloDias } from '../catalogo/datas';
import { juntar, limpo } from '../catalogo/formatar';
import { abrirSite } from '../catalogo/links';
import { BotaoFavorito } from '../components/catalogo/BotaoFavorito';
import { InfoItem } from '../components/catalogo/InfoItem';
import { Botao } from '../components/ui/Botao';
import { Carregando, EstadoErro } from '../components/ui/Estados';
import { Tela } from '../components/ui/Tela';
import { useConsulta } from '../hooks/useConsulta';
import { cores, espaco, raio, sombra, tipografia } from '../theme/tokens';

// Detalhe do vestibular (mesmos campos do card da página /vestibulares do site),
// compartilhado por Explorar e Salvos. O cartão laranja do Figma ("Definir um
// lembrete") mostra a contagem até a prova: lembretes dependem de notificações,
// fora do escopo do app.
export default function VestibularDetalhe() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { dados: v, erro, carregando, recarregar } = useConsulta(
    async () => (await obterVestibular(Number(id))).data,
    [id],
  );

  if (!v) {
    return (
      <Tela cabecalho={{ titulo: 'Vestibular' }}>
        {carregando ? (
          <Carregando />
        ) : (
          <EstadoErro mensagem={erro ?? 'Vestibular não encontrado.'} onTentarNovamente={recarregar} />
        )}
      </Tela>
    );
  }

  const data = dataCurta(v.data_prova);
  const dias = diasAte(v.data_prova);
  const realizada = dias !== null && dias < 0;
  const instituicao = limpo(v.instituicao);
  const local = juntar(v.cidade, v.regiao) ?? 'Nacional';
  const inscricoes = limpo(v.periodo_inscricao);
  const taxa = limpo(v.taxa_inscricao);
  const descricao = limpo(v.descricao);
  const cursos = limpo(v.cursos_oferecidos);
  const requisitos = limpo(v.requisitos);
  const edital = limpo(v.link_edital);

  return (
    <Tela
      cabecalho={{
        titulo: v.nome,
        grande: true,
        acao: <BotaoFavorito tipo="vestibular" id={v.id} nome={v.nome} />,
      }}
    >
      <View style={[styles.destaque, realizada && styles.destaqueRealizado]} accessible>
        <Text style={styles.destaqueRotulo}>{realizada ? 'Prova realizada' : data ? 'Faltam' : 'Data da prova'}</Text>
        <Text style={styles.destaqueValor}>
          {realizada ? data : data ? rotuloDias(v.data_prova) : 'A definir'}
        </Text>
        {!realizada && !!data && <Text style={styles.destaqueData}>Prova em {data}</Text>}
      </View>

      <View style={styles.infos}>
        {!!instituicao && (
          <InfoItem
            icone="account-balance"
            texto={limpo(v.tipo_instituicao) ? `${instituicao} (${v.tipo_instituicao})` : instituicao}
            onPress={v.faculdade_id ? () => router.push(`/faculdades/${v.faculdade_id}`) : undefined}
            rotuloAcessivel={v.faculdade_id ? `Ver a faculdade ${instituicao}` : undefined}
          />
        )}
        <InfoItem icone="event" texto={`Inscrições: ${inscricoes ?? 'A definir'}`} />
        {!!taxa && <InfoItem icone="receipt" texto={`Taxa: ${taxa}`} />}
        <InfoItem icone="place" texto={local} />
      </View>

      {!!descricao && <Bloco titulo="Sobre o processo seletivo" texto={descricao} />}
      {!!cursos && <Bloco titulo="Cursos e vagas" texto={cursos} />}
      {!!requisitos && <Bloco titulo="Requisitos" texto={requisitos} />}

      {!!edital && <Botao titulo="Ver edital" variante="primario" icone="open-in-new" onPress={() => abrirSite(edital)} />}
    </Tela>
  );
}

function Bloco({ titulo, texto }: { titulo: string; texto: string }) {
  return (
    <View style={styles.bloco}>
      <Text style={[tipografia.tituloBloco, styles.titulo]} accessibilityRole="header">
        {titulo}
      </Text>
      <Text style={[tipografia.descricao, styles.texto]}>{texto}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  destaque: { backgroundColor: cores.laranja, borderRadius: raio.linha, padding: espaco.lg, gap: espaco.xxs, ...sombra },
  destaqueRealizado: { backgroundColor: cores.roxoClaro },
  destaqueRotulo: { ...tipografia.rotulo, color: cores.branco },
  destaqueValor: { ...tipografia.tituloPagina, color: cores.branco },
  destaqueData: { ...tipografia.descricao, color: cores.branco },
  infos: { gap: espaco.md },
  bloco: { gap: espaco.sm },
  titulo: { color: cores.roxoEscuro },
  texto: { color: cores.textoSuave },
});
