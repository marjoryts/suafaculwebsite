// Etapa C: calendário e lista de vestibulares (mesmos filtros do site) e detalhe.
import { userEvent } from '@testing-library/react-native';
import { screen, waitFor } from 'expo-router/testing-library';

import { chaveDia, dataPorExtenso, diasAte, lerData, resumoProva, rotuloDias, semana } from '../src/catalogo/datas';
import { abrirApp, comSessaoGuardada } from '../test-utils/app';
import { catalogo, pagina, prepararApiSimulada, vestibular } from '../test-utils/apiSimulada';

jest.mock('../src/api/auth');
jest.mock('../src/api/catalogo');
jest.mock('../src/api/favoritos');
jest.mock('../src/api/testeVocacional');
jest.mock('../src/api/perfil');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const SecureStore = require('expo-secure-store');

/** Data ISO daqui a `n` dias (os testes não dependem do dia em que rodam). */
function daquiA(n: number): string {
  const d = new Date();
  return chaveDia(new Date(d.getFullYear(), d.getMonth(), d.getDate() + n));
}

beforeEach(async () => {
  SecureStore.__limpar();
  prepararApiSimulada();
  await comSessaoGuardada();
});

describe('datas das provas', () => {
  const hoje = new Date(2026, 3, 10); // sexta-feira, 10/04/2026

  it('lê ISO como data local e rejeita datas inválidas', () => {
    expect(lerData('2026-04-10')?.getDate()).toBe(10);
    expect(lerData('2026-02-31')).toBeNull();
    expect(lerData('abril')).toBeNull();
    expect(lerData(null)).toBeNull();
  });

  it('conta os dias como o Figma ("68 dias") e marca a prova realizada', () => {
    expect(diasAte('2026-06-17', hoje)).toBe(68);
    expect(rotuloDias('2026-04-10', hoje)).toBe('Hoje');
    expect(rotuloDias('2026-04-11', hoje)).toBe('Amanhã');
    expect(rotuloDias('2026-04-09', hoje)).toBe('Prova realizada');
    expect(rotuloDias(null, hoje)).toBeUndefined();
    expect(resumoProva({ data_prova: '2026-06-17', instituicao: 'USP' }, hoje)).toBe('Prova: 17/06/2026 · 68 dias');
    expect(resumoProva({ data_prova: null, instituicao: 'USP' }, hoje)).toBe('USP · Data a definir');
  });

  it('semana de segunda a domingo e data por extenso', () => {
    expect(semana(hoje).map((d) => d.getDate())).toEqual([6, 7, 8, 9, 10, 11, 12]); // o frame do Figma
    expect(dataPorExtenso(hoje)).toBe('Sexta-feira, 10 de abril de 2026');
  });
});

describe('lista de vestibulares', () => {
  it('mostra os vestibulares com data e dias restantes, e abre o detalhe', async () => {
    catalogo.listarVestibulares.mockResolvedValue(
      pagina([vestibular(3, { nome: 'Fuvest', data_prova: daquiA(30) }), vestibular(4, { nome: 'Enem' })]),
    );
    const { vista } = await abrirApp('/vestibulares');
    const user = userEvent.setup();
    expect(await screen.findByText('Fuvest')).toBeTruthy();
    expect(screen.getByText(/30 dias/)).toBeTruthy();
    expect(screen.getByText('UNICAMP · Data a definir')).toBeTruthy();
    await user.press(screen.getByRole('button', { name: /^Fuvest,/ }));
    await waitFor(() => expect(vista).toHavePathname('/vestibulares/3'));
  });

  it('por padrão inclui públicas e privadas, como o site ("Todas as Instituições")', async () => {
    await abrirApp('/vestibulares');
    await screen.findByText('Vestibular 3');
    expect(catalogo.listarVestibulares).toHaveBeenCalledWith(expect.objectContaining({ instituicao: 'Todas' }), 1);
  });

  it('filtros de instituição, várias regiões e meses', async () => {
    await abrirApp('/vestibulares');
    const user = userEvent.setup();
    await screen.findByText('Vestibular 3');
    await user.press(screen.getByRole('button', { name: 'Privadas' }));
    await user.press(screen.getByRole('button', { name: 'Sul' }));
    await user.press(screen.getByRole('button', { name: 'Nordeste' }));
    await user.press(screen.getByRole('button', { name: 'Dezembro' }));
    await waitFor(() =>
      expect(catalogo.listarVestibulares).toHaveBeenLastCalledWith(
        expect.objectContaining({ instituicao: 'Privada', regiao: ['Sul', 'Nordeste'], mes: [12] }),
        1,
      ),
    );
  });

  it('o filtro de curso usa os cursos reais do banco', async () => {
    await abrirApp('/vestibulares');
    const user = userEvent.setup();
    await screen.findByText('Vestibular 3');
    await user.press(await screen.findByRole('button', { name: 'Curso 1' }));
    await waitFor(() =>
      expect(catalogo.listarVestibulares).toHaveBeenLastCalledWith(expect.objectContaining({ curso: 'Curso 1' }), 1),
    );
  });

  it('o calendário marca os dias com prova e mostra as provas do dia escolhido', async () => {
    const hoje = new Date();
    catalogo.listarVestibulares.mockResolvedValue(pagina([vestibular(5, { nome: 'Prova de hoje', data_prova: chaveDia(hoje) })]));
    await abrirApp('/vestibulares');
    const user = userEvent.setup();
    const dia = await screen.findByRole('button', { name: new RegExp(`^\\w+ ${hoje.getDate()}, tem prova, hoje$`) });
    await user.press(dia);
    expect(dia).toBeSelected();
    expect(screen.getAllByText('Prova de hoje').length).toBe(2); // no dia e na lista
  });
});

describe('detalhe do vestibular', () => {
  it('mostra todos os campos do card do site e a contagem até a prova', async () => {
    catalogo.obterVestibular.mockResolvedValue({
      data: vestibular(3, {
        nome: 'Fuvest',
        data_prova: daquiA(10),
        taxa_inscricao: 'R$ 191,00',
        cursos_oferecidos: 'Medicina (175 vagas)',
        requisitos: 'Ensino médio completo',
        link_edital: 'https://fuvest.br',
      }),
    });
    const { vista } = await abrirApp('/vestibulares/3');
    const user = userEvent.setup();
    expect(await screen.findByText('Fuvest')).toBeTruthy();
    expect(screen.getByText('10 dias')).toBeTruthy();
    expect(screen.getByText('Taxa: R$ 191,00')).toBeTruthy();
    expect(screen.getByText('Medicina (175 vagas)')).toBeTruthy();
    expect(screen.getByText('Ensino médio completo')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Ver edital' })).toBeTruthy();
    await user.press(screen.getByRole('link', { name: 'Ver a faculdade UNICAMP' }));
    await waitFor(() => expect(vista).toHavePathname('/faculdades/7'));
  });

  it('prova que já passou aparece como realizada', async () => {
    catalogo.obterVestibular.mockResolvedValue({ data: vestibular(3, { data_prova: daquiA(-5) }) });
    await abrirApp('/vestibulares/3');
    expect(await screen.findByText('Prova realizada')).toBeTruthy();
  });
});
