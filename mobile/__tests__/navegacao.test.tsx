// Renderiza as rotas REAIS de src/app com a sessão simulada (a API é mockada).
import { userEvent } from '@testing-library/react-native';
import { router } from 'expo-router';
import { act, screen, waitFor } from 'expo-router/testing-library';
import fs from 'fs';
import path from 'path';

import { ApiError } from '../src/api/client';
import { abrirApp, APP_DIR, auth, CHAVE_REFRESH as CHAVE, comSessaoGuardada, tokens, usuarioAna as usuario } from '../test-utils/app';
import { prepararApiSimulada } from '../test-utils/apiSimulada';

jest.mock('../src/api/auth');
jest.mock('../src/api/catalogo');
jest.mock('../src/api/favoritos');
jest.mock('../src/api/testeVocacional');
jest.mock('../src/api/perfil');
// Só os endpoints de conta são simulados; os utilitários de erro são os reais.
jest.mock('../src/api/conta', () => ({
  ...jest.requireActual('../src/api/conta'),
  enviarCodigoDeVerificacao: jest.fn(),
  confirmarEmail: jest.fn(),
  solicitarRecuperacao: jest.fn(),
  validarCodigoDeRecuperacao: jest.fn(),
  redefinirSenha: jest.fn(),
}));
// eslint-disable-next-line @typescript-eslint/no-require-imports
const conta = require('../src/api/conta') as jest.Mocked<typeof import('../src/api/conta')>;
const funcoesDeConta = () =>
  [
    conta.enviarCodigoDeVerificacao,
    conta.confirmarEmail,
    conta.solicitarRecuperacao,
    conta.validarCodigoDeRecuperacao,
    conta.redefinirSenha,
  ] as jest.Mock[];
const funcoesDaApi = () => Object.values(auth).filter((f) => typeof f === 'function') as jest.Mock[];
// eslint-disable-next-line @typescript-eslint/no-require-imports
const SecureStore = require('expo-secure-store');

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let vista: any;

async function abrir(initialUrl = '/') {
  ({ vista } = await abrirApp(initialUrl));
}

beforeEach(() => {
  // Só os mocks da API são resetados: resetAllMocks também apagaria as implementações
  // do armazenamento seguro simulado (jest.setup.js).
  funcoesDaApi().forEach((f) => f.mockReset());
  funcoesDeConta().forEach((f) => f.mockReset());
  SecureStore.__limpar();
  prepararApiSimulada();
});

describe('estrutura (login obrigatório)', () => {
  it('sem sessão, a primeira tela é o Login', async () => {
    await abrir('/');
    await waitFor(() => expect(vista).toHavePathname('/login'));
    expect(screen.getAllByText('Entrar').length).toBeGreaterThan(0);
  });

  it('sem sessão, uma rota protegida (/perfil) leva ao login', async () => {
    await abrir('/perfil');
    await waitFor(() => expect(vista).toHavePathname('/login'));
  });

  it('com sessão guardada, abre direto o Explorar (sem passar pelo login)', async () => {
    await comSessaoGuardada();
    await abrir('/');
    await waitFor(() => expect(vista).toHavePathname('/'));
    expect(await screen.findByText('Teste vocacional')).toBeTruthy();
    expect(auth.renovar).toHaveBeenCalledWith('refresh-guardado');
    expect(auth.meuPerfil).toHaveBeenCalled();
  });

  it('as abas principais são SOMENTE Explorar, Salvos e Perfil', async () => {
    const entradas = fs.readdirSync(path.join(APP_DIR, '(app)')).sort();
    expect(entradas).toEqual(['(explorar)', '(perfil)', '(salvos)', '_layout.tsx']);
    await comSessaoGuardada();
    await abrir('/');
    for (const rotulo of ['Explorar', 'Salvos', 'Perfil']) {
      expect((await screen.findAllByText(rotulo)).length).toBeGreaterThan(0);
    }
  });
});

