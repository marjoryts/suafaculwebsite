// Dados e respostas simuladas do catálogo e dos favoritos para os testes de tela.
// Os testes chamam jest.mock('../src/api/catalogo') e jest.mock('../src/api/favoritos')
// e depois prepararApiSimulada() no beforeEach.
import * as catalogoReal from '../src/api/catalogo';
import { ApiError } from '../src/api/client';
import * as favoritosReal from '../src/api/favoritos';
import * as adminReal from '../src/api/admin';
import * as perfilReal from '../src/api/perfil';
import * as testeReal from '../src/api/testeVocacional';
import type { Curso, Faculdade, FaculdadeDetalhe, Favorito, Painel, Paginated, Vestibular } from '../src/api/tipos';

export const catalogo = catalogoReal as jest.Mocked<typeof catalogoReal>;
export const favoritosApi = favoritosReal as jest.Mocked<typeof favoritosReal>;
export const testeApi = testeReal as jest.Mocked<typeof testeReal>;
export const perfilApi = perfilReal as jest.Mocked<typeof perfilReal>;
export const adminApi = adminReal as jest.Mocked<typeof adminReal>;

/** Questionário curto (2 perguntas) no formato de GET /teste-vocacional/perguntas. */
export const QUESTIONARIO = {
  secoes: [
    { titulo: 'Interesses', perguntas: [{ id: 'q1', texto: 'O que você mais gosta?', opcoes: [{ id: 'a', texto: 'Tecnologia' }, { id: 'b', texto: 'Pessoas' }] }] },
    { titulo: 'Habilidades', perguntas: [{ id: 'q2', texto: 'Em que você é bom?', opcoes: [{ id: 'a', texto: 'Cálculo' }, { id: 'b', texto: 'Escrita' }] }] },
  ],
};

export function curso(id: number, extra: Partial<Curso> = {}): Curso {
  return {
    id,
    nome: `Curso ${id}`,
    instituicao: 'UNICAMP',
    faculdade_id: 7,
    modalidade: 'presencial',
    descricao: 'Forma profissionais da área.',
    duracao: '4 anos',
    grau: 'Bacharelado',
    area: 'Tecnologia',
    tipo_instituicao: 'Pública',
    ...extra,
  };
}

export function faculdade(id: number, extra: Partial<Faculdade> = {}): Faculdade {
  return {
    id,
    codigo_emec: String(id),
    nome: `Faculdade ${id}`,
    sigla: null,
    organizacao_academica: 'Universidade',
    tipo_instituicao: 'Pública',
    url: '',
    endereco: '',
    cidade: 'Campinas',
    uf: 'SP',
    telefone: '',
    email: '',
    situacao: 'Ativa',
    total_cursos: 0,
    ...extra,
  };
}

export function vestibular(id: number, extra: Partial<Vestibular> = {}): Vestibular {
  return {
    id,
    nome: `Vestibular ${id}`,
    instituicao: 'UNICAMP',
    faculdade_id: 7,
    tipo_instituicao: 'Pública',
    cidade: 'Campinas',
    regiao: 'Sudeste',
    periodo_inscricao: 'Agosto',
    data_prova: null,
    descricao: 'Processo seletivo.',
    link_edital: null,
    taxa_inscricao: null,
    cursos_oferecidos: null,
    requisitos: null,
    status: 'ativo',
    ...extra,
  };
}

export function pagina<T>(itens: T[], total = itens.length, page = 1, limit = 20): Paginated<T> {
  return { data: itens, meta: { total, page, limit, total_pages: Math.max(1, Math.ceil(total / limit)) } };
}

/** Respostas padrão: catálogo com poucos itens e nenhum favorito. */
export function prepararApiSimulada(favoritos: Favorito[] = []) {
  catalogo.listarCursos.mockReset().mockResolvedValue(pagina([curso(1), curso(2)]));
  catalogo.listarFaculdades.mockReset().mockResolvedValue(pagina([faculdade(7), faculdade(8)]));
  catalogo.obterCurso.mockReset().mockImplementation(async (id) => ({ data: curso(id) }));
  catalogo.obterFaculdade
    .mockReset()
    .mockImplementation(async (id): Promise<{ data: FaculdadeDetalhe }> => ({
      data: { ...faculdade(id), cursos: [], vestibulares: [] },
    }));
  catalogo.listarVestibulares.mockReset().mockResolvedValue(pagina([vestibular(3), vestibular(4)]));
  catalogo.obterVestibular.mockReset().mockImplementation(async (id) => ({ data: vestibular(id) }));
  catalogo.sugestoes.mockReset().mockResolvedValue({ data: { local: [], faculdade: [], curso: [] } });
  favoritosApi.listarFavoritos.mockReset().mockResolvedValue({ data: favoritos });
  favoritosApi.favoritar
    .mockReset()
    .mockImplementation(async (tipo, id) => ({ data: { tipo, item_id: id, nome_item: `Item ${id}`, created_at: null } }));
  favoritosApi.desfavoritar.mockReset().mockResolvedValue(undefined);
  // Teste vocacional: questionário curto, nenhum resultado ainda (404 nas recomendações).
  if (jest.isMockFunction(testeApi.perguntas)) {
    testeApi.perguntas.mockReset().mockResolvedValue({ data: QUESTIONARIO });
    testeApi.historico.mockReset().mockResolvedValue({ data: [] });
    testeApi.recomendacoes
      .mockReset()
      .mockRejectedValue(new ApiError(404, 'RESOURCE_NOT_FOUND', 'Nenhum teste vocacional encontrado na sua conta.'));
    testeApi.enviarRespostas.mockReset();
  }
  if (jest.isMockFunction(perfilApi.meuPainel)) {
    perfilApi.meuPainel.mockReset().mockResolvedValue({ data: painelVazio() });
    perfilApi.atualizarPerfil.mockReset();
    perfilApi.alterarSenha.mockReset();
    perfilApi.pedirTrocaDeEmail.mockReset();
    perfilApi.confirmarTrocaDeEmail.mockReset();
  }
}

export function painelVazio(extra: Partial<Painel> = {}): Painel {
  return {
    usuario: { id: 1, nome_usuario: 'ana', email: 'ana@x.com', tipo: 'aluno', avatar_url: null, auth_provider: 'local', created_at: null, email_verificado: true, senha_definida: true },
    contagem_favoritos: { cursos: 0, faculdades: 0, vestibulares: 0 },
    favoritos_recentes: [],
    proximas_provas: [],
    testes_vocacionais: [],
    ultimo_teste: null,
    ...extra,
  };
}
