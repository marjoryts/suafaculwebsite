// Endereço da API: variável definida > IP do computador do Expo (dev) > localhost.

function carregarConfig({ env, hostUri }: { env?: string; hostUri?: string }) {
  let config: typeof import('../src/config') | undefined;
  jest.isolateModules(() => {
    if (env === undefined) delete process.env.EXPO_PUBLIC_API_URL;
    else process.env.EXPO_PUBLIC_API_URL = env;
    jest.doMock('expo-constants', () => ({ __esModule: true, default: { expoConfig: { hostUri } } }));
    config = require('../src/config');
  });
  return config!;
}

const original = process.env.EXPO_PUBLIC_API_URL;
afterAll(() => {
  if (original === undefined) delete process.env.EXPO_PUBLIC_API_URL;
  else process.env.EXPO_PUBLIC_API_URL = original;
});

describe('endereço da API', () => {
  it('sem variável, usa o IP do computador que serve o Expo (porta 5000)', () => {
    const c = carregarConfig({ hostUri: '192.168.137.61:8081' });
    expect(c.API_URL).toBe('http://192.168.137.61:5000');
    expect(c.API_V1_URL).toBe('http://192.168.137.61:5000/api/v1');
  });

  it('a variável definida tem prioridade (e perde a barra final)', () => {
    const c = carregarConfig({ env: 'https://api.suafacul.com/', hostUri: '192.168.137.61:8081' });
    expect(c.API_URL).toBe('https://api.suafacul.com');
  });

  it('sem variável nem Expo, cai no localhost', () => {
    expect(carregarConfig({}).API_URL).toBe('http://localhost:5000');
  });
});
