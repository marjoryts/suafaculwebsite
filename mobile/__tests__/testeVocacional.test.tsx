// Etapa D: teste vocacional (introdução → perguntas → resultado → cursos recomendados).
import { userEvent } from '@testing-library/react-native';
import { screen, waitFor } from 'expo-router/testing-library';

import { ApiError } from '../src/api/client';
import type { Recomendacoes } from '../src/api/tipos';
import { abrirApp, comSessaoGuardada } from '../test-utils/app';
import { prepararApiSimulada, testeApi } from '../test-utils/apiSimulada';

jest.mock('../src/api/auth');
jest.mock('../src/api/catalogo');
jest.mock('../src/api/favoritos');
jest.mock('../src/api/testeVocacional');
jest.mock('../src/api/perfil');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const SecureStore = require('expo-secure-store');

const RECOMENDACOES: Recomendacoes = {
  resultado_id: 9,
  perfil: 'tecnico',
  perfil_nome: 'Perfil Técnico / Exato',
  perfil_descricao: 'Você gosta de lógica e tecnologia.',
  created_at: null,
  cursos: [
    { id: 1, nome: 'Engenharia de Software', area: 'Tecnologia', grau: 'Bacharelado', descricao: null, compatibilidade: 92, perfis: ['tecnico'], criterio: 'nome', total_instituicoes: 3 },
    { id: 2, nome: 'Direito', area: 'Direito', grau: 'Bacharelado', descricao: null, compatibilidade: 40, perfis: ['humano', 'gestao'], criterio: 'area', total_instituicoes: 1 },
  ],
  total_compativeis: 2,
  sem_dados_suficientes: 1,
  total_cursos_analisados: 3,
};

function comResultado() {
  testeApi.recomendacoes.mockResolvedValue({ data: RECOMENDACOES });
  testeApi.historico.mockResolvedValue({
    data: [
      {
        id: 9,
        perfil: 'tecnico',
        perfil_nome: 'Perfil Técnico / Exato',
        created_at: null,
        pontuacoes: [
          { chave: 'tecnico', nome: 'Perfil Técnico / Exato', percentual: 70 },
          { chave: 'humano', nome: 'Perfil Humano / Social', percentual: 30 },
          { chave: 'pratico', nome: 'Perfil Prático / Operacional', percentual: 0 },
        ],
      },
    ],
  });
}

beforeEach(async () => {
  SecureStore.__limpar();
  prepararApiSimulada();
  await comSessaoGuardada();
});

it('fluxo completo: responde uma pergunta por vez, o servidor calcula e o resultado aparece', async () => {
  testeApi.enviarRespostas.mockImplementation(async () => {
    comResultado();
    return { data: { resultado_id: 9, scores: {}, pontuacoes: [], perfis: [], salvo: true } };
  });
  const { vista } = await abrirApp('/teste-vocacional');
  const user = userEvent.setup();

  await user.press(await screen.findByRole('button', { name: 'Iniciar Teste' }));
  await waitFor(() => expect(vista).toHavePathname('/teste-vocacional/perguntas'));

  expect(await screen.findByText('O que você mais gosta?')).toBeTruthy();
  expect(screen.getByText('Interesses · Pergunta 1 de 2')).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Próxima' })).toBeDisabled(); // sem resposta ainda
  await user.press(screen.getByRole('radio', { name: 'Tecnologia' }));
  expect(screen.getByRole('radio', { name: 'Tecnologia' })).toBeChecked();
  await user.press(screen.getByRole('button', { name: 'Próxima' }));

  expect(await screen.findByText('Em que você é bom?')).toBeTruthy();
  await user.press(screen.getByRole('button', { name: 'Anterior' })); // volta sem perder a resposta
  expect(screen.getByRole('radio', { name: 'Tecnologia' })).toBeChecked();
  await user.press(screen.getByRole('button', { name: 'Próxima' }));
  await user.press(screen.getByRole('radio', { name: 'Escrita' }));
  await user.press(screen.getByRole('button', { name: 'Ver resultado' }));

  expect(testeApi.enviarRespostas).toHaveBeenCalledWith({ q1: 'a', q2: 'b' });
  await waitFor(() => expect(vista).toHavePathname('/teste-vocacional/resultado'));
  expect((await screen.findAllByText('Perfil Técnico / Exato')).length).toBe(2); // destaque + ranking
  expect(screen.getByText('Você gosta de lógica e tecnologia.')).toBeTruthy();
  expect(screen.getByLabelText('1º, Perfil Técnico / Exato, 70%')).toBeTruthy();
  expect(screen.getByLabelText('2º, Perfil Humano / Social, 30%')).toBeTruthy();
  expect(screen.queryByText(/Prático/)).toBeNull(); // perfis com 0% não entram no ranking
  expect(testeApi.recomendacoes).toHaveBeenCalledWith(9, 1);
});

it('cursos recomendados mostram a compatibilidade e abrem o curso', async () => {
  comResultado();
  const { vista } = await abrirApp('/teste-vocacional/resultado?id=9');
  const user = userEvent.setup();
  await user.press(await screen.findByRole('button', { name: 'Ver cursos recomendados' }));
  await waitFor(() => expect(vista).toHavePathname('/teste-vocacional/recomendados'));
  expect(await screen.findByLabelText('92% compatível')).toBeTruthy();
  expect(screen.getByLabelText('40% compatível')).toBeTruthy();
  expect(screen.getByText(/1 curso ficou de fora/)).toBeTruthy();
  expect(testeApi.recomendacoes).toHaveBeenLastCalledWith(9, 50);
  await user.press(screen.getByRole('button', { name: /^Engenharia de Software,/ }));
  await waitFor(() => expect(vista).toHavePathname('/cursos/1'));
});

it('sem teste feito, o resultado convida a começar', async () => {
  const { vista } = await abrirApp('/teste-vocacional/resultado');
  const user = userEvent.setup();
  expect(await screen.findByText('Você ainda não fez o teste')).toBeTruthy();
  await user.press(screen.getByRole('button', { name: 'Iniciar Teste' }));
  await waitFor(() => expect(vista).toHavePathname('/teste-vocacional/perguntas'));
});

it('a introdução oferece rever o último resultado quando existe', async () => {
  comResultado();
  const { vista } = await abrirApp('/teste-vocacional');
  const user = userEvent.setup();
  await user.press(await screen.findByRole('button', { name: 'Ver meu último resultado' }));
  await waitFor(() => expect(vista).toHavePathname('/teste-vocacional/resultado'));
});

it('erro ao enviar mantém as respostas e mostra a mensagem', async () => {
  testeApi.enviarRespostas.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', 'Sem rede.'));
  const { vista } = await abrirApp('/teste-vocacional/perguntas');
  const user = userEvent.setup();
  await user.press(await screen.findByRole('radio', { name: 'Tecnologia' }));
  await user.press(screen.getByRole('button', { name: 'Próxima' }));
  await user.press(await screen.findByRole('radio', { name: 'Cálculo' }));
  await user.press(screen.getByRole('button', { name: 'Ver resultado' }));
  expect(await screen.findByText('Sem rede.')).toBeTruthy();
  expect(vista).toHavePathname('/teste-vocacional/perguntas');
  expect(screen.getByRole('radio', { name: 'Cálculo' })).toBeChecked();
});
