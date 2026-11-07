import { useFocusEffect, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { listarUsuarios } from '../../../../api/admin';
import type { UsuarioAdmin } from '../../../../api/tipos';
import { normalizar, plural } from '../../../../catalogo/formatar';
import { ExigirAdmin } from '../../../../components/admin/ExigirAdmin';
import { Botao } from '../../../../components/ui/Botao';
import { CampoBusca } from '../../../../components/ui/CampoBusca';
import { Carregando, EstadoErro, EstadoVazio } from '../../../../components/ui/Estados';
import { LinhaLista } from '../../../../components/ui/LinhaLista';
import { Tela } from '../../../../components/ui/Tela';
import { useConsulta } from '../../../../hooks/useConsulta';
import { cores, tipografia } from '../../../../theme/tokens';

// Seção "Usuários" do painel: lista com busca por nome ou e-mail (filtro local, como no site).
export default function Usuarios() {
  return (
    <ExigirAdmin titulo="Usuários">
      <Conteudo />
    </ExigirAdmin>
  );
}

function Conteudo() {
  const router = useRouter();
  const [busca, setBusca] = useState('');
  const consulta = useConsulta(async () => (await listarUsuarios()).data, []);
  const { recarregar } = consulta;
  useFocusEffect(
    useCallback(() => {
      void recarregar(); // volta do formulário com a lista atualizada
    }, [recarregar]),
  );

  const termo = normalizar(busca.trim());
  const usuarios = (consulta.dados ?? []).filter(
    (u) => !termo || normalizar(`${u.nome_usuario} ${u.email}`).includes(termo),
  );

  function abrir(u?: UsuarioAdmin) {
    router.push(u ? { pathname: '/admin/usuario', params: { ...u, id: String(u.id) } } : '/admin/usuario');
  }

  return (
    <Tela cabecalho={{ titulo: 'Usuários' }}>
      <Botao titulo="Adicionar usuário" icone="person-add" tamanho="compacto" onPress={() => abrir()} />
      <CampoBusca placeholder="Buscar por nome ou e-mail..." value={busca} onChangeText={setBusca} autoCapitalize="none" />
      {!consulta.dados ? (
        consulta.carregando ? <Carregando /> : <EstadoErro mensagem={consulta.erro ?? 'Erro.'} onTentarNovamente={recarregar} />
      ) : usuarios.length === 0 ? (
        <EstadoVazio icone="person-search" titulo="Nenhum usuário encontrado" />
      ) : (
        <>
          <Text style={[tipografia.descricao, styles.cinza]}>{plural(usuarios.length, 'usuário', 'usuários')}</Text>
          {usuarios.map((u) => (
            <LinhaLista
              key={u.id}
              titulo={u.nome_usuario}
              subtitulo={`${u.email} · ${u.tipo === 'admin' ? 'Administrador' : 'Aluno'}`}
              icone={u.tipo === 'admin' ? 'admin-panel-settings' : 'person'}
              onPress={() => abrir(u)}
            />
          ))}
        </>
      )}
    </Tela>
  );
}

const styles = StyleSheet.create({ cinza: { color: cores.textoSuave } });
