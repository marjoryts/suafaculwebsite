// Painel administrativo no app: visível só para admin (o servidor também barra) e com
// as mesmas operações do painel do site.
import { userEvent } from '@testing-library/react-native';
import { screen, waitFor } from 'expo-router/testing-library';
import { Alert } from 'react-native';

import { ApiError } from '../src/api/client';
import { abrirApp, auth, comSessaoGuardada, usuarioAna } from '../test-utils/app';
import { adminApi, catalogo, faculdade, pagina, prepararApiSimulada } from '../test-utils/apiSimulada';

jest.mock('../src/api/auth');
jest.mock('../src/api/catalogo');
jest.mock('../src/api/favoritos');
jest.mock('../src/api/testeVocacional');
jest.mock('../src/api/perfil');
jest.mock('../src/api/admin');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const SecureStore = require('expo-secure-store');

const STATS = {
  total_usuarios: 3, total_admins: 1, novos_usuarios_30d: 2, total_faculdades: 2957, faculdades_importadas_emec: 2900,
  total_cursos: 11, faculdades_com_cursos: 8, total_vestibulares: 40, vestibulares_ativos: 30, vestibulares_sem_faculdade: 5,
  total_alunos: 2, total_favoritos: 16, total_testes_vocacionais: 4, vestibulares_encerrados: 10,
};

async function comoAdmin() {
  await comSessaoGuardada();
  auth.meuPerfil.mockResolvedValue({ data: { ...usuarioAna, tipo: 'admin' } });
}

/** Responde "sim" no próximo Alert de confirmação (botão destrutivo). */
function confirmarProximoAlerta() {
  return jest.spyOn(Alert, 'alert').mockImplementationOnce((_t, _m, botoes) => {
    botoes?.find((b) => b.style === 'destructive')?.onPress?.();
  });
}

beforeEach(async () => {
  SecureStore.__limpar();
  prepararApiSimulada();
  adminApi.estatisticas.mockResolvedValue({ data: { stats: STATS, automacoes: [] } });
  adminApi.listarUsuarios.mockResolvedValue({
    data: [
      { id: 1, nome_usuario: 'ana', email: 'ana@x.com', tipo: 'admin' },
      { id: 2, nome_usuario: 'beto', email: 'beto@x.com', tipo: 'aluno' },
    ],
  });
});

