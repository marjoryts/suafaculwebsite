// Cliente HTTP da API /api/v1. Só transporte: envia o Bearer, renova o token
// uma vez quando ele expira e traduz o envelope de erro do backend.
// Nenhuma regra de negócio mora no app.
import { API_V1_URL } from '../config';

/** Erro devolvido pelo backend: { error: { code, message, request_id } }. */
export class ApiError extends Error {
  constructor(
    public readonly status: number, // 0 = sem resposta (rede/timeout)
    public readonly code: string,
    message: string,
    public readonly requestId?: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/** O que o cliente precisa saber da sessão (implementado em auth/gerenciadorDeSessao.ts). */
export type ProvedorDeSessao = {
  obterAccessToken(): string | null;
  /** Troca o refresh token por um novo par e devolve o novo access token. */
  renovar(): Promise<string>;
  /** O servidor disse que a sessão não vale mais (revogada/inválida). */
  aoPerderSessao(): void;
};

let provedor: ProvedorDeSessao | null = null;

export function configurarProvedorDeSessao(p: ProvedorDeSessao | null) {
  provedor = p;
}

export type Opcoes = {
  metodo?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  corpo?: unknown;
  /** Envia o Bearer e renova o token se ele tiver expirado. */
  autenticado?: boolean;
  /** Tempo limite em ms (padrão 10 s). Importações do painel admin levam minutos. */
  timeoutMs?: number;
};

const TIMEOUT_MS = 10_000;

async function enviar<T>(caminho: string, opcoes: Opcoes, accessToken: string | null): Promise<T> {
  const controle = new AbortController();
  const limite = setTimeout(() => controle.abort(), opcoes.timeoutMs ?? TIMEOUT_MS);

  const cabecalhos: Record<string, string> = { Accept: 'application/json' };
  if (opcoes.corpo !== undefined) cabecalhos['Content-Type'] = 'application/json';
  if (accessToken) cabecalhos.Authorization = `Bearer ${accessToken}`;

  let resposta: Response;
  try {
    resposta = await fetch(`${API_V1_URL}${caminho}`, {
      method: opcoes.metodo ?? 'GET',
      headers: cabecalhos,
      body: opcoes.corpo === undefined ? undefined : JSON.stringify(opcoes.corpo),
      signal: controle.signal,
    });
  } catch {
    // Em desenvolvimento mostra o endereço usado: o erro mais comum é um IP errado em .env.local.
    const aviso = __DEV__ ? ` Endereço da API: ${API_V1_URL}` : '';
    throw new ApiError(0, 'NETWORK_ERROR', `Não foi possível conectar ao servidor.${aviso}`);
  } finally {
    clearTimeout(limite);
  }

  if (resposta.status === 204) return undefined as T;
  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const erro = corpo?.error;
    throw new ApiError(
      resposta.status,
      erro?.code ?? 'HTTP_ERROR',
      erro?.message ?? `Erro ${resposta.status}`,
      erro?.request_id,
      erro?.details,
    );
  }
  return corpo as T;
}

export async function api<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  if (!opcoes.autenticado) return enviar<T>(caminho, opcoes, null);

  try {
    return await enviar<T>(caminho, opcoes, provedor?.obterAccessToken() ?? null);
  } catch (e) {
    if (!(e instanceof ApiError) || e.status !== 401 || !provedor) throw e;

    if (e.code === 'TOKEN_EXPIRED') {
      // Renova (chamadas simultâneas esperam a MESMA renovação) e repete uma única vez.
      const novoToken = await provedor.renovar();
      try {
        return await enviar<T>(caminho, opcoes, novoToken);
      } catch (e2) {
        if (e2 instanceof ApiError && e2.status === 401) provedor.aoPerderSessao();
        throw e2;
      }
    }
    provedor.aoPerderSessao(); // INVALID_TOKEN / UNAUTHENTICATED: a sessão acabou
    throw e;
  }
}