describe('login', () => {
  it('login válido leva ao Explorar e guarda só o refresh token', async () => {
    auth.entrar.mockResolvedValue({ data: { usuario, tokens: tokens(1) } });
    auth.meuPerfil.mockResolvedValue({ data: usuario });
    await abrir('/');
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('E-mail'), 'ana@x.com');
    await user.type(screen.getByLabelText('Senha'), 'segredo1');
    await user.press(screen.getByRole('button', { name: 'Entrar' }));

    await waitFor(() => expect(vista).toHavePathname('/'));
    expect(auth.entrar).toHaveBeenCalledWith('ana@x.com', 'segredo1');
    expect(SecureStore.__conteudo()).toEqual({ [CHAVE]: 'refresh-1' });
  });

  it('credenciais inválidas mostram a mensagem do backend e continuam no login', async () => {
    auth.entrar.mockRejectedValue(new ApiError(401, 'INVALID_CREDENTIALS', 'E-mail ou senha inválidos.'));
    await abrir('/');
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('E-mail'), 'ana@x.com');
    await user.type(screen.getByLabelText('Senha'), 'errada');
    await user.press(screen.getByRole('button', { name: 'Entrar' }));

    expect(await screen.findByText('E-mail ou senha inválidos.')).toBeTruthy();
    expect(vista).toHavePathname('/login');
    expect(SecureStore.__conteudo()).toEqual({});
  });

  it('campos vazios não chamam a API', async () => {
    await abrir('/');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Entrar' }));
    expect(await screen.findByText('Informe e-mail e senha.')).toBeTruthy();
    expect(auth.entrar).not.toHaveBeenCalled();
  });

  it('sem development build/configuração, o Google não aparece (nada de botão decorativo)', async () => {
    await abrir('/');
    expect(await screen.findByText('Bem-vindo(a) de volta!')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Continuar com Google' })).toBeNull();
  });
});

describe('cadastro', () => {
  async function irParaCadastro() {
    await abrir('/');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Criar conta' }));
    await waitFor(() => expect(vista).toHavePathname('/cadastro'));
    return user;
  }

  it('cadastro válido abre a sessão e leva ao Explorar', async () => {
    auth.cadastrar.mockResolvedValue({ data: { usuario, tokens: tokens(1) } });
    auth.meuPerfil.mockResolvedValue({ data: usuario });
    const user = await irParaCadastro();
    await user.type(screen.getByLabelText('Nome de usuário'), 'ana');
    await user.type(screen.getByLabelText('E-mail'), 'ana@x.com');
    await user.type(screen.getByLabelText('Senha'), 'segredo1');
    await user.type(screen.getByLabelText('Confirme sua senha'), 'segredo1');
    await user.press(screen.getByRole('button', { name: 'Cadastrar' }));

    await waitFor(() => expect(vista).toHavePathname('/'));
    expect(auth.cadastrar).toHaveBeenCalledWith('ana', 'ana@x.com', 'segredo1');
  });

  it('confirmação diferente é barrada na interface, sem chamar a API', async () => {
    const user = await irParaCadastro();
    await user.type(screen.getByLabelText('Nome de usuário'), 'ana');
    await user.type(screen.getByLabelText('E-mail'), 'ana@x.com');
    await user.type(screen.getByLabelText('Senha'), 'segredo1');
    await user.type(screen.getByLabelText('Confirme sua senha'), 'outra');
    await user.press(screen.getByRole('button', { name: 'Cadastrar' }));
    expect(await screen.findByText('A confirmação não confere com a senha.')).toBeTruthy();
    expect(auth.cadastrar).not.toHaveBeenCalled();
  });

  it('erro do backend (conta já existe) é exibido como veio', async () => {
    auth.cadastrar.mockRejectedValue(new ApiError(409, 'CONFLICT', 'Nome de usuário ou e-mail já cadastrado.'));
    const user = await irParaCadastro();
    await user.type(screen.getByLabelText('Nome de usuário'), 'ana');
    await user.type(screen.getByLabelText('E-mail'), 'ana@x.com');
    await user.type(screen.getByLabelText('Senha'), 'segredo1');
    await user.type(screen.getByLabelText('Confirme sua senha'), 'segredo1');
    await user.press(screen.getByRole('button', { name: 'Cadastrar' }));
    expect(await screen.findByText('Nome de usuário ou e-mail já cadastrado.')).toBeTruthy();
    expect(vista).toHavePathname('/cadastro');
  });
});

