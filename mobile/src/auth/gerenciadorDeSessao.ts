// Estado dos tokens + regras de TRANSPORTE da sessão (sem React, testável).
//
// O refresh token do backend é de USO ÚNICO: cada renovação invalida o token
// enviado. Por isso:
//   - chamadas simultâneas esperam a MESMA renovação (single-flight); duas
//     renovações paralelas com o mesmo token derrubariam a sessão no servidor;
//   - o novo refresh token é gravado no armazenamento ANTES de ser usado;
//   - só apagamos a sessão quando o servidor responde 401. Falha de rede NÃO
//     desloga o usuário.
import { ApiError, ProvedorDeSessao } from '../api/client';
import type { Tokens } from '../api/tipos';
import type { TokenStorage } from './tokenStorage';

type Dependencias = {
  storage: TokenStorage;
  /** Chama POST /auth/refresh. */
  renovarNoServidor: (refreshToken: string) => Promise<Tokens>;
  /** Avisado quando a sessão termina (a interface volta para o login). */
  aoEncerrar: () => void;
};

export class GerenciadorDeSessao implements ProvedorDeSessao {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private renovacao: Promise<string> | null = null;

  constructor(private readonly dep: Dependencias) {}

  obterAccessToken() {
    return this.accessToken;
  }

  obterRefreshToken() {
    return this.refreshToken;
  }

  /** Guarda um par de tokens recém-emitido (login, cadastro ou renovação). */
  async definir(tokens: Tokens) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    await this.dep.storage.gravar(tokens.refresh_token);
  }

  /** Ao abrir o app: há sessão guardada? Se sim, renova. Devolve true se restaurou. */
  async restaurar(): Promise<boolean> {
    const guardado = await this.dep.storage.ler();
    if (!guardado) return false;
    this.refreshToken = guardado;
    try {
      await this.renovar();
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) throw e; // sem rede: mantém a sessão guardada
      return false;
    }
  }

  renovar(): Promise<string> {
    if (this.renovacao) return this.renovacao;

    this.renovacao = (async () => {
      const refresh = this.refreshToken;
      if (!refresh) throw new ApiError(401, 'INVALID_REFRESH_TOKEN', 'Sem sessão.');
      try {
        const novos = await this.dep.renovarNoServidor(refresh);
        await this.definir(novos);
        return novos.access_token;
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) await this.encerrar();
        throw e;
      }
    })().finally(() => {
      this.renovacao = null;
    });
    return this.renovacao;
  }

  /** Limpa tudo localmente e avisa a interface. */
  async encerrar() {
    this.accessToken = null;
    this.refreshToken = null;
    await this.dep.storage.apagar().catch(() => undefined);
    this.dep.aoEncerrar();
  }

  aoPerderSessao() {
    void this.encerrar();
  }
}
