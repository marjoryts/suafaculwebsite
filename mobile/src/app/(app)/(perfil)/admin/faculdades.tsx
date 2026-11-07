import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { importarFaculdades } from '../../../../api/admin';
import { listarFaculdades } from '../../../../api/catalogo';
import type { Faculdade } from '../../../../api/tipos';
import { juntar, local, plural } from '../../../../catalogo/formatar';
import { ExigirAdmin } from '../../../../components/admin/ExigirAdmin';
import { confirmar } from '../../../../components/admin/confirmar';
import { resumoImportacao } from '../../../../components/admin/relatorios';
import { GrupoFiltro } from '../../../../components/catalogo/GrupoFiltro';
import { ListaPaginada } from '../../../../components/catalogo/ListaPaginada';
import { Botao } from '../../../../components/ui/Botao';
import { CampoBusca } from '../../../../components/ui/CampoBusca';
import { CampoTexto } from '../../../../components/ui/CampoTexto';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useAtrasado } from '../../../../hooks/useAtrasado';
import { mensagemDeErro } from '../../../../hooks/useConsulta';
import { usePaginacao } from '../../../../hooks/usePaginacao';
import { cores, espaco, raio, tipografia } from '../../../../theme/tokens';

const UFS = ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
  'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'].map((uf) => ({ rotulo: uf, valor: uf }));

// Seção "Faculdades" do painel: lista com busca, cadastro manual e importação do e-MEC.
// O envio de CSV (dados abertos do MEC) fica só no site: o arquivo tem centenas de MB.
export default function FaculdadesAdmin() {
  return (
    <ExigirAdmin titulo="Faculdades">
      <Conteudo />
    </ExigirAdmin>
  );
}

function Conteudo() {
  const router = useRouter();
  const [texto, setTexto] = useState('');
  const busca = useAtrasado(texto.trim());
  const pagina = usePaginacao((p) => listarFaculdades({ busca }, p), [busca]);
  const { recarregar } = pagina;
  useFocusEffect(
    useCallback(() => {
      void recarregar();
    }, [recarregar]),
  );

  const [codigos, setCodigos] = useState('');
  const [uf, setUf] = useState<string[]>([]);
  const [importando, setImportando] = useState(false);
  const [resultado, setResultado] = useState<{ ok: boolean; texto: string } | null>(null);

  async function importar(alvo: Parameters<typeof importarFaculdades>[0]) {
    setResultado(null);
    setImportando(true);
    try {
      const { data } = await importarFaculdades(alvo);
      setResultado({ ok: data.success !== false, texto: resumoImportacao(data) });
      void recarregar();
    } catch (e) {
      setResultado({ ok: false, texto: mensagemDeErro(e) });
    } finally {
      setImportando(false);
    }
  }

  const listaCodigos = codigos.split(',').map((c) => c.trim()).filter(Boolean);

  return (
    <Tela cabecalho={{ titulo: 'Faculdades' }} rolar={false}>
      <ListaPaginada<Faculdade>
        pagina={pagina}
        chave={(f) => String(f.id)}
        contagem={(n) => plural(n, 'faculdade', 'faculdades')}
        vazio={{ titulo: 'Nenhuma faculdade encontrada', mensagem: 'Tente outra busca.' }}
        cabecalho={
          <>
            <Botao titulo="Cadastrar manualmente" icone="add" tamanho="compacto" onPress={() => router.push('/admin/faculdade')} />

            <View style={styles.caixa}>
              <Text style={[tipografia.tituloBloco, styles.roxo]}>Importar do e-MEC</Text>
              <CampoTexto
                rotulo="Códigos e-MEC (separe por vírgula)"
                placeholder="Ex.: 339, 55"
                value={codigos}
                onChangeText={setCodigos}
                keyboardType="numbers-and-punctuation"
              />
              <Botao
                titulo="Importar códigos"
                variante="secundario"
                tamanho="compacto"
                desabilitado={importando || listaCodigos.length === 0}
                onPress={() => void importar({ codigos: listaCodigos })}
              />
              <GrupoFiltro rotulo="Por UF" opcoes={UFS} selecionados={uf} onAlternar={(v) => setUf((u) => (u[0] === v ? [] : [v]))} />
              <Botao
                titulo={uf[0] ? `Importar ${uf[0]}` : 'Escolha uma UF'}
                variante="secundario"
                tamanho="compacto"
                desabilitado={importando || !uf[0]}
                onPress={() =>
                  confirmar('Importar UF', `Importar todas as instituições ativas de ${uf[0]}? Pode levar alguns minutos.`, () =>
                    void importar({ uf: uf[0] }), 'Importar')
                }
              />
              <Botao
                titulo="Brasil (27 UFs)"
                variante="secundario"
                tamanho="compacto"
                desabilitado={importando}
                onPress={() =>
                  confirmar('Importar o Brasil inteiro', 'Importar as instituições ativas das 27 UFs? Leva vários minutos.', () =>
                    void importar({ brasil: true }), 'Importar')
                }
              />
              {importando && <Text style={[tipografia.descricao, styles.cinza]}>Importando... isso pode levar alguns minutos.</Text>}
              {!!resultado && (
                <Text style={[tipografia.rotulo, { color: resultado.ok ? cores.sucesso : cores.erro }]} accessibilityLiveRegion="polite">
                  {resultado.texto}
                </Text>
              )}
              <Text style={[tipografia.descricao, styles.cinza]}>O envio do CSV oficial do MEC está disponível no painel do site.</Text>
            </View>

            <CampoBusca placeholder="Buscar por nome, sigla ou cidade..." value={texto} onChangeText={setTexto} autoCapitalize="none" />
          </>
        }
        renderItem={(f) => (
          <LinhaLista
            titulo={f.nome}
            subtitulo={juntar(f.sigla, local(f.cidade, f.uf), f.tipo_instituicao, f.codigo_emec ? `e-MEC ${f.codigo_emec}` : undefined)}
            icone="school"
            onPress={() => router.push({ pathname: '/admin/faculdade', params: { id: String(f.id) } })}
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
});
