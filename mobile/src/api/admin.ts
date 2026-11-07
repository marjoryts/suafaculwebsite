// Painel administrativo (/api/v1/admin/*): só funciona com conta admin — o servidor
// confere o papel no banco a cada chamada. Listagens usam as rotas do catálogo.
import { api } from './client';
import type {
  Curso,
  EstatisticasAdmin,
  Faculdade,
  RelatorioImportacao,
  RelatorioValidacao,
  Resposta,
  UsuarioAdmin,
  Vestibular,
} from './tipos';

const IMPORTACAO_MS = 5 * 60_000; // e-MEC por UF/Brasil leva minutos

export const estatisticas = () => api<Resposta<EstatisticasAdmin>>('/admin/estatisticas', { autenticado: true });

export const listarUsuarios = () => api<Resposta<UsuarioAdmin[]>>('/admin/usuarios', { autenticado: true });

export type DadosUsuario = { nome_usuario: string; email: string; password?: string; tipo?: 'aluno' | 'admin' };

export const criarUsuario = (dados: DadosUsuario) =>
  api<Resposta<UsuarioAdmin>>('/admin/usuarios', { metodo: 'POST', corpo: dados, autenticado: true });

export const atualizarUsuario = (id: number, dados: DadosUsuario) =>
  api<Resposta<UsuarioAdmin>>(`/admin/usuarios/${id}`, { metodo: 'PATCH', corpo: dados, autenticado: true });

export const excluirUsuario = (id: number) =>
  api<void>(`/admin/usuarios/${id}`, { metodo: 'DELETE', autenticado: true });

export type DadosFaculdade = Partial<Record<
  'codigo_emec' | 'nome' | 'sigla' | 'organizacao_academica' | 'tipo_instituicao' | 'url' | 'endereco' | 'cidade' | 'uf' | 'telefone' | 'email' | 'situacao',
  string
>>;

export const criarFaculdade = (dados: DadosFaculdade) =>
  api<Resposta<Faculdade>>('/admin/faculdades', { metodo: 'POST', corpo: dados, autenticado: true });

export const atualizarFaculdade = (id: number, dados: DadosFaculdade) =>
  api<Resposta<Faculdade>>(`/admin/faculdades/${id}`, { metodo: 'PATCH', corpo: dados, autenticado: true });

export const excluirFaculdade = (id: number) =>
  api<void>(`/admin/faculdades/${id}`, { metodo: 'DELETE', autenticado: true });

export const importarFaculdades = (alvo: { codigos: string[] } | { uf: string } | { brasil: true }) =>
  api<Resposta<RelatorioImportacao>>('/admin/faculdades/importacoes', {
    metodo: 'POST',
    corpo: alvo,
    autenticado: true,
    timeoutMs: IMPORTACAO_MS,
  });

export type DadosCurso = Partial<Record<
  'nome' | 'instituicao' | 'modalidade' | 'descricao' | 'duracao' | 'grau' | 'area' | 'tipo_instituicao',
  string
>> & { faculdade_id?: number | null };

export const criarCurso = (dados: DadosCurso) =>
  api<Resposta<Curso>>('/admin/cursos', { metodo: 'POST', corpo: dados, autenticado: true });

export type DadosVestibular = Partial<Record<
  | 'nome' | 'instituicao' | 'tipo_instituicao' | 'cidade' | 'regiao' | 'periodo_inscricao' | 'data_prova'
  | 'descricao' | 'link_edital' | 'taxa_inscricao' | 'cursos_oferecidos' | 'requisitos',
  string
>>;

export const criarVestibular = (dados: DadosVestibular) =>
  api<Resposta<Vestibular>>('/admin/vestibulares', { metodo: 'POST', corpo: dados, autenticado: true });

/** aplicar=false: só o relatório (pré-visualizar); true: grava. */
export const validarVestibulares = (aplicar: boolean) =>
  api<Resposta<RelatorioValidacao>>('/admin/vestibulares/validacao', {
    metodo: 'POST',
    corpo: { aplicar },
    autenticado: true,
    timeoutMs: 60_000,
  });
