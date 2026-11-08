import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import * as authApi from '../api/auth';
import { ApiError, configurarProvedorDeSessao } from '../api/client';
import type { Usuario } from '../api/tipos';
import { GerenciadorDeSessao } from './gerenciadorDeSessao';
import { tokenStorage } from './tokenStorage';

export type EstadoDaSessao = 'carregando' | 'autenticado' | 'anonimo' | 'sem-conexao';

type ContextoDaSessao = {
  estado: EstadoDaSessao;
  usuario: Usuario | null;
  entrar(email: string, senha: string): Promise<void>;
  /** Login com Google: recebe o ID token do Google Sign-In (módulo nativo, development build). */
  entrarComGoogle(idToken: string): Promise<void>;
  cadastrar(nomeUsuario: string, email: string, senha: string): Promise<void>;
  sair(): Promise<void>;
  /** Recarrega o perfil (ex.: depois de editar). */
  atualizarUsuario(usuario: Usuario): void;
  /** Repete a restauração da sessão (tela "sem conexão"). */
  tentarNovamente(): void;
};

const Contexto = createContext<ContextoDaSessao | null>(null);

export function SessaoProvider({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<EstadoDaSessao>('carregando');
  const [usuario, setUsuario] = useState<Usuario | null>(null);

  // Um único gerenciador por execução do app.
  const gerenciador = useRef<GerenciadorDeSessao | null>(null);
  if (gerenciador.current === null) {
    gerenciador.current = new GerenciadorDeSessao({
      storage: tokenStorage,
      renovarNoServidor: async (refresh) => (await authApi.renovar(refresh)).data.tokens,
      aoEncerrar: () => {
        setUsuario(null);
        setEstado('anonimo');
      },
    });
    configurarProvedorDeSessao(gerenciador.current);
  }
  const g = gerenciador.current;

  const iniciar = useCallback(async () => {
    setEstado('carregando');
    try {
      if (!(await g.restaurar())) {
        setEstado('anonimo');
        return;
      }
      setUsuario((await authApi.meuPerfil()).data);
      setEstado('autenticado');
    } catch (e) {
      // Sem rede não é o mesmo que "sem sessão": mantém o token guardado e deixa tentar de novo.
      setEstado(e instanceof ApiError && e.status === 0 ? 'sem-conexao' : 'anonimo');
    }
  }, [g]);

  useEffect(() => {
    void iniciar();
  }, [iniciar]);

  const valor = useMemo<ContextoDaSessao>(
    () => ({
      estado,
      usuario,
      async entrar(email, senha) {
        const { data } = await authApi.entrar(email, senha);
        await g.definir(data.tokens);
        setUsuario(data.usuario);
        setEstado('autenticado');
      },
      async entrarComGoogle(idToken) {
        const { data } = await authApi.entrarComGoogle(idToken);
        await g.definir(data.tokens);
        setUsuario(data.usuario);
        setEstado('autenticado');
      },
      async cadastrar(nomeUsuario, email, senha) {
        const { data } = await authApi.cadastrar(nomeUsuario, email, senha);
        await g.definir(data.tokens);
        setUsuario(data.usuario);
        setEstado('autenticado');
      },
      async sair() {
        const refresh = g.obterRefreshToken();
        try {
          if (refresh) await authApi.sair(refresh);
        } catch {
          // Sem rede o logout no servidor falha; a sessão local é apagada de qualquer jeito.
        }
        await g.encerrar();
      },
      atualizarUsuario: setUsuario,
      tentarNovamente: () => void iniciar(),
    }),
    [estado, usuario, g, iniciar],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSessao(): ContextoDaSessao {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error('useSessao deve ser usado dentro de <SessaoProvider>.');
  return contexto;
}
