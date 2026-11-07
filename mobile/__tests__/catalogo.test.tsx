// Etapa B: catálogo real (listas, filtros, busca, detalhes, home) e favoritar.
// Renderiza as rotas reais; a API é simulada (test-utils/apiSimulada.ts).
import { userEvent } from '@testing-library/react-native';
import { act, screen, waitFor, within } from 'expo-router/testing-library';
import { Alert } from 'react-native';

import { ApiError } from '../src/api/client';
import { abrirApp, comSessaoGuardada } from '../test-utils/app';
import { catalogo, curso, faculdade, favoritosApi, pagina, prepararApiSimulada } from '../test-utils/apiSimulada';

jest.mock('../src/api/auth');
jest.mock('../src/api/catalogo');
jest.mock('../src/api/favoritos');
jest.mock('../src/api/testeVocacional');
jest.mock('../src/api/perfil');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const SecureStore = require('expo-secure-store');

beforeEach(async () => {
  SecureStore.__limpar();
  prepararApiSimulada();
  await comSessaoGuardada();
});

describe('lista de cursos', () => {
  it('mostra os cursos da API com contagem e abre o detalhe', async () => {
    catalogo.listarCursos.mockResolvedValue(pagina([curso(1, { nome: 'Medicina' }), curso(2)], 2));
    const { vista } = await abrirApp('/cursos');
    const user = userEvent.setup();
    expect(await screen.findByText('Medicina')).toBeTruthy();
    expect(screen.getByText('2 cursos encontrados')).toBeTruthy();
    await user.press(screen.getByRole('button', { name: /^Medicina,/ }));
    await waitFor(() => expect(vista).toHavePathname('/cursos/1'));
  });

  it('filtros de área, modalidade e instituição usam os valores do website', async () => {
    await abrirApp('/cursos');
    const user = userEvent.setup();
    await screen.findByText('Curso 1');
    await user.press(screen.getByRole('button', { name: 'Saúde' }));
    await user.press(screen.getByRole('button', { name: 'EaD' }));
    await user.press(screen.getByRole('button', { name: 'Pública' }));
    await waitFor(() =>
      expect(catalogo.listarCursos).toHaveBeenLastCalledWith(
        { busca: '', area: 'Saúde', modalidade: ['ead'], tipo_instituicao: ['Pública'] },
        1,
      ),
    );
    // Área é escolha única: tocar de novo desmarca.
    await user.press(screen.getByRole('button', { name: 'Saúde' }));
    await waitFor(() =>
      expect(catalogo.listarCursos).toHaveBeenLastCalledWith(expect.objectContaining({ area: undefined }), 1),
    );
  });

  it('a busca por texto espera o usuário parar de digitar (uma consulta, não uma por letra)', async () => {
    await abrirApp('/cursos');
    const user = userEvent.setup();
    await screen.findByText('Curso 1');
    catalogo.listarCursos.mockClear();
    await user.type(screen.getByLabelText('Pesquise cursos...'), 'direito');
    await waitFor(() =>
      expect(catalogo.listarCursos).toHaveBeenCalledWith(expect.objectContaining({ busca: 'direito' }), 1),
    );
    expect(catalogo.listarCursos).toHaveBeenCalledTimes(1);
  });

  it('lista vazia e erro com "Tentar novamente"', async () => {
    // Permanente: abrir /cursos direto também monta a home por baixo (que lista cursos).
    catalogo.listarCursos.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', 'Sem rede.'));
    await abrirApp('/cursos');
    const user = userEvent.setup();
    expect(await screen.findByText('Sem rede.')).toBeTruthy();
    catalogo.listarCursos.mockResolvedValue(pagina([]));
    await user.press(screen.getAllByRole('button', { name: 'Tentar novamente' }).at(-1)!);
    expect(await screen.findByText('Nenhum curso encontrado')).toBeTruthy();
  });
});

