import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';

import { listarCursos } from '../../../../api/catalogo';
import type { Curso } from '../../../../api/tipos';
import { juntar, modalidade, plural } from '../../../../catalogo/formatar';
import { ExigirAdmin } from '../../../../components/admin/ExigirAdmin';
import { ListaPaginada } from '../../../../components/catalogo/ListaPaginada';
import { Botao } from '../../../../components/ui/Botao';
import { CampoBusca } from '../../../../components/ui/CampoBusca';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useAtrasado } from '../../../../hooks/useAtrasado';
import { usePaginacao } from '../../../../hooks/usePaginacao';

// Seção "Cursos" do painel: lista com busca e cadastro. A importação do CSV do Censo
// INEP fica só no site (arquivo de centenas de MB).
export default function CursosAdmin() {
  return (
    <ExigirAdmin titulo="Cursos">
      <Conteudo />
    </ExigirAdmin>
  );
}

function Conteudo() {
  const router = useRouter();
  const [texto, setTexto] = useState('');
  const busca = useAtrasado(texto.trim());
  const pagina = usePaginacao((p) => listarCursos({ busca }, p), [busca]);
  const { recarregar } = pagina;
  useFocusEffect(
    useCallback(() => {
      void recarregar();
    }, [recarregar]),
  );

  return (
    <Tela cabecalho={{ titulo: 'Cursos' }} rolar={false}>
      <ListaPaginada<Curso>
        pagina={pagina}
        chave={(c) => String(c.id)}
        contagem={(n) => plural(n, 'curso', 'cursos')}
        vazio={{ titulo: 'Nenhum curso encontrado', mensagem: 'Tente outra busca.' }}
        cabecalho={
          <>
            <Botao titulo="Cadastrar curso" icone="add" tamanho="compacto" onPress={() => router.push('/admin/curso')} />
            <CampoBusca placeholder="Buscar por nome, instituição ou área..." value={texto} onChangeText={setTexto} autoCapitalize="none" />
          </>
        }
        renderItem={(c) => (
          <LinhaLista
            titulo={c.nome}
            subtitulo={juntar(c.instituicao, c.area, modalidade(c.modalidade))}
            icone="menu-book"
            onPress={() => router.push(`/cursos/${c.id}`)}
          />
        )}
      />
    </Tela>
  );
}