describe('verificação de e-mail', () => {
  const pendente = { ...usuario, email_verificado: false };

  it('cadastro leva direto à tela do código; código errado mostra as tentativas e o certo confirma', async () => {
    auth.cadastrar.mockResolvedValue({ data: { usuario: pendente, tokens: tokens(1) } });
    conta.confirmarEmail
      .mockRejectedValueOnce(new ApiError(422, 'INVALID_CODE', 'Código incorreto.', undefined, { tentativas_restantes: 4 }))
      .mockResolvedValueOnce({ data: { usuario } });
    await abrir('/');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Criar conta' }));
    await user.type(await screen.findByLabelText('Nome de usuário'), 'ana');
    await user.type(screen.getByLabelText('E-mail'), 'ana@x.com');
    await user.type(screen.getByLabelText('Senha'), 'segredo12');
    await user.type(screen.getByLabelText('Confirme sua senha'), 'segredo12');
    await user.press(screen.getByRole('button', { name: 'Cadastrar' }));

    await waitFor(() => expect(vista).toHavePathname('/verificar-email'));
    expect(await screen.findByText('Confirme seu e-mail')).toBeTruthy();
    // o código acabou de ser enviado: reenvio só depois do intervalo
    expect(screen.getByRole('button', { name: /Reenviar código em \d+ s/ })).toBeDisabled();

    await user.type(screen.getByLabelText('Código de 5 dígitos'), '11111');
    expect(await screen.findByText('Código incorreto. Restam 4 tentativa(s).')).toBeTruthy();
    await user.type(screen.getByLabelText('Código de 5 dígitos'), '04821');
    expect(await screen.findByText('E-mail confirmado!')).toBeTruthy();
    expect(conta.confirmarEmail).toHaveBeenLastCalledWith('ana@x.com', '04821');
  });

  it('código expirado pede um novo; o reenvio mostra a resposta genérica do servidor', async () => {
    await SecureStore.setItemAsync(CHAVE, 'refresh-guardado');
    auth.renovar.mockResolvedValue({ data: { tokens: tokens(2) } });
    auth.meuPerfil.mockResolvedValue({ data: pendente });
    conta.confirmarEmail.mockRejectedValue(new ApiError(422, 'CODE_EXPIRED', 'Este código expirou. Peça um novo código.'));
    conta.enviarCodigoDeVerificacao.mockResolvedValue({
      data: { mensagem: 'Se houver uma conta com esse e-mail, enviaremos um código.' },
    });
    await abrir('/perfil');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Confirmar e-mail' }));
    await user.type(await screen.findByLabelText('Código de 5 dígitos'), '12345');
    expect(await screen.findByText(/Este código expirou\. Peça um novo código\. Toque em "Reenviar código"\./)).toBeTruthy();
    await user.press(screen.getByRole('button', { name: 'Reenviar código' }));
    expect(conta.enviarCodigoDeVerificacao).toHaveBeenCalledWith('ana@x.com');
    expect(await screen.findByText('Se houver uma conta com esse e-mail, enviaremos um código.')).toBeTruthy();
    expect(screen.getByRole('button', { name: /Reenviar código em \d+ s/ })).toBeDisabled();
  });
});

describe('recuperação de senha', () => {
  async function ateOCodigo() {
    conta.solicitarRecuperacao.mockResolvedValue({
      data: { mensagem: 'Se houver uma conta com esse e-mail, enviaremos um código.' },
    });
    await abrir('/');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Esqueceu a senha?' }));
    await user.type(await screen.findByLabelText('E-mail'), 'ana@x.com');
    await user.press(screen.getByRole('button', { name: 'Enviar' }));
    expect(await screen.findByText('Digite o código')).toBeTruthy();
    expect(conta.solicitarRecuperacao).toHaveBeenCalledWith('ana@x.com');
    return user;
  }

  it('e-mail → código → nova senha → "Senha alterada" → login', async () => {
    conta.validarCodigoDeRecuperacao.mockResolvedValue({ data: { valido: true } });
    conta.redefinirSenha.mockResolvedValue({ data: { mensagem: 'ok' } });
    const user = await ateOCodigo();
    await user.type(screen.getByLabelText('Código de 5 dígitos'), '04821');
    expect(await screen.findByText('Salvar nova senha')).toBeTruthy();
    await user.type(screen.getByLabelText('Nova senha'), 'novaSenha1');
    await user.type(screen.getByLabelText('Confirme a nova senha'), 'novaSenha1');
    await user.press(screen.getByRole('button', { name: 'Salvar nova senha' }));
    await waitFor(() => expect(vista).toHavePathname('/senha-alterada'));
    expect(conta.redefinirSenha).toHaveBeenCalledWith('ana@x.com', '04821', 'novaSenha1', 'novaSenha1');
    await user.press(screen.getByRole('button', { name: 'Entrar agora' }));
    await waitFor(() => expect(vista).toHavePathname('/login'));
    expect(auth.entrar).not.toHaveBeenCalled(); // a recuperação não abre sessão
  });

  it('código com tentativas esgotadas mostra a mensagem e não libera a nova senha', async () => {
    conta.validarCodigoDeRecuperacao.mockRejectedValue(
      new ApiError(429, 'TOO_MANY_ATTEMPTS', 'Muitas tentativas com este código. Peça um novo código.', undefined, {
        retry_after: 900,
      }),
    );
    const user = await ateOCodigo();
    await user.type(screen.getByLabelText('Código de 5 dígitos'), '99999');
    expect(await screen.findByText('Muitas tentativas com este código. Peça um novo código.')).toBeTruthy();
    expect(screen.queryByLabelText('Nova senha')).toBeNull();
  });

  it('limite de pedidos (429) mostra a mensagem e não avança', async () => {
    conta.solicitarRecuperacao.mockRejectedValue(
      new ApiError(429, 'RATE_LIMITED', 'Muitas tentativas. Tente novamente mais tarde.', undefined, { retry_after: 120 }),
    );
    await abrir('/recuperar-senha');
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('E-mail'), 'ana@x.com');
    await user.press(screen.getByRole('button', { name: 'Enviar' }));
    expect(await screen.findByText('Muitas tentativas. Tente novamente mais tarde.')).toBeTruthy();
    expect(screen.queryByText('Digite o código')).toBeNull();
  });
});