describe('lista de faculdades', () => {
  it('filtro de local vindo da busca aparece como chip e pode ser removido', async () => {
    await abrirApp('/faculdades?cidade=Campinas');
    const user = userEvent.setup();
    await screen.findByText('Faculdade 7');
    expect(catalogo.listarFaculdades).toHaveBeenLastCalledWith(expect.objectContaining({ cidade: 'Campinas' }), 1);
    await user.press(screen.getByRole('button', { name: 'Local: Campinas' }));
    await waitFor(() =>
      expect(catalogo.listarFaculdades).toHaveBeenLastCalledWith(expect.objectContaining({ cidade: '' }), 1),
    );
  });

  it('"Híbrido" envia "semipresencial", como o website', async () => {
    await abrirApp('/faculdades');
    const user = userEvent.setup();
    await screen.findByText('Faculdade 7');
    await user.press(screen.getByRole('button', { name: 'Híbrido' }));
    await waitFor(() =>
      expect(catalogo.listarFaculdades).toHaveBeenLastCalledWith(
        expect.objectContaining({ modalidade: ['semipresencial'] }),
        1,
      ),
    );
  });

  it('não mostra cidade/UF gravadas como o texto "null" no banco', async () => {
    catalogo.listarFaculdades.mockResolvedValue(
      pagina([faculdade(9, { nome: 'Academia X', cidade: 'null', uf: 'null', tipo_instituicao: 'Pública' })]),
    );
    await abrirApp('/faculdades');
    expect(await screen.findByText('Academia X')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Academia X, Pública' })).toBeTruthy();
    expect(screen.queryByText(/null/)).toBeNull();
  });
});

describe('busca', () => {
  it('agrupa as sugestões e leva cada tipo ao destino certo', async () => {
    catalogo.sugestoes.mockResolvedValue({
      data: {
        local: [{ tipo: 'local', campo: 'cidade', valor: 'Campinas', rotulo: 'Campinas', detalhe: 'SP · 12 faculdades', subtipo: 'cidade' }],
        faculdade: [{ tipo: 'faculdade', campo: 'faculdade', valor: 'UNICAMP', rotulo: 'UNICAMP', detalhe: 'null/null · Pública', id: 7 }],
        curso: [{ tipo: 'curso', campo: 'curso', valor: 'Medicina', rotulo: 'Medicina', detalhe: 'Saúde · 1 instituição' }],
      },
    });
    const { vista } = await abrirApp('/busca');
    const user = userEvent.setup();
    expect(screen.getByText('O que você procura?')).toBeTruthy();
    await user.type(screen.getByLabelText('Pesquise faculdades, cursos...'), 'cam');
    expect(await screen.findByText('Locais')).toBeTruthy();
    expect(catalogo.sugestoes).toHaveBeenCalledWith('cam');
    expect(screen.getByText('Pública')).toBeTruthy(); // "null/null" removido do detalhe

    await user.press(screen.getByRole('button', { name: /^Campinas,/ }));
    await waitFor(() => expect(vista).toHavePathname('/faculdades'));
    expect(catalogo.listarFaculdades).toHaveBeenLastCalledWith(expect.objectContaining({ cidade: 'Campinas' }), 1);
  });

  it('uma letra só não consulta o servidor', async () => {
    await abrirApp('/busca');
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Pesquise faculdades, cursos...'), 'c');
    await act(async () => {
      jest.advanceTimersByTime(1000); // o renderRouter usa timers falsos
    });
    expect(catalogo.sugestoes).not.toHaveBeenCalled();
  });
});

describe('detalhes', () => {
  it('curso: mostra os dados reais e a instituição leva à faculdade', async () => {
    catalogo.obterCurso.mockResolvedValue({
      data: curso(3, { nome: 'Engenharia de Software', duracao: '4 anos', modalidade: 'ead', faculdade_id: 7 }),
    });
    const { vista } = await abrirApp('/cursos/3');
    const user = userEvent.setup();
    expect(await screen.findByText('Engenharia de Software')).toBeTruthy();
    expect(screen.getByText('Duração: 4 anos')).toBeTruthy();
    expect(screen.getByText('EaD')).toBeTruthy();
    await user.press(screen.getByRole('link', { name: 'Ver a faculdade UNICAMP' }));
    await waitFor(() => expect(vista).toHavePathname('/faculdades/7'));
  });

  it('faculdade: título pela sigla, cursos clicáveis e erro 404 tratado', async () => {
    catalogo.obterFaculdade.mockResolvedValueOnce({
      data: {
        ...faculdade(7, { nome: 'Universidade Estadual de Campinas', sigla: 'UNICAMP' }),
        cursos: [{ id: 3, nome: 'Medicina', modalidade: 'presencial', grau: 'Bacharelado', area: 'Saúde' }],
        vestibulares: [],
      },
    });
    const { vista } = await abrirApp('/faculdades/7');
    const user = userEvent.setup();
    expect(await screen.findByText('UNICAMP')).toBeTruthy();
    expect(screen.getByText('Universidade Estadual de Campinas')).toBeTruthy();
    await user.press(screen.getByRole('button', { name: 'Medicina · Presencial' }));
    await waitFor(() => expect(vista).toHavePathname('/cursos/3'));

    catalogo.obterFaculdade.mockRejectedValueOnce(new ApiError(404, 'NOT_FOUND', 'Faculdade não encontrada.'));
    await abrirApp('/faculdades/999');
    expect(await screen.findByText('Faculdade não encontrada.')).toBeTruthy();
  });
});

describe('favoritar', () => {
  it('o coração salva no servidor e muda de estado', async () => {
    await abrirApp('/cursos');
    const user = userEvent.setup();
    await screen.findByText('Curso 1');
    await user.press(screen.getByRole('button', { name: 'Salvar Curso 1' }));
    expect(favoritosApi.favoritar).toHaveBeenCalledWith('curso', 1);
    expect(await screen.findByRole('button', { name: 'Remover Curso 1 dos salvos' })).toBeSelected();

    await user.press(screen.getByRole('button', { name: 'Remover Curso 1 dos salvos' }));
    expect(favoritosApi.desfavoritar).toHaveBeenCalledWith('curso', 1);
    expect(await screen.findByRole('button', { name: 'Salvar Curso 1' })).toBeTruthy();
  });

  it('se o servidor recusar, desfaz e avisa', async () => {
    const alerta = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    favoritosApi.favoritar.mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', 'Sem rede.'));
    await abrirApp('/cursos');
    const user = userEvent.setup();
    await screen.findByText('Curso 1');
    await user.press(screen.getByRole('button', { name: 'Salvar Curso 1' }));
    await waitFor(() => expect(alerta).toHaveBeenCalledWith('Não foi possível atualizar seus salvos', 'Sem rede.'));
    expect(screen.getByRole('button', { name: 'Salvar Curso 1' })).not.toBeSelected();
    alerta.mockRestore();
  });

  it('favoritar no detalhe reflete na lista (estado compartilhado)', async () => {
    const { vista } = await abrirApp('/cursos');
    const user = userEvent.setup();
    await screen.findByText('Curso 1');
    await user.press(screen.getByRole('button', { name: /^Curso 1,/ }));
    await waitFor(() => expect(vista).toHavePathname('/cursos/1'));
    await user.press(await screen.findByRole('button', { name: 'Salvar Curso 1' }));
    await user.press(screen.getByRole('button', { name: 'Voltar' }));
    await waitFor(() => expect(vista).toHavePathname('/cursos'));
    expect(screen.getByRole('button', { name: 'Remover Curso 1 dos salvos' })).toBeTruthy();
  });
});

describe('home do Explorar', () => {
  it('mostra seções com dados reais e os salvos como atalhos', async () => {
    prepararApiSimulada([{ tipo: 'faculdade', item_id: 7, nome_item: 'UNICAMP', created_at: null }]);
    catalogo.listarFaculdades.mockImplementation(async (f) =>
      pagina([faculdade(f.tipo_instituicao === 'Pública' ? 7 : 8, { sigla: f.tipo_instituicao === 'Pública' ? 'USP' : 'FIAP' })]),
    );
    const { vista } = await abrirApp('/');
    const user = userEvent.setup();
    expect(await screen.findByText('USP')).toBeTruthy();
    expect(screen.getByText('FIAP')).toBeTruthy();
    expect(await screen.findByText('Curso 1')).toBeTruthy();
    expect(catalogo.listarFaculdades).toHaveBeenCalledWith({ tipo_instituicao: 'Pública' }, 1, 8);

    const salvos = screen.getByLabelText('Seus salvos');
    await user.press(within(salvos).getByRole('button', { name: 'UNICAMP' }));
    await waitFor(() => expect(vista).toHavePathname('/faculdades/7'));
  });

  it('erro numa seção não derruba as outras', async () => {
    catalogo.listarCursos.mockRejectedValue(new ApiError(500, 'INTERNAL', 'Erro no servidor.'));
    await abrirApp('/');
    expect(await screen.findByText('Erro no servidor.')).toBeTruthy();
    expect(screen.getAllByText('Faculdade 7').length).toBeGreaterThan(0);
  });
});
