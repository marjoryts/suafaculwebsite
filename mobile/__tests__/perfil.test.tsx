// Etapa E: Salvos, painel do aluno no Perfil, editar perfil, alterar senha, Ajuda e Sobre nós.
import { userEvent } from '@testing-library/react-native';
import { screen, waitFor } from 'expo-router/testing-library';

import { ApiError } from '../src/api/client';
import type { Favorito } from '../src/api/tipos';
import { filtrarFaq, normalizar } from '../src/conteudo/institucional';
import { abrirApp, auth, comSessaoGuardada, usuarioAna } from '../test-utils/app';
import { favoritosApi, painelVazio, perfilApi, prepararApiSimulada } from '../test-utils/apiSimulada';

jest.mock('../src/api/auth');
jest.mock('../src/api/catalogo');
jest.mock('../src/api/favoritos');
jest.mock('../src/api/testeVocacional');
jest.mock('../src/api/perfil');
// eslint-disable-next-line @typescript-eslint/no-require-imports
const SecureStore = require('expo-secure-store');

const FAVORITOS: Favorito[] = [
  { tipo: 'faculdade', item_id: 7, nome_item: 'UNICAMP', created_at: null, item: { id: 7, cidade: 'Campinas', uf: 'SP', tipo_instituicao: 'Pública' } },
  { tipo: 'curso', item_id: 1, nome_item: 'Medicina', created_at: null, item: { id: 1, instituicao: 'USP', modalidade: 'presencial' } },
  { tipo: 'curso', item_id: 99, nome_item: 'Curso antigo', created_at: null, item: null },
];

beforeEach(async () => {
  SecureStore.__limpar();
  prepararApiSimulada();
  await comSessaoGuardada();
});

describe('aba Salvos', () => {
  it('agrupa como o painel do site, com resumo de cada item, e abre o detalhe', async () => {
    favoritosApi.listarFavoritos.mockResolvedValue({ data: FAVORITOS });
    const { vista } = await abrirApp('/salvos');
    const user = userEvent.setup();
    expect(await screen.findByText('Faculdades favoritas (1)')).toBeTruthy();
    expect(screen.getByText('Cursos favoritos (2)')).toBeTruthy();
    expect(screen.getByText('Vestibulares salvos (0)')).toBeTruthy();
    expect(screen.getByText('Campinas/SP · Pública')).toBeTruthy();
    expect(screen.getByText('USP · Presencial')).toBeTruthy();
    expect(screen.getByText('Não está mais disponível no catálogo')).toBeTruthy(); // item apagado do catálogo
    await user.press(screen.getByRole('button', { name: 'Medicina, USP · Presencial' }));
    await waitFor(() => expect(vista).toHavePathname('/cursos/1'));
  });

  it('remover pelo coração tira o item da lista', async () => {
    favoritosApi.listarFavoritos.mockResolvedValue({ data: FAVORITOS });
    await abrirApp('/salvos');
    const user = userEvent.setup();
    await user.press(await screen.findByRole('button', { name: 'Remover UNICAMP dos salvos' }));
    expect(favoritosApi.desfavoritar).toHaveBeenCalledWith('faculdade', 7);
    expect(await screen.findByText('Faculdades favoritas (0)')).toBeTruthy();
  });

  it('sem nada salvo, mostra o convite do site', async () => {
    await abrirApp('/salvos');
    expect(await screen.findByText('Nada salvo ainda')).toBeTruthy();
  });
});