describe('sessão ativa', () => {
  it('sair apaga o armazenamento, avisa o servidor e volta ao login', async () => {
    await comSessaoGuardada();
    auth.sair.mockResolvedValue(undefined);
    await abrir('/perfil');
    const user = userEvent.setup();
    expect(await screen.findByText('ana@x.com')).toBeTruthy();
    await user.press(screen.getByRole('button', { name: 'Sair' }));

    await waitFor(() => expect(vista).toHavePathname('/login'));
    expect(auth.sair).toHaveBeenCalledWith('refresh-2');
    expect(SecureStore.__conteudo()).toEqual({});
  });

  it('sair sem rede ainda encerra a sessão local', async () => {
    await comSessaoGuardada();
    auth.sair.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', 'Sem rede.'));
    await abrir('/perfil');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Sair' }));
    await waitFor(() => expect(vista).toHavePathname('/login'));
    expect(SecureStore.__conteudo()).toEqual({});
  });

  it('refresh token guardado e inválido: cai no login e limpa o armazenamento', async () => {
    await SecureStore.setItemAsync(CHAVE, 'velho');
    auth.renovar.mockRejectedValue(new ApiError(401, 'INVALID_REFRESH_TOKEN', 'Inválido.'));
    await abrir('/');
    await waitFor(() => expect(vista).toHavePathname('/login'));
    expect(SecureStore.__conteudo()).toEqual({});
  });
});

describe('base visual (Etapa A)', () => {
  it('a barra inferior mostra as 3 abas e navega entre elas', async () => {
    await comSessaoGuardada();
    await abrir('/');
    const user = userEvent.setup();
    const abas = await screen.findAllByRole('tab');
    expect(abas.map((a) => a.props.accessibilityLabel)).toEqual(['Explorar', 'Salvos', 'Perfil']);
    expect(screen.getByRole('tab', { name: 'Explorar' })).toBeSelected();

    await user.press(screen.getByRole('tab', { name: 'Salvos' }));
    await waitFor(() => expect(vista).toHavePathname('/salvos'));
    expect(screen.getByRole('tab', { name: 'Salvos' })).toBeSelected();

    await user.press(screen.getByRole('tab', { name: 'Perfil' }));
    await waitFor(() => expect(vista).toHavePathname('/perfil'));

    await user.press(screen.getByRole('tab', { name: 'Explorar' }));
    await waitFor(() => expect(vista).toHavePathname('/'));
  });

  it('a busca do Explorar é um atalho para a tela de busca', async () => {
    await comSessaoGuardada();
    await abrir('/');
    const user = userEvent.setup();
    expect(await screen.findByText('Olá, ana!')).toBeTruthy();
    await user.press(screen.getByRole('search'));
    await waitFor(() => expect(vista).toHavePathname('/busca'));
  });

  it('login: sem o módulo nativo do Google não há botão do Google nem chamadas à API', async () => {
    await abrir('/login');
    expect(await screen.findByText('Bem-vindo(a) de volta!')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Google/ })).toBeNull();
    expect(funcoesDaApi().every((f) => f.mock.calls.length === 0)).toBe(true);
  });

  it('perfil: só opções que funcionam, e "Conta" abre a edição', async () => {
    await comSessaoGuardada();
    await abrir('/perfil');
    const user = userEvent.setup();
    expect(await screen.findByText('Configurações')).toBeTruthy();
    for (const opcao of ['Favoritos', 'Conta', 'Alterar senha', 'Ajuda', 'Sobre nós', 'Sair']) {
      expect(screen.getByRole('button', { name: opcao })).toBeTruthy();
    }
    for (const semSuporte of ['Modo Noturno', 'Notificações']) {
      expect(screen.queryByText(semSuporte)).toBeNull();
    }
    await user.press(screen.getByRole('button', { name: 'Conta' }));
    await waitFor(() => expect(vista).toHavePathname('/editar'));
  });

  it('o botão voltar do cabeçalho retorna à tela anterior', async () => {
    await comSessaoGuardada();
    await abrir('/');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Vestibulares' }));
    await waitFor(() => expect(vista).toHavePathname('/vestibulares'));
    await user.press(await screen.findByRole('button', { name: 'Voltar' }));
    await waitFor(() => expect(vista).toHavePathname('/'));
  });
});