describe('permissões no app', () => {
  it('aluno não vê o painel e, se abrir o endereço, vê "Acesso restrito" sem chamar a API', async () => {
    await comSessaoGuardada();
    await abrirApp('/perfil');
    expect(await screen.findByText('Configurações')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Painel administrativo' })).toBeNull();

    await abrirApp('/admin');
    expect(await screen.findByText('Acesso restrito')).toBeTruthy();
    expect(adminApi.estatisticas).not.toHaveBeenCalled();
  });

  it('admin vê o painel com os indicadores do site', async () => {
    await comoAdmin();
    const { vista } = await abrirApp('/perfil');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Painel administrativo' }));
    await waitFor(() => expect(vista).toHavePathname('/admin'));
    expect(await screen.findByLabelText('3 Usuários, 1 admin(s) · 2 novos em 30 dias')).toBeTruthy();
    expect(screen.getByLabelText('2957 Faculdades, 2900 importadas do e-MEC')).toBeTruthy();
    expect(screen.getByLabelText('40 Vestibulares, 30 ativos · 5 sem faculdade')).toBeTruthy();
    expect(screen.getByLabelText('16 Favoritos salvos, Cursos, faculdades e vestibulares')).toBeTruthy();
  });

  it('se o servidor recusar (403), o erro aparece', async () => {
    await comoAdmin();
    adminApi.estatisticas.mockRejectedValue(new ApiError(403, 'FORBIDDEN', 'Acesso restrito a administradores.'));
    await abrirApp('/admin');
    expect(await screen.findByText('Acesso restrito a administradores.')).toBeTruthy();
  });
});

describe('usuários', () => {
  it('busca local e criação de admin', async () => {
    await comoAdmin();
    adminApi.criarUsuario.mockResolvedValue({ data: { id: 3, nome_usuario: 'caio', email: 'caio@x.com', tipo: 'admin' } });
    const { vista } = await abrirApp('/admin/usuarios');
    const user = userEvent.setup();
    expect(await screen.findByText('beto')).toBeTruthy();
    await user.type(screen.getByLabelText('Buscar por nome ou e-mail...'), 'BÉTO');
    expect(screen.queryByText('ana')).toBeNull();

    await user.press(screen.getByRole('button', { name: 'Adicionar usuário' }));
    await waitFor(() => expect(vista).toHavePathname('/admin/usuario'));
    await user.type(await screen.findByLabelText('Nome de usuário'), 'caio');
    await user.type(screen.getByLabelText('E-mail'), 'caio@x.com');
    await user.type(screen.getByLabelText('Senha'), 'segredo1');
    await user.press(screen.getByRole('button', { name: 'Administrador' }));
    await user.press(screen.getByRole('button', { name: 'Criar usuário' }));
    expect(adminApi.criarUsuario).toHaveBeenCalledWith({ nome_usuario: 'caio', email: 'caio@x.com', tipo: 'admin', password: 'segredo1' });
    await waitFor(() => expect(vista).toHavePathname('/admin/usuarios'));
  });

  it('editar mostra a regra do servidor e excluir pede confirmação', async () => {
    await comoAdmin();
    adminApi.atualizarUsuario.mockRejectedValue(new ApiError(403, 'FORBIDDEN', 'Você não pode remover seu próprio acesso de admin.'));
    adminApi.excluirUsuario.mockResolvedValue(undefined);
    const { vista } = await abrirApp('/admin/usuarios');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'beto, beto@x.com · Aluno' }));
    await waitFor(() => expect(vista).toHavePathname('/admin/usuario'));
    expect(screen.getByLabelText('Nome de usuário').props.value).toBe('beto');

    await user.press(screen.getByRole('button', { name: 'Salvar alterações' }));
    expect(await screen.findByText('Você não pode remover seu próprio acesso de admin.')).toBeTruthy();
    expect(adminApi.atualizarUsuario).toHaveBeenCalledWith(2, { nome_usuario: 'beto', email: 'beto@x.com', tipo: 'aluno' }); // sem senha = mantém

    const alerta = confirmarProximoAlerta();
    await user.press(screen.getByRole('button', { name: 'Excluir usuário' }));
    expect(alerta).toHaveBeenCalled();
    await waitFor(() => expect(adminApi.excluirUsuario).toHaveBeenCalledWith(2));
    alerta.mockRestore();
  });
});

describe('faculdades', () => {
  it('importar por UF pede confirmação e mostra o resumo do servidor', async () => {
    await comoAdmin();
    adminApi.importarFaculdades.mockResolvedValue({ data: { success: true, total_encontradas: 600, total_criadas: 12, total_atualizadas: 588 } });
    await abrirApp('/admin/faculdades');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'SP' }));
    const alerta = confirmarProximoAlerta();
    await user.press(screen.getByRole('button', { name: 'Importar SP' }));
    expect(alerta).toHaveBeenCalled();
    expect(adminApi.importarFaculdades).toHaveBeenCalledWith({ uf: 'SP' });
    expect(await screen.findByText('600 encontradas · 12 criadas · 588 atualizadas')).toBeTruthy();
    alerta.mockRestore();
  });

  it('importar por códigos manda a lista', async () => {
    await comoAdmin();
    adminApi.importarFaculdades.mockResolvedValue({ data: { success: true, message: '2 faculdades importadas.' } });
    await abrirApp('/admin/faculdades');
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('Códigos e-MEC (separe por vírgula)'), '339, 55');
    await user.press(screen.getByRole('button', { name: 'Importar códigos' }));
    expect(adminApi.importarFaculdades).toHaveBeenCalledWith({ codigos: ['339', '55'] });
    expect(await screen.findByText('2 faculdades importadas.')).toBeTruthy();
  });

  it('editar carrega os dados atuais (sem o texto "null") e salva', async () => {
    await comoAdmin();
    catalogo.obterFaculdade.mockResolvedValue({
      data: { ...faculdade(7, { nome: 'Academia X', sigla: 'AX', cidade: 'null', tipo_instituicao: 'Privada' }), cursos: [], vestibulares: [] },
    });
    adminApi.atualizarFaculdade.mockResolvedValue({ data: faculdade(7) });
    catalogo.listarFaculdades.mockResolvedValue(pagina([faculdade(7, { nome: 'Academia X' })]));
    const { vista } = await abrirApp('/admin/faculdades');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: /^Academia X/ }));
    await waitFor(() => expect(vista).toHavePathname('/admin/faculdade'));
    expect((await screen.findByLabelText('Nome *')).props.value).toBe('Academia X');
    expect(screen.getByLabelText('Cidade').props.value).toBe('');
    await user.press(screen.getByRole('button', { name: 'Salvar alterações' }));
    expect(adminApi.atualizarFaculdade).toHaveBeenCalledWith(7, expect.objectContaining({ nome: 'Academia X', sigla: 'AX', tipo_instituicao: 'Privada' }));
  });
});

