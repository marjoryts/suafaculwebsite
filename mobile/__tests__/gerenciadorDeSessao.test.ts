import { ApiError } from '../src/api/client';
import type { Tokens } from '../src/api/tipos';
import { GerenciadorDeSessao } from '../src/auth/gerenciadorDeSessao';
import type { TokenStorage } from '../src/auth/tokenStorage';

const tokens = (n: number): Tokens => ({
  token_type: 'Bearer',
  access_token: `access-${n}`,
  expires_in: 900,
  refresh_token: `refresh-${n}`,
  refresh_expires_in: 2592000,
});

function criar(opcoes: { guardado?: string | null; renovar?: (r: string) => Promise<Tokens> } = {}) {
  let guardado: string | null = opcoes.guardado ?? null;
  const storage: TokenStorage = {
    ler: jest.fn(async () => guardado),
    gravar: jest.fn(async (t: string) => {
      guardado = t;
    }),
    apagar: jest.fn(async () => {
      guardado = null;
    }),
  };
  const renovarNoServidor = jest.fn(opcoes.renovar ?? (async () => tokens(2)));
  const aoEncerrar = jest.fn();
  const gerenciador = new GerenciadorDeSessao({ storage, renovarNoServidor, aoEncerrar });
  return { gerenciador, storage, renovarNoServidor, aoEncerrar, guardado: () => guardado };
}

describe('definir / encerrar', () => {
  it('guarda no armazenamento seguro SOMENTE o refresh token', async () => {
    const { gerenciador, storage } = criar();
    await gerenciador.definir(tokens(1));
    expect(storage.gravar).toHaveBeenCalledWith('refresh-1');
    expect(gerenciador.obterAccessToken()).toBe('access-1');
    expect(gerenciador.obterRefreshToken()).toBe('refresh-1');
  });

  it('encerrar apaga tudo e avisa a interface', async () => {
    const { gerenciador, aoEncerrar, guardado } = criar();
    await gerenciador.definir(tokens(1));
    await gerenciador.encerrar();
    expect(gerenciador.obterAccessToken()).toBeNull();
    expect(guardado()).toBeNull();
    expect(aoEncerrar).toHaveBeenCalledTimes(1);
  });
});

describe('renovar (refresh token de uso único)', () => {
  it('chamadas simultâneas esperam a MESMA renovação (single-flight)', async () => {
    let liberar!: (t: Tokens) => void;
    const { gerenciador, renovarNoServidor } = criar({
      renovar: () => new Promise<Tokens>((r) => (liberar = r)),
    });
    await gerenciador.definir(tokens(1));

    const tres = [gerenciador.renovar(), gerenciador.renovar(), gerenciador.renovar()];
    liberar(tokens(2));

    expect(await Promise.all(tres)).toEqual(['access-2', 'access-2', 'access-2']);
    expect(renovarNoServidor).toHaveBeenCalledTimes(1); // duas renovações paralelas derrubariam a sessão
  });

  it('usa o refresh token NOVO na renovação seguinte (rotação) e o grava', async () => {
    let n = 1;
    const { gerenciador, renovarNoServidor, guardado } = criar({ renovar: async () => tokens(++n) });
    await gerenciador.definir(tokens(1));

    await gerenciador.renovar();
    await gerenciador.renovar();

    expect(renovarNoServidor.mock.calls.map((c) => c[0])).toEqual(['refresh-1', 'refresh-2']);
    expect(guardado()).toBe('refresh-3');
  });

  it('depois de terminar, uma nova renovação pode acontecer', async () => {
    const { gerenciador, renovarNoServidor } = criar();
    await gerenciador.definir(tokens(1));
    await gerenciador.renovar();
    await gerenciador.renovar();
    expect(renovarNoServidor).toHaveBeenCalledTimes(2);
  });

  it('sem refresh token falha com 401 sem chamar o servidor', async () => {
    const { gerenciador, renovarNoServidor } = criar();
    await expect(gerenciador.renovar()).rejects.toMatchObject({ status: 401 });
    expect(renovarNoServidor).not.toHaveBeenCalled();
  });

  it('401 do servidor encerra a sessão (refresh reusado/expirado/revogado)', async () => {
    const { gerenciador, aoEncerrar, guardado } = criar({
      renovar: async () => {
        throw new ApiError(401, 'REFRESH_TOKEN_REUSED', 'Sessão encerrada.');
      },
    });
    await gerenciador.definir(tokens(1));
    await expect(gerenciador.renovar()).rejects.toMatchObject({ code: 'REFRESH_TOKEN_REUSED' });
    expect(aoEncerrar).toHaveBeenCalledTimes(1);
    expect(guardado()).toBeNull();
  });

  it('falha de REDE não derruba a sessão', async () => {
    const { gerenciador, aoEncerrar, guardado } = criar({
      renovar: async () => {
        throw new ApiError(0, 'NETWORK_ERROR', 'Sem rede.');
      },
    });
    await gerenciador.definir(tokens(1));
    await expect(gerenciador.renovar()).rejects.toMatchObject({ status: 0 });
    expect(aoEncerrar).not.toHaveBeenCalled();
    expect(guardado()).toBe('refresh-1'); // continua guardado para tentar de novo
  });
});

describe('restaurar (abrir o app)', () => {
  it('sem token guardado: não há sessão e não chama o servidor', async () => {
    const { gerenciador, renovarNoServidor } = criar({ guardado: null });
    expect(await gerenciador.restaurar()).toBe(false);
    expect(renovarNoServidor).not.toHaveBeenCalled();
  });

  it('com token guardado: renova e fica autenticado', async () => {
    const { gerenciador, renovarNoServidor } = criar({ guardado: 'refresh-guardado' });
    expect(await gerenciador.restaurar()).toBe(true);
    expect(renovarNoServidor).toHaveBeenCalledWith('refresh-guardado');
    expect(gerenciador.obterAccessToken()).toBe('access-2');
  });

  it('token guardado inválido: devolve false e limpa o armazenamento', async () => {
    const { gerenciador, guardado } = criar({
      guardado: 'velho',
      renovar: async () => {
        throw new ApiError(401, 'INVALID_REFRESH_TOKEN', 'Inválido.');
      },
    });
    expect(await gerenciador.restaurar()).toBe(false);
    expect(guardado()).toBeNull();
  });

  it('sem rede ao abrir: propaga o erro e MANTÉM o token guardado', async () => {
    const { gerenciador, guardado, aoEncerrar } = criar({
      guardado: 'refresh-guardado',
      renovar: async () => {
        throw new ApiError(0, 'NETWORK_ERROR', 'Sem rede.');
      },
    });
    await expect(gerenciador.restaurar()).rejects.toMatchObject({ status: 0 });
    expect(guardado()).toBe('refresh-guardado');
    expect(aoEncerrar).not.toHaveBeenCalled();
  });
});