describe('Perfil: Meu painel', () => {
  it('mostra contadores, próximas provas dos salvos e o perfil vocacional', async () => {
    perfilApi.meuPainel.mockResolvedValue({
      data: painelVazio({
        contagem_favoritos: { cursos: 2, faculdades: 1, vestibulares: 3 },
        proximas_provas: [{ id: 3, nome: 'Fuvest', instituicao: 'USP', cidade: 'São Paulo', regiao: 'Sudeste', data_prova: '2099-11-20', periodo_inscricao: null, link_edital: null }],
        testes_vocacionais: [{ id: 9, perfil: 'tecnico', perfil_nome: 'Perfil Técnico / Exato', created_at: null, pontuacoes: [{ chave: 'tecnico', nome: 'Perfil Técnico / Exato', percentual: 70 }] }],
        ultimo_teste: { id: 9, perfil: 'tecnico', perfil_nome: 'Perfil Técnico / Exato', created_at: null, pontuacoes: [{ chave: 'tecnico', nome: 'Perfil Técnico / Exato', percentual: 70 }] },
      }),
    });
    const { vista } = await abrirApp('/perfil');
    const user = userEvent.setup();
    expect(await screen.findByLabelText('2 Cursos favoritos')).toBeTruthy();
    expect(screen.getByLabelText('3 Vestibulares salvos')).toBeTruthy();
    expect(screen.getByLabelText('1 Teste vocacional')).toBeTruthy();
    expect(screen.getByText('Fuvest')).toBeTruthy();
    expect(screen.getByText('Perfil Técnico / Exato: 70%')).toBeTruthy();
    expect(screen.getByText('Estudante')).toBeTruthy();
    await user.press(screen.getByRole('button', { name: 'Ver resultado completo' }));
    await waitFor(() => expect(vista).toHavePathname('/teste-vocacional/resultado'));
  });

  it('sem teste e sem provas, mostra os convites do site', async () => {
    await abrirApp('/perfil');
    expect(await screen.findByText(/Salve vestibulares nos favoritos/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Fazer teste agora' })).toBeTruthy();
  });
});

describe('editar perfil e senha', () => {
  it('salva nome e e-mail pela API e atualiza a sessão', async () => {
    perfilApi.atualizarPerfil.mockResolvedValue({ data: { ...usuarioAna, nome_usuario: 'ana.souza' } });
    await abrirApp('/editar');
    const user = userEvent.setup();
    const campo = await screen.findByLabelText('Nome de usuário');
    expect(screen.getAllByRole('button', { name: 'Salvar alterações' })[0]).toBeDisabled(); // nada mudou ainda
    await user.clear(campo);
    await user.type(campo, 'ana.souza');
    await user.press(screen.getByRole('button', { name: 'Salvar alterações' }));
    expect(perfilApi.atualizarPerfil).toHaveBeenCalledWith({ nome_usuario: 'ana.souza', email: 'ana@x.com' });
    expect(await screen.findByText('Perfil atualizado com sucesso!')).toBeTruthy();
    expect(screen.getAllByText('ana.souza').length).toBeGreaterThan(0); // topo já mostra o novo nome
  });

  it('mostra a mensagem do backend (ex.: e-mail em uso)', async () => {
    perfilApi.atualizarPerfil.mockRejectedValue(new ApiError(422, 'VALIDATION_ERROR', 'Esse nome de usuário ou e-mail já está em uso.'));
    await abrirApp('/editar');
    const user = userEvent.setup();
    const email = await screen.findByLabelText('Endereço de E-mail');
    await user.clear(email);
    await user.type(email, 'outra@x.com');
    await user.press(screen.getByRole('button', { name: 'Salvar alterações' }));
    expect(await screen.findByText('Esse nome de usuário ou e-mail já está em uso.')).toBeTruthy();
  });

  it('alterar senha confere a confirmação antes de chamar a API', async () => {
    perfilApi.alterarSenha.mockResolvedValue({ data: usuarioAna });
    await abrirApp('/alterar-senha');
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('Nova senha'), 'novaSenha1');
    await user.type(screen.getByLabelText('Confirme a nova senha'), 'outra');
    await user.press(screen.getByRole('button', { name: 'Alterar senha' }));
    expect(await screen.findByText('A confirmação não confere com a nova senha.')).toBeTruthy();
    expect(perfilApi.alterarSenha).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText('Confirme a nova senha'));
    await user.type(screen.getByLabelText('Confirme a nova senha'), 'novaSenha1');
    await user.press(screen.getByRole('button', { name: 'Alterar senha' }));
    expect(perfilApi.alterarSenha).toHaveBeenCalledWith('novaSenha1', 'novaSenha1');
    expect(await screen.findByText('Senha alterada com sucesso!')).toBeTruthy();
    expect(auth.sair).not.toHaveBeenCalled(); // a sessão deste aparelho continua
  });
});

describe('Ajuda e Sobre nós', () => {
  it('a busca ignora acentos e exige todos os termos, como no site', () => {
    expect(normalizar('Vocacional É')).toBe('vocacional e');
    expect(filtrarFaq('').length).toBe(3);
    const r = filtrarFaq('gratuito teste');
    expect(r.map((g) => g.titulo)).toEqual(['Teste vocacional']);
    expect(r[0].perguntas.map((p) => p.pergunta)).toEqual(['O teste vocacional é gratuito?']);
    expect(filtrarFaq('inexistentezzz')).toEqual([]);
  });

  it('tela de Ajuda: perguntas abrem e a busca filtra', async () => {
    await abrirApp('/ajuda');
    const user = userEvent.setup();
    const pergunta = await screen.findByRole('button', { name: 'Como me cadastrar?' });
    expect(screen.queryByText(/Criar conta/)).toBeNull();
    await user.press(pergunta);
    expect(screen.getByText(/Criar conta/)).toBeTruthy();
    await user.type(screen.getByLabelText('Busque uma dúvida...'), 'edital');
    expect(await screen.findByText('Onde vejo as datas dos vestibulares?')).toBeTruthy();
    expect(screen.queryByText('Como me cadastrar?')).toBeNull();
  });

  it('Sobre nós mostra missão, valores e a equipe com as fotos do backend', async () => {
    await abrirApp('/sobre');
    expect(await screen.findByText('Nossa missão')).toBeTruthy();
    expect(screen.getByText('Transparência')).toBeTruthy();
    expect(screen.getByLabelText('Marjory Sousa, Desenvolvedora Full Stack')).toBeTruthy();
  });
});
