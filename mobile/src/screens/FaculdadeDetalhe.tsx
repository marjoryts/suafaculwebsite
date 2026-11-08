import { useLocalSearchParams, useRouter } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { obterFaculdade } from '../api/catalogo';
import { juntar, limpo, local, modalidade, nomeCurto } from '../catalogo/formatar';
import { abrirMapa, abrirSite, enviarEmail, ligar } from '../catalogo/links';
import { BotaoFavorito } from '../components/catalogo/BotaoFavorito';
import { InfoItem } from '../components/catalogo/InfoItem';
import { Botao } from '../components/ui/Botao';
import { Carregando, EstadoErro } from '../components/ui/Estados';
import { LinhaLista } from '../components/ui/LinhaLista';
import { Tela } from '../components/ui/Tela';
import { useConsulta } from '../hooks/useConsulta';
import { cores, espaco, raio, tipografia } from '../theme/tokens';

const TONS = [cores.roxoEscuro, cores.roxo, cores.roxoClaro];

// Detalhe da faculdade (Figma "Página Faculdades"), compartilhado por Explorar e Salvos.
// Sem foto, descrição, mapa embutido nem "compatibilidade %": esses dados não existem no banco.
export default function FaculdadeDetalhe() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { dados: f, erro, carregando, recarregar } = useConsulta(
    async () => (await obterFaculdade(Number(id))).data,
    [id],
  );

  if (!f) {
    return (
      <Tela cabecalho={{ titulo: 'Faculdade' }}>
        {carregando ? (
          <Carregando />
        ) : (
          <EstadoErro mensagem={erro ?? 'Faculdade não encontrada.'} onTentarNovamente={recarregar} />
        )}
      </Tela>
    );
  }

  const titulo = nomeCurto(f);
  const lugar = local(f.cidade, f.uf);
  const endereco = limpo(f.endereco);
  const site = limpo(f.url);
  const telefone = limpo(f.telefone);
  const email = limpo(f.email);
  const organizacao = limpo(f.organizacao_academica);
  const tipo = limpo(f.tipo_instituicao);

  return (
    <Tela
      cabecalho={{
        titulo,
        grande: true,
        acao: <BotaoFavorito tipo="faculdade" id={f.id} nome={f.nome} />,
      }}
    >
      {titulo !== f.nome && <Text style={[tipografia.descricao, styles.cinza]}>{f.nome}</Text>}

      <View style={styles.infos}>
        {!!organizacao && <InfoItem icone="account-balance" texto={organizacao} />}
        {!!tipo && <InfoItem icone="apartment" texto={`Instituição ${tipo.toLowerCase()}`} />}
        {!!lugar && <InfoItem icone="place" texto={lugar} />}
      </View>

      <View style={styles.bloco}>
        <Text style={[tipografia.tituloBloco, styles.roxo]} accessibilityRole="header">
          Cursos
        </Text>
        {f.cursos.length === 0 ? (
          <Text style={[tipografia.descricao, styles.cinza]}>Nenhum curso cadastrado para esta instituição.</Text>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.rolagem} contentContainerStyle={styles.cursos}>
            {f.cursos.map((c, i) => (
              <Pressable
                key={c.id}
                accessibilityRole="button"
                accessibilityLabel={juntar(c.nome, modalidade(c.modalidade))}
                onPress={() => router.push(`/cursos/${c.id}`)}
                style={({ pressed }) => [styles.cartaoCurso, { backgroundColor: TONS[i % TONS.length] }, pressed && { opacity: 0.85 }]}
              >
                <Text style={styles.nomeCurso} numberOfLines={3}>
                  {c.nome}
                </Text>
                {!!modalidade(c.modalidade) && <Text style={styles.detalheCurso}>{modalidade(c.modalidade)}</Text>}
              </Pressable>
            ))}
          </ScrollView>
        )}
      </View>

      {f.vestibulares.length > 0 && (
        <View style={styles.bloco}>
          <Text style={[tipografia.tituloBloco, styles.roxo]} accessibilityRole="header">
            Vestibulares
          </Text>
          {f.vestibulares.map((v) => (
            <LinhaLista
              key={v.id}
              titulo={v.nome}
              subtitulo={limpo(v.data_prova) ? `Prova: ${v.data_prova}` : limpo(v.periodo_inscricao)}
              icone="event"
              onPress={() => router.push(`/vestibulares/${v.id}`)}
            />
          ))}
        </View>
      )}

      {(!!endereco || !!lugar) && (
        <View style={styles.bloco}>
          <Text style={[tipografia.tituloBloco, styles.roxo]} accessibilityRole="header">
            Ver endereço
          </Text>
          <Text style={[tipografia.descricao, styles.cinza]}>{juntar(endereco, lugar)}</Text>
          <Botao
            titulo="Abrir no mapa"
            variante="secundario"
            tamanho="compacto"
            icone="map"
            onPress={() => abrirMapa(endereco, f.cidade, f.uf, endereco ? undefined : f.nome)}
          />
        </View>
      )}

      {(!!site || !!telefone || !!email) && (
        <View style={styles.infos}>
          {!!site && <InfoItem icone="language" texto={site} onPress={() => abrirSite(site)} rotuloAcessivel={`Abrir o site ${site}`} />}
          {!!telefone && <InfoItem icone="call" texto={telefone} onPress={() => ligar(telefone)} rotuloAcessivel={`Ligar para ${telefone}`} />}
          {!!email && <InfoItem icone="mail" texto={email} onPress={() => enviarEmail(email)} rotuloAcessivel={`Enviar e-mail para ${email}`} />}
        </View>
      )}
    </Tela>
  );
}

const styles = StyleSheet.create({
  roxo: { color: cores.roxoEscuro },
  cinza: { color: cores.textoSuave },
  infos: { gap: espaco.md },
  bloco: { gap: espaco.smd },
  rolagem: { marginHorizontal: -espaco.lg },
  cursos: { gap: espaco.md + 5, paddingHorizontal: espaco.lg }, // 21 entre os cards, como no Figma
  // Cards "Cursos e suas compatibilidades" do Figma (97×122, cantos 20).
  cartaoCurso: { width: 110, minHeight: 122, borderRadius: raio.linha, padding: espaco.smd, justifyContent: 'space-between' },
  nomeCurso: { fontFamily: tipografia.rotulo.fontFamily, fontSize: 12, lineHeight: 18, color: cores.branco, textAlign: 'center' },
  detalheCurso: { ...tipografia.legenda, fontSize: 11, color: cores.sobreBarra, textAlign: 'center' },
});
