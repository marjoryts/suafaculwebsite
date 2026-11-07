import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { estatisticas } from '../../../../api/admin';
import type { Automacao } from '../../../../api/tipos';
import { ExigirAdmin } from '../../../../components/admin/ExigirAdmin';
import { Carregando, EstadoErro } from '../../../../components/ui/Estados';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useConsulta } from '../../../../hooks/useConsulta';
import { cores, espaco, familias, raio, sombra, tipografia } from '../../../../theme/tokens';

// Visão geral do painel administrativo (mesmos indicadores, grupos e textos do /admin do site).
export default function PainelAdmin() {
  return (
    <ExigirAdmin titulo="Painel administrativo">
      <Conteudo />
    </ExigirAdmin>
  );
}

function Conteudo() {
  const router = useRouter();
  const consulta = useConsulta(async () => (await estatisticas()).data, []);
  const { recarregar } = consulta;
  useFocusEffect(
    useCallback(() => {
      void recarregar();
    }, [recarregar]),
  );

  if (!consulta.dados) {
    return (
      <Tela cabecalho={{ titulo: 'Painel administrativo' }}>
        {consulta.carregando ? <Carregando /> : <EstadoErro mensagem={consulta.erro ?? 'Erro.'} onTentarNovamente={recarregar} />}
      </Tela>
    );
  }

  const { stats: s, automacoes } = consulta.dados;
  return (
    <Tela cabecalho={{ titulo: 'Painel administrativo' }}>
      <View style={styles.grade}>
        <Indicador valor={s.total_usuarios} rotulo="Usuários" extra={`${s.total_admins} admin(s) · ${s.novos_usuarios_30d} novos em 30 dias`} />
        <Indicador valor={s.total_faculdades} rotulo="Faculdades" extra={`${s.faculdades_importadas_emec} importadas do e-MEC`} />
        <Indicador valor={s.total_cursos} rotulo="Cursos cadastrados" extra={`em ${s.faculdades_com_cursos} faculdade(s)`} />
        <Indicador valor={s.total_vestibulares} rotulo="Vestibulares" extra={`${s.vestibulares_ativos} ativos · ${s.vestibulares_sem_faculdade} sem faculdade`} />
      </View>

      <Titulo>Gerenciar</Titulo>
      <LinhaLista titulo="Usuários" subtitulo="Criar, editar, mudar o tipo e excluir" icone="people" onPress={() => router.push('/admin/usuarios')} />
      <LinhaLista titulo="Faculdades" subtitulo="Cadastrar, editar e importar do e-MEC" icone="school" onPress={() => router.push('/admin/faculdades')} />
      <LinhaLista titulo="Cursos" subtitulo="Cadastrar vinculado a uma faculdade" icone="menu-book" onPress={() => router.push('/admin/cursos')} />
      <LinhaLista titulo="Vestibulares" subtitulo="Cadastrar e validar datas e instituições" icone="event" onPress={() => router.push('/admin/vestibulares')} />

      <Titulo>Engajamento</Titulo>
      <View style={styles.grade}>
        <Indicador valor={s.total_alunos} rotulo="Alunos cadastrados" extra="Contas do tipo aluno" />
        <Indicador valor={s.total_favoritos} rotulo="Favoritos salvos" extra="Cursos, faculdades e vestibulares" />
        <Indicador valor={s.total_testes_vocacionais} rotulo="Testes vocacionais" extra="Resultados registrados" />
        <Indicador valor={s.vestibulares_encerrados} rotulo="Vestibulares encerrados" extra="Prova já realizada" />
      </View>

      <Titulo>Automações recentes</Titulo>
      {automacoes.length === 0 ? (
        <Text style={[tipografia.descricao, styles.cinza]}>Nenhuma automação executada ainda.</Text>
      ) : (
        automacoes.map((a) => <LinhaAutomacao key={a.id} a={a} />)
      )}
    </Tela>
  );
}

function Indicador({ valor, rotulo, extra }: { valor: number | undefined; rotulo: string; extra?: string }) {
  return (
    <View style={styles.indicador} accessible accessibilityLabel={`${valor ?? 0} ${rotulo}${extra ? `, ${extra}` : ''}`}>
      <Text style={styles.valor}>{valor ?? '–'}</Text>
      <Text style={styles.rotulo}>{rotulo}</Text>
      {!!extra && <Text style={styles.extra}>{extra}</Text>}
    </View>
  );
}

function LinhaAutomacao({ a }: { a: Automacao }) {
  const ok = a.sucesso === true || a.sucesso === 1;
  return (
    <LinhaLista
      titulo={a.tipo.replace(/_/g, ' ')}
      subtitulo={[a.executado_em, ok ? 'concluída' : (a.status ?? 'falhou'), a.resumo].filter(Boolean).join(' · ')}
      icone={ok ? 'check-circle' : 'error-outline'}
    />
  );
}

function Titulo({ children }: { children: string }) {
  return (
    <Text style={[tipografia.tituloBloco, styles.titulo]} accessibilityRole="header">
      {children}
    </Text>
  );
}

const styles = StyleSheet.create({
  titulo: { color: cores.roxoEscuro, marginTop: espaco.sm },
  cinza: { color: cores.textoSuave },
  grade: { flexDirection: 'row', flexWrap: 'wrap', gap: espaco.smd },
  indicador: { flexBasis: '47%', flexGrow: 1, backgroundColor: cores.superficie, borderRadius: raio.linha, padding: espaco.md, gap: 2, ...sombra },
  valor: { fontFamily: familias.interNegrito, fontSize: 28, color: cores.roxo },
  rotulo: { ...tipografia.rotulo, fontSize: 14, color: cores.roxoEscuro },
  extra: { ...tipografia.legenda, color: cores.textoSuave },
});