describe('cursos e vestibulares', () => {
  it('cadastrar curso vinculado a uma faculdade buscada', async () => {
    await comoAdmin();
    catalogo.listarFaculdades.mockResolvedValue(pagina([faculdade(7, { nome: 'UNICAMP', tipo_instituicao: 'Pública' })]));
    adminApi.criarCurso.mockResolvedValue({ data: {} as never });
    await abrirApp('/admin/curso');
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('Busque a faculdade...'), 'unic');
    await user.press(await screen.findByRole('button', { name: /^UNICAMP/ }));
    await user.type(screen.getByLabelText('Nome do curso *'), 'Física');
    await user.press(screen.getByRole('button', { name: 'Saúde' }));
    await user.press(screen.getByRole('button', { name: 'Cadastrar curso' }));
    expect(adminApi.criarCurso).toHaveBeenCalledWith(
      expect.objectContaining({ nome: 'Física', instituicao: 'UNICAMP', area: 'Saúde', faculdade_id: 7, tipo_instituicao: 'Pública' }),
    );
  });

  it('validação: pré-visualizar não grava; aplicar pede confirmação', async () => {
    await comoAdmin();
    const relatorio = (aplicado: boolean) => ({
      data: {
        resumo: { total: 40, ativos: 30, encerrados: 10, data_invalida: 0, sem_faculdade_cadastrada: 5, falhas: 0, aplicado },
        itens: [{ vestibular_id: 1, nome: 'Enem', status_validacao: 'encerrado', cadastrado_ok: false, faculdade_nome: null }],
      },
    });
    adminApi.validarVestibulares.mockImplementation(async (aplicar) => relatorio(aplicar));
    await abrirApp('/admin/vestibulares');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Pré-visualizar' }));
    expect(adminApi.validarVestibulares).toHaveBeenLastCalledWith(false);
    expect(await screen.findByText('Pré-visualização (nada foi gravado)')).toBeTruthy();
    expect(screen.getByText(/Enem: Prova realizada · faculdade não cadastrada/)).toBeTruthy();

    const alerta = confirmarProximoAlerta();
    await user.press(screen.getByRole('button', { name: 'Validar e aplicar' }));
    expect(adminApi.validarVestibulares).toHaveBeenLastCalledWith(true);
    expect(await screen.findByText('Validação aplicada')).toBeTruthy();
    alerta.mockRestore();
  });

  it('cadastrar vestibular com os campos novos do site', async () => {
    await comoAdmin();
    adminApi.criarVestibular.mockRejectedValue(new ApiError(409, 'CONFLICT', 'Já existe um vestibular cadastrado com esse nome.'));
    await abrirApp('/admin/vestibular');
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('Nome do vestibular *'), 'Fuvest');
    await user.type(screen.getByLabelText('Instituição *'), 'USP');
    await user.type(screen.getByLabelText('Taxa de inscrição'), 'R$ 191');
    await user.press(screen.getByRole('button', { name: 'Cadastrar vestibular' }));
    expect(adminApi.criarVestibular).toHaveBeenCalledWith(expect.objectContaining({ nome: 'Fuvest', instituicao: 'USP', taxa_inscricao: 'R$ 191', regiao: 'Sudeste' }));
    expect(await screen.findByText('Já existe um vestibular cadastrado com esse nome.')).toBeTruthy();
  });
});