describe('sem conexão ao abrir', () => {
  it('mostra "Sem conexão", mantém a sessão e permite tentar de novo', async () => {
    await SecureStore.setItemAsync(CHAVE, 'refresh-guardado');
    auth.renovar.mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', 'Sem rede.'));
    await abrir('/');
    expect(await screen.findByText('Sem conexão')).toBeTruthy();
    expect(SecureStore.__conteudo()).toEqual({ [CHAVE]: 'refresh-guardado' }); // não deslogou

    auth.renovar.mockResolvedValue({ data: { tokens: tokens(2) } });
    auth.meuPerfil.mockResolvedValue({ data: usuario });
    const user = userEvent.setup();
    await user.press(screen.getByRole('button', { name: 'Tentar novamente' }));
    await waitFor(() => expect(vista).toHavePathname('/'));
  });
});

describe('navegação dentro do Explorar e detalhes compartilhados', () => {
  beforeEach(async () => {
    await comSessaoGuardada();
  });

  it.each([
    ['/busca', 'Busca'],
    ['/cursos', 'Cursos'],
    ['/faculdades', 'Faculdades'],
    ['/vestibulares', 'Vestibulares'],
    ['/teste-vocacional', 'Teste Vocacional'],
    ['/teste-vocacional/perguntas', 'Teste Vocacional'],
    ['/teste-vocacional/resultado', 'Resultado'],
    ['/teste-vocacional/recomendados', 'Cursos recomendados'],
  ])('a área %s existe dentro do Explorar', async (rota, titulo) => {
    await abrir(rota);
    await waitFor(() => expect(vista).toHavePathname(rota));
    expect(await screen.findByText(titulo)).toBeTruthy();
  });

  it('o Explorar dá acesso a Cursos, Faculdades, Vestibulares e Teste vocacional', async () => {
    await abrir('/');
    const user = userEvent.setup();
    for (const [botao, rota] of [
      ['Ver todos: Cursos', '/cursos'],
      ['Ver todos: Faculdades Públicas', '/faculdades'],
      ['Vestibulares', '/vestibulares'],
      ['Teste vocacional', '/teste-vocacional'],
    ]) {
      await user.press(await screen.findByRole('button', { name: botao }));
      await waitFor(() => expect(vista).toHavePathname(rota));
      await act(async () => router.back());
      await waitFor(() => expect(vista).toHavePathname('/'));
    }
  });

  it.each([
    ['/cursos/12', 'Curso 12'],
    ['/faculdades/7', 'Faculdade 7'],
    ['/vestibulares/3', 'Vestibular 3'],
  ])('o detalhe %s abre', async (rota, titulo) => {
    await abrir(rota);
    expect(await screen.findByText(titulo)).toBeTruthy();
  });

  it('abrir um detalhe a partir de Salvos mantém a aba Salvos (rota compartilhada)', async () => {
    await abrir('/salvos');
    await waitFor(() => expect(vista).toHavePathname('/salvos'));
    await act(async () => router.push('/cursos/12'));
    await waitFor(() => expect(vista).toHavePathname('/cursos/12'));
    await act(async () => router.back());
    await waitFor(() => expect(vista).toHavePathname('/salvos')); // voltou para Salvos, não para o Explorar
  });
});
