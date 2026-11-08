import { api, ApiError, configurarProvedorDeSessao, ProvedorDeSessao } from '../src/api/client';

function resposta(status: number, corpo?: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => {
      if (corpo === undefined) throw new Error('sem corpo');
      return corpo;
    },
  } as unknown as Response;
}

const erro = (status: number, code: string, message = 'msg') =>
  resposta(status, { error: { code, message, request_id: 'req-1' } });

let fetchMock: jest.Mock;

beforeEach(() => {
  fetchMock = jest.fn();
  global.fetch = fetchMock as unknown as typeof fetch;
  configurarProvedorDeSessao(null);
});

function provedor(parcial: Partial<ProvedorDeSessao> = {}) {
  const p: ProvedorDeSessao = {
    obterAccessToken: jest.fn(() => 'access-1'),
    renovar: jest.fn(async () => 'access-2'),
    aoPerderSessao: jest.fn(),
    ...parcial,
  };
  configurarProvedorDeSessao(p);
  return p;
}

const authDe = (chamada: number) => fetchMock.mock.calls[chamada][1].headers.Authorization;

describe('requisições', () => {
  it('chama /api/v1, envia JSON e devolve o corpo', async () => {
    fetchMock.mockResolvedValue(resposta(200, { data: 1 }));
    expect(await api('/cursos?limit=1')).toEqual({ data: 1 });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/api\/v1\/cursos\?limit=1$/);
    expect(init.headers.Accept).toBe('application/json');
    expect(init.headers.Authorization).toBeUndefined();
  });

  it('serializa o corpo e define Content-Type só quando há corpo', async () => {
    fetchMock.mockResolvedValue(resposta(200, {}));
    await api('/auth/login', { metodo: 'POST', corpo: { email: 'a@b.com' } });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe('POST');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(init.body).toBe('{"email":"a@b.com"}');
  });

  it('204 devolve undefined', async () => {
    fetchMock.mockResolvedValue(resposta(204));
    expect(await api('/auth/logout', { metodo: 'POST', corpo: {} })).toBeUndefined();
  });

  it('traduz o envelope de erro do backend', async () => {
    fetchMock.mockResolvedValue(erro(422, 'VALIDATION_ERROR', 'Dados inválidos.'));
    await expect(api('/x')).rejects.toMatchObject({
      status: 422,
      code: 'VALIDATION_ERROR',
      message: 'Dados inválidos.',
      requestId: 'req-1',
    });
  });

  it('erro sem corpo JSON vira HTTP_ERROR', async () => {
    fetchMock.mockResolvedValue(resposta(502));
    await expect(api('/x')).rejects.toMatchObject({ status: 502, code: 'HTTP_ERROR' });
  });

  it('falha de rede vira ApiError status 0', async () => {
    fetchMock.mockRejectedValue(new TypeError('Network request failed'));
    const e = await api('/x').catch((x) => x);
    expect(e).toBeInstanceOf(ApiError);
    expect(e).toMatchObject({ status: 0, code: 'NETWORK_ERROR' });
  });

  it('rotas públicas nunca enviam Authorization nem consultam a sessão', async () => {
    const p = provedor();
    fetchMock.mockResolvedValue(resposta(200, {}));
    await api('/cursos');
    expect(authDe(0)).toBeUndefined();
    expect(p.obterAccessToken).not.toHaveBeenCalled();
  });
});

describe('autenticadas: renovação do token', () => {
  it('envia o Bearer', async () => {
    provedor();
    fetchMock.mockResolvedValue(resposta(200, { data: 1 }));
    await api('/me', { autenticado: true });
    expect(authDe(0)).toBe('Bearer access-1');
  });

  it('TOKEN_EXPIRED: renova UMA vez e repete a requisição com o token novo', async () => {
    const p = provedor();
    fetchMock.mockResolvedValueOnce(erro(401, 'TOKEN_EXPIRED')).mockResolvedValueOnce(resposta(200, { data: 'ok' }));
    expect(await api('/me', { autenticado: true })).toEqual({ data: 'ok' });
    expect(p.renovar).toHaveBeenCalledTimes(1);
    expect(authDe(0)).toBe('Bearer access-1');
    expect(authDe(1)).toBe('Bearer access-2');
    expect(p.aoPerderSessao).not.toHaveBeenCalled();
  });

  it('se depois de renovar continuar 401, a sessão é encerrada (sem laço infinito)', async () => {
    const p = provedor();
    fetchMock.mockResolvedValue(erro(401, 'TOKEN_EXPIRED'));
    await expect(api('/me', { autenticado: true })).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(2); // original + uma repetição
    expect(p.renovar).toHaveBeenCalledTimes(1);
    expect(p.aoPerderSessao).toHaveBeenCalledTimes(1);
  });

  it.each(['INVALID_TOKEN', 'UNAUTHENTICATED'])('%s: encerra a sessão sem tentar renovar', async (code) => {
    const p = provedor();
    fetchMock.mockResolvedValue(erro(401, code));
    await expect(api('/me', { autenticado: true })).rejects.toMatchObject({ code });
    expect(p.renovar).not.toHaveBeenCalled();
    expect(p.aoPerderSessao).toHaveBeenCalledTimes(1);
  });

  it('erros que não são 401 (ex.: 404, 422) não mexem na sessão', async () => {
    const p = provedor();
    fetchMock.mockResolvedValue(erro(404, 'RESOURCE_NOT_FOUND'));
    await expect(api('/favoritos/curso/9', { autenticado: true })).rejects.toMatchObject({ status: 404 });
    expect(p.renovar).not.toHaveBeenCalled();
    expect(p.aoPerderSessao).not.toHaveBeenCalled();
  });

  it('falha de rede durante a renovação propaga o erro (e não finge sessão perdida)', async () => {
    const p = provedor({
      renovar: jest.fn(async () => {
        throw new ApiError(0, 'NETWORK_ERROR', 'Sem rede.');
      }),
    });
    fetchMock.mockResolvedValue(erro(401, 'TOKEN_EXPIRED'));
    await expect(api('/me', { autenticado: true })).rejects.toMatchObject({ status: 0 });
    expect(p.aoPerderSessao).not.toHaveBeenCalled();
  });
});
