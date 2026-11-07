// Integração REAL: cliente TypeScript do app contra o backend Flask rodando.
// Desligado por padrão. Para rodar:
//   1) suba o Flask (ex.: porta 5060, banco de teste)
//   2) INTEGRACAO=1 EXPO_PUBLIC_API_URL=http://127.0.0.1:5060 npm test -- integracao
import http from 'http';

import * as authApi from '../src/api/auth';
import * as catalogoApi from '../src/api/catalogo';
import * as favoritosApi from '../src/api/favoritos';
import * as adminApi from '../src/api/admin';
import * as perfilApi from '../src/api/perfil';
import * as testeApi from '../src/api/testeVocacional';
import { api, ApiError, configurarProvedorDeSessao } from '../src/api/client';
import type { Paginated } from '../src/api/tipos';
import { GerenciadorDeSessao } from '../src/auth/gerenciadorDeSessao';
import type { TokenStorage } from '../src/auth/tokenStorage';

const describeIntegracao = process.env.INTEGRACAO === '1' ? describe : describe.skip;

// O fetch do ambiente Jest do Expo é um substituto sem rede: aqui usamos um fetch
// mínimo sobre o módulo http do Node para falar com o backend de verdade.
function fetchReal(url: string, init: { method?: string; headers?: Record<string, string>; body?: string } = {}) {
  return new Promise<Response>((resolve, reject) => {
    const req = http.request(url, { method: init.method ?? 'GET', headers: init.headers }, (res) => {
      const partes: Buffer[] = [];
      res.on('data', (d) => partes.push(d));
      res.on('end', () => {
        const texto = Buffer.concat(partes).toString('utf-8');
        const status = res.statusCode ?? 0;
        resolve({
          ok: status >= 200 && status < 300,
          status,
          json: async () => JSON.parse(texto),
          text: async () => texto,
        } as unknown as Response);
      });
    });
    req.on('error', reject);
    if (init.body) req.write(init.body);
    req.end();
  });
}

beforeAll(() => {
  if (process.env.INTEGRACAO === '1') global.fetch = fetchReal as unknown as typeof fetch;
});

function novoGerenciador(armazenamentoInicial: string | null = null) {
  let guardado: string | null = armazenamentoInicial;
  const storage: TokenStorage = {
    ler: async () => guardado,
    gravar: async (t) => {
      guardado = t;
    },
    apagar: async () => {
      guardado = null;
    },
  };
  const aoEncerrar = jest.fn();
  const g = new GerenciadorDeSessao({
    storage,
    renovarNoServidor: async (r) => (await authApi.renovar(r)).data.tokens,
    aoEncerrar,
  });
  configurarProvedorDeSessao(g);
  return { g, aoEncerrar, guardado: () => guardado };
}

const sufixo = Date.now().toString(36);
const credenciais = (n: string) => ({
  nome: `app_${n}_${sufixo}`,
  email: `app_${n}_${sufixo}@teste.com`,
  senha: 'segredo123',
});

