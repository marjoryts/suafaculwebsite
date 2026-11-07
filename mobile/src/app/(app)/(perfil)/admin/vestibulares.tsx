import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { validarVestibulares } from '../../../../api/admin';
import { listarVestibulares } from '../../../../api/catalogo';
import type { RelatorioValidacao, Vestibular } from '../../../../api/tipos';
import { resumoProva } from '../../../../catalogo/datas';
import { plural } from '../../../../catalogo/formatar';
import { ExigirAdmin } from '../../../../components/admin/ExigirAdmin';
import { confirmar } from '../../../../components/admin/confirmar';
import { ListaPaginada } from '../../../../components/catalogo/ListaPaginada';
import { Botao } from '../../../../components/ui/Botao';
import { CampoBusca } from '../../../../components/ui/CampoBusca';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useAtrasado } from '../../../../hooks/useAtrasado';
import { mensagemDeErro } from '../../../../hooks/useConsulta';
import { usePaginacao } from '../../../../hooks/usePaginacao';
import { cores, espaco, raio, tipografia } from '../../../../theme/tokens';

const SITUACAO: Record<string, string> = {
  ativo: 'Prova futura',
  encerrado: 'Prova realizada',
  data_invalida: 'Data inválida',
  nao_validado: 'Não validado',
};

// Seção "Vestibulares" do painel: validação automática (pré-visualizar ou aplicar),
// lista (públicos e privados) e cadastro.
export default function VestibularesAdmin() {
  return (
    <ExigirAdmin titulo="Vestibulares">
      <Conteudo />
    </ExigirAdmin>
  );
}

function Conteudo() {
  const router = useRouter();
  const [texto, setTexto] = useState('');
  const busca = useAtrasado(texto.trim());
  const pagina = usePaginacao((p) => listarVestibulares({ busca, instituicao: 'Todas' }, p), [busca]);
  const { recarregar } = pagina;
  useFocusEffect(
    useCallback(() => {
      void recarregar();
    }, [recarregar]),
  );

  const [validando, setValidando] = useState(false);
  const [relatorio, setRelatorio] = useState<RelatorioValidacao | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function validar(aplicar: boolean) {
    setErro(null);
    setValidando(true);
    try {
      setRelatorio((await validarVestibulares(aplicar)).data);
      if (aplicar) void recarregar();
    } catch (e) {
      setErro(mensagemDeErro(e));
    } finally {
      setValidando(false);
    }
  }

  const r = relatorio?.resumo;
  return (
    <Tela cabecalho={{ titulo: 'Vestibulares' }} rolar={false}>
      <ListaPaginada<Vestibular>
        pagina={pagina}
        chave={(v) => String(v.id)}
        contagem={(n) => plural(n, 'vestibular', 'vestibulares')}
        vazio={{ titulo: 'Nenhum vestibular encontrado', mensagem: 'Tente outra busca.' }}
        cabecalho={
          <>
            <Botao titulo="Cadastrar vestibular" icone="add" tamanho="compacto" onPress={() => router.push('/admin/vestibular')} />

            <View style={styles.caixa}>
              <Text style={[tipografia.tituloBloco, styles.roxo]}>Validação automática</Text>
              <Text style={[tipografia.descricao, styles.cinza]}>
                Confere as datas das provas e se a instituição já está cadastrada.
              </Text>
              <View style={styles.linha}>
                <View style={styles.metade}>
                  <Botao titulo="Pré-visualizar" variante="secundario" tamanho="compacto" desabilitado={validando} onPress={() => void validar(false)} />
                </View>
                <View style={styles.metade}>
                  <Botao
                    titulo="Validar e aplicar"
                    tamanho="compacto"
                    carregando={validando}
                    onPress={() =>
                      confirmar('Validar e aplicar', 'Gravar o resultado da validação em todos os vestibulares?', () => void validar(true), 'Aplicar')
                    }
                  />
                </View>
              </View>
              {!!erro && <Text style={[tipografia.corpo, { color: cores.erro }]}>{erro}</Text>}
              {!!r && (
                <View style={styles.resumo} accessibilityLiveRegion="polite">
                  <Text style={[tipografia.rotulo, styles.roxo]}>
                    {r.aplicado ? 'Validação aplicada' : 'Pré-visualização (nada foi gravado)'}
                  </Text>
                  <Text style={[tipografia.descricao, styles.cinza]}>
                    {r.total} no total · {r.ativos} com prova futura · {r.encerrados} realizados · {r.data_invalida} com
                    data inválida · {r.sem_faculdade_cadastrada} sem faculdade cadastrada
                    {r.falhas ? ` · ${r.falhas} falha(s)` : ''}
                  </Text>
                  {relatorio!.itens
                    .filter((i) => i.status_validacao !== 'ativo' || !i.cadastrado_ok)
                    .slice(0, 20)
                    .map((i) => (
                      <Text key={i.vestibular_id} style={[tipografia.descricao, styles.cinza]}>
                        • {i.nome}: {SITUACAO[i.status_validacao] ?? i.status_validacao}
                        {i.cadastrado_ok ? '' : ' · faculdade não cadastrada'}
                      </Text>
                    ))}
                </View>
              )}
            </View>

            <CampoBusca placeholder="Buscar por nome, instituição ou cidade..." value={texto} onChangeText={setTexto} autoCapitalize="none" />
          </>
        }
        renderItem={(v) => (
          <LinhaLista
            titulo={v.nome}
            subtitulo={[resumoProva(v), v.tipo_instituicao, v.status ? SITUACAO[v.status] : undefined].filter(Boolean).join(' · ')}
            icone="event"
            onPress={() => router.push(`/vestibulares/${v.id}`)}
          />
        )}
      />
    </Tela>
  );
}

const styles = StyleSheet.create({
  caixa: { backgroundColor: cores.superficie, borderRadius: raio.linha, padding: espaco.md, gap: espaco.smd },
  roxo: { color: cores.roxoEscuro },
  cinza: { color: cores.textoSuave },
  linha: { flexDirection: 'row', gap: espaco.sm },
  metade: { flex: 1 },
  resumo: { gap: espaco.xs },
});