describeIntegracao('app ↔ backend (API real)', () => {
  it('catálogo público: GET /cursos devolve {data, meta}', async () => {
    const pagina = await api<Paginated<{ id: number; nome: string }>>('/cursos?limit=2');
    expect(pagina.data.length).toBeGreaterThan(0);
    expect(pagina.meta).toMatchObject({ page: 1, limit: 2 });
  });

  it('cadastro → perfil autenticado → login', async () => {
    const { g } = novoGerenciador();
    const c = credenciais('fluxo');
    const { data } = await authApi.cadastrar(c.nome, c.email, c.senha);
    expect(data.tokens).toMatchObject({ token_type: 'Bearer', expires_in: 900 });
    expect(data.usuario).toMatchObject({ nome_usuario: c.nome, email: c.email, tipo: 'aluno' });
    await g.definir(data.tokens);

    expect((await authApi.meuPerfil()).data.email).toBe(c.email); // Bearer enviado pelo cliente

    const login = await authApi.entrar(c.email, c.senha);
    expect(login.data.usuario.id).toBe(data.usuario.id);
  });

  it('erros do backend chegam como ApiError com código e mensagem', async () => {
    const c = credenciais('erros');
    await authApi.cadastrar(c.nome, c.email, c.senha);
    await expect(authApi.cadastrar(c.nome, c.email, c.senha)).rejects.toMatchObject({
      status: 409,
      code: 'CONFLICT',
    });
    await expect(authApi.cadastrar('x', 'y@z.com', '123')).rejects.toMatchObject({ status: 422, code: 'VALIDATION_ERROR' });
    const e = await authApi.entrar(c.email, 'errada123').catch((x) => x);
    expect(e).toBeInstanceOf(ApiError);
    expect(e).toMatchObject({ status: 401, code: 'INVALID_CREDENTIALS' });
    expect(e.requestId).toBeTruthy();
  });

  it('rotação: cada renovação troca o refresh token; o antigo reapresentado derruba a sessão', async () => {
    const { g, aoEncerrar } = novoGerenciador();
    const c = credenciais('rotacao');
    const { data } = await authApi.cadastrar(c.nome, c.email, c.senha);
    await g.definir(data.tokens);
    const refresh1 = data.tokens.refresh_token;

    await g.renovar(); // (o access token pode coincidir se emitido no mesmo segundo; o refresh nunca)
    expect(g.obterRefreshToken()).not.toBe(refresh1);

    // Alguém reapresenta o refresh antigo (já usado): o servidor trata como roubo.
    await expect(authApi.renovar(refresh1)).rejects.toMatchObject({ status: 401, code: 'REFRESH_TOKEN_REUSED' });

    // A família inteira foi revogada: até o token "legítimo" mais novo deixa de valer,
    // e o cliente encerra a sessão local ao perceber.
    await expect(authApi.meuPerfil()).rejects.toMatchObject({ status: 401, code: 'INVALID_TOKEN' });
    expect(aoEncerrar).toHaveBeenCalled();
    expect(g.obterAccessToken()).toBeNull();
  });

  it('cinco renovações simultâneas viram UMA no servidor (single-flight) e a sessão segue válida', async () => {
    const { g, aoEncerrar } = novoGerenciador();
    const c = credenciais('paralelo');
    const { data } = await authApi.cadastrar(c.nome, c.email, c.senha);
    await g.definir(data.tokens);

    const resultados = await Promise.all([1, 2, 3, 4, 5].map(() => g.renovar()));
    expect(new Set(resultados).size).toBe(1);
    expect(aoEncerrar).not.toHaveBeenCalled();
    expect((await authApi.meuPerfil()).data.email).toBe(c.email); // sem derrubar a sessão
  });

  it('logout revoga a sessão no servidor', async () => {
    const { g } = novoGerenciador();
    const c = credenciais('logout');
    const { data } = await authApi.cadastrar(c.nome, c.email, c.senha);
    await g.definir(data.tokens);

    await authApi.sair(data.tokens.refresh_token);
    await expect(authApi.renovar(data.tokens.refresh_token)).rejects.toMatchObject({ code: 'INVALID_REFRESH_TOKEN' });
    await expect(authApi.meuPerfil()).rejects.toMatchObject({ code: 'INVALID_TOKEN' });
  });

  it('restaurar a sessão ao abrir o app (refresh guardado → novo par)', async () => {
    const c = credenciais('restaurar');
    const { data } = await authApi.cadastrar(c.nome, c.email, c.senha);
    const antes = novoGerenciador();
    await antes.g.definir(data.tokens); // grava o refresh token no "armazenamento do aparelho"

    // Fecha e reabre o app: memória vazia, mas o armazenamento seguro continua com o refresh token.
    const reaberto = novoGerenciador(antes.guardado());
    expect(reaberto.g.obterAccessToken()).toBeNull();
    expect(await reaberto.g.restaurar()).toBe(true);
    expect((await authApi.meuPerfil()).data.email).toBe(c.email);
    expect(reaberto.guardado()).not.toBe(data.tokens.refresh_token); // o refresh guardado foi rotacionado
  });

  // ── Etapa B: as funções que as telas do catálogo chamam ─────────────────────

  it('catálogo: filtros dos cursos e das faculdades chegam ao backend como o site envia', async () => {
    const todos = await catalogoApi.listarCursos({}, 1, 50);
    const exemplo = todos.data[0];
    const porArea = await catalogoApi.listarCursos({ area: exemplo.area ?? undefined }, 1, 50);
    expect(porArea.data.length).toBeGreaterThan(0);
    expect(porArea.data.every((c) => c.area === exemplo.area)).toBe(true);

    const presenciais = await catalogoApi.listarCursos({ modalidade: ['presencial', 'ead'] }, 1, 50);
    expect(presenciais.data.every((c) => ['presencial', 'ead'].includes(c.modalidade ?? ''))).toBe(true);

    const publicas = await catalogoApi.listarFaculdades({ tipo_instituicao: 'Pública' }, 1, 5);
    expect(publicas.data.every((f) => f.tipo_instituicao === 'Pública')).toBe(true);
    expect(publicas.meta.total).toBeLessThan((await catalogoApi.listarFaculdades({}, 1, 1)).meta.total);

    const sp = await catalogoApi.listarFaculdades({ cidade: 'SP' }, 1, 5); // UF pelo filtro "cidade"
    expect(sp.data.every((f) => f.uf === 'SP')).toBe(true);
  });

  it('busca e detalhes: sugestões levam a ids e nomes que existem', async () => {
    const { data } = await catalogoApi.sugestoes('sao');
    expect(Object.keys(data).sort()).toEqual(['curso', 'faculdade', 'local']);
    const sugerida = data.faculdade[0];
    expect(sugerida.id).toBeTruthy();
    const detalhe = (await catalogoApi.obterFaculdade(sugerida.id!)).data;
    expect(detalhe.nome).toBe(sugerida.rotulo);
    expect(Array.isArray(detalhe.cursos)).toBe(true);

    const curso = (await catalogoApi.listarCursos({}, 1, 1)).data[0];
    expect((await catalogoApi.obterCurso(curso.id)).data.nome).toBe(curso.nome);
    await expect(catalogoApi.obterCurso(999999)).rejects.toMatchObject({ status: 404 });
  });

  it('favoritos: salvar, listar com resumo e remover (com o Bearer da sessão)', async () => {
    const { g } = novoGerenciador();
    const c = credenciais('favoritos');
    const { data } = await authApi.cadastrar(c.nome, c.email, c.senha);
    await g.definir(data.tokens);
    const curso = (await catalogoApi.listarCursos({}, 1, 1)).data[0];

    const salvo = await favoritosApi.favoritar('curso', curso.id);
    expect(salvo.data).toMatchObject({ tipo: 'curso', item_id: curso.id, nome_item: curso.nome });
    await favoritosApi.favoritar('curso', curso.id); // idempotente: não duplica
    const lista = (await favoritosApi.listarFavoritos()).data;
    expect(lista.filter((f) => f.item_id === curso.id)).toHaveLength(1);
    expect(lista[0].item).toMatchObject({ id: curso.id, nome: curso.nome });

    await favoritosApi.desfavoritar('curso', curso.id);
    expect((await favoritosApi.listarFavoritos()).data).toHaveLength(0);
    await expect(favoritosApi.favoritar('curso', 999999)).rejects.toMatchObject({ status: 404 });
  });

  // ── Fase de paridade com o site ─────────────────────────────────────────────

  it('vestibulares: catálogo novo (taxa/cursos/requisitos), várias regiões e privadas', async () => {
    const todos = await catalogoApi.listarVestibulares({}, 1, 100);
    expect(todos.meta.total).toBeGreaterThanOrEqual(40);
    expect(todos.data.some((v) => v.taxa_inscricao || v.cursos_oferecidos)).toBe(true);
    const publicas = await catalogoApi.listarVestibulares({ instituicao: 'Pública' }, 1, 100);
    expect(publicas.data.every((v) => v.tipo_instituicao === 'Pública')).toBe(true);
    const duas = await catalogoApi.listarVestibulares({ regiao: ['Sudeste', 'Sul'] }, 1, 100);
    expect(duas.data.every((v) => ['Sudeste', 'Sul'].includes(v.regiao ?? ''))).toBe(true);
    const um = (await catalogoApi.obterVestibular(todos.data[0].id)).data;
    expect(um.nome).toBe(todos.data[0].nome);
  });

  it('teste vocacional: perguntas → respostas → recomendações com compatibilidade', async () => {
    const { g } = novoGerenciador();
    const c = credenciais('teste');
    await g.definir((await authApi.cadastrar(c.nome, c.email, c.senha)).data.tokens);
    const q = (await testeApi.perguntas()).data;
    const respostas = Object.fromEntries(q.secoes.flatMap((s) => s.perguntas).map((p) => [p.id, p.opcoes[0].id]));
    const res = (await testeApi.enviarRespostas(respostas)).data;
    expect(res.resultado_id).toBeTruthy();
    const rec = (await testeApi.recomendacoes(res.resultado_id!, 5)).data;
    expect(rec.resultado_id).toBe(res.resultado_id);
    expect(rec.cursos.length).toBeGreaterThan(0);
    expect(rec.cursos[0].compatibilidade).toBeGreaterThan(0);
    expect((await testeApi.historico()).data[0].id).toBe(res.resultado_id);
  });

  it('perfil: painel, editar nome e trocar senha (a sessão continua)', async () => {
    const { g } = novoGerenciador();
    const c = credenciais('perfil');
    await g.definir((await authApi.cadastrar(c.nome, c.email, c.senha)).data.tokens);
    expect((await perfilApi.meuPainel()).data.contagem_favoritos).toEqual({ cursos: 0, faculdades: 0, vestibulares: 0 });
    const novo = `${c.nome}_x`;
    expect((await perfilApi.atualizarPerfil({ nome_usuario: novo, email: c.email })).data.nome_usuario).toBe(novo);
    await perfilApi.alterarSenha('novaSenha123', 'novaSenha123');
    expect((await authApi.meuPerfil()).data.nome_usuario).toBe(novo);
    expect((await authApi.entrar(c.email, 'novaSenha123')).data.usuario.id).toBeTruthy();
  });

  it('admin: aluno recebe 403; admin vê as estatísticas e cria/exclui usuário', async () => {
    const aluno = novoGerenciador();
    const c = credenciais('nao_admin');
    await aluno.g.definir((await authApi.cadastrar(c.nome, c.email, c.senha)).data.tokens);
    await expect(adminApi.estatisticas()).rejects.toMatchObject({ status: 403, code: 'FORBIDDEN' });

    const email = process.env.INTEGRACAO_ADMIN_EMAIL;
    const senha = process.env.INTEGRACAO_ADMIN_SENHA;
    if (!email || !senha) return; // servidor de teste sem admin conhecido
    const adm = novoGerenciador();
    await adm.g.definir((await authApi.entrar(email, senha)).data.tokens);
    expect((await adminApi.estatisticas()).data.stats.total_vestibulares).toBeGreaterThanOrEqual(40);
    const u = credenciais('criado_pelo_admin');
    const criado = (await adminApi.criarUsuario({ nome_usuario: u.nome, email: u.email, password: u.senha, tipo: 'aluno' })).data;
    expect(criado.tipo).toBe('aluno');
    await adminApi.excluirUsuario(criado.id);
    expect((await adminApi.listarUsuarios()).data.some((x) => x.id === criado.id)).toBe(false);
  });

  it('google: sem client IDs no servidor, responde GOOGLE_NOT_CONFIGURED (nunca autentica)', async () => {
    const e = await authApi.entrarComGoogle('a.b.c').catch((x) => x);
    expect(e).toBeInstanceOf(ApiError);
    expect([401, 503]).toContain(e.status); // 503 sem client IDs; 401 se configurado (token falso)
  });
});
