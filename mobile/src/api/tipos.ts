// Tipos das respostas da API /api/v1 (contrato: GET /api/v1/openapi.json).
// Só descrevem o formato; nenhuma regra de negócio mora aqui.

export type Tokens = {
  token_type: 'Bearer';
  access_token: string;
  expires_in: number; // segundos
  refresh_token: string;
  refresh_expires_in: number; // segundos
};

export type Usuario = {
  id: number;
  nome_usuario: string;
  email: string;
  tipo: 'aluno' | 'admin';
  avatar_url: string | null;
  auth_provider: string | null;
  created_at: string | null;
  /** false: conta criada antes da verificação ou ainda sem o código confirmado. */
  email_verificado: boolean;
  /** false: conta criada pelo Google, ainda sem senha própria (não pede a senha atual). */
  senha_definida: boolean;
};

/** Resposta de /auth/login e /auth/registrar. */
export type Sessao = { usuario: Usuario; tokens: Tokens };

export type Resposta<T> = { data: T };

export type Paginated<T> = {
  data: T[];
  meta: { total: number; page: number; limit: number; total_pages: number };
};

// ── Catálogo (GET /cursos, /faculdades, /busca/sugestoes) ──────────────────

export type Curso = {
  id: number;
  nome: string;
  instituicao: string | null;
  faculdade_id: number | null;
  modalidade: string | null; // presencial | ead | semipresencial
  descricao: string | null;
  duracao: string | null;
  grau: string | null;
  area: string | null;
  tipo_instituicao: string | null; // Pública | Privada
};

export type CursoResumo = Pick<Curso, 'id' | 'nome' | 'modalidade' | 'grau' | 'area'>;

export type VestibularResumo = {
  id: number;
  nome: string;
  data_prova: string | null;
  periodo_inscricao: string | null;
  link_edital: string | null;
};

export type Faculdade = {
  id: number;
  codigo_emec: string | null;
  nome: string;
  sigla: string | null;
  organizacao_academica: string | null;
  tipo_instituicao: string | null;
  url: string | null;
  endereco: string | null;
  cidade: string | null;
  uf: string | null;
  telefone: string | null;
  email: string | null;
  situacao: string | null;
  total_cursos: number;
};

export type Vestibular = {
  id: number;
  nome: string;
  instituicao: string | null;
  faculdade_id: number | null;
  tipo_instituicao: string | null;
  cidade: string | null;
  regiao: string | null;
  periodo_inscricao: string | null; // texto livre ("1º a 30 de agosto")
  data_prova: string | null; // ISO "AAAA-MM-DD"
  descricao: string | null;
  link_edital: string | null;
  taxa_inscricao: string | null;
  cursos_oferecidos: string | null;
  requisitos: string | null;
  status: string | null; // ativo | encerrado | data_invalida | nao_validado
};

export type FaculdadeDetalhe = Faculdade & { cursos: CursoResumo[]; vestibulares: VestibularResumo[] };

export type Sugestao = {
  tipo: 'local' | 'faculdade' | 'curso';
  campo: 'cidade' | 'faculdade' | 'curso';
  valor: string;
  rotulo: string;
  detalhe: string | null;
  id?: number; // só faculdades
  subtipo?: string; // locais: cidade | uf | regiao
};

export type Sugestoes = Record<Sugestao['tipo'], Sugestao[]>;

// ── Favoritos (GET/PUT/DELETE /favoritos) ───────────────────────────────────

export type TipoFavorito = 'curso' | 'faculdade' | 'vestibular';

export type Favorito = {
  tipo: TipoFavorito;
  item_id: number;
  nome_item: string;
  created_at: string | null;
  /** Resumo do item; null se ele foi removido do catálogo depois de favoritado. */
  item?: Record<string, unknown> | null;
};

// ── Teste vocacional (GET/POST /teste-vocacional/*) ─────────────────────────

export type Questionario = {
  secoes: { titulo: string; perguntas: { id: string; texto: string; opcoes: { id: string; texto: string }[] }[] }[];
};

export type PontuacaoPerfil = { chave: string; nome: string; percentual: number };

export type ResultadoTeste = {
  resultado_id: number | null;
  scores: Record<string, number>;
  pontuacoes: PontuacaoPerfil[];
  perfis: { chave: string; nome: string; descricao: string; areas: string[] }[];
  salvo: boolean;
};

export type ItemHistorico = {
  id: number;
  perfil: string;
  perfil_nome: string;
  created_at: string | null;
  pontuacoes: PontuacaoPerfil[];
};

export type CursoRecomendado = {
  id: number;
  nome: string;
  area: string | null;
  grau: string | null;
  descricao: string | null;
  compatibilidade: number; // 1–100
  perfis: string[];
  criterio: 'nome' | 'area';
  total_instituicoes: number;
};

export type Recomendacoes = {
  resultado_id: number;
  perfil: string;
  perfil_nome: string;
  perfil_descricao: string | null;
  created_at: string | null;
  cursos: CursoRecomendado[];
  total_compativeis: number;
  sem_dados_suficientes: number;
  total_cursos_analisados: number;
};

// ── Painel do aluno (GET /me/dashboard) ─────────────────────────────────────

export type ProximaProva = {
  id: number;
  nome: string;
  instituicao: string | null;
  cidade: string | null;
  regiao: string | null;
  data_prova: string;
  periodo_inscricao: string | null;
  link_edital: string | null;
};

export type Painel = {
  usuario: Usuario;
  contagem_favoritos: { cursos: number; faculdades: number; vestibulares: number };
  favoritos_recentes: Favorito[];
  proximas_provas: ProximaProva[];
  testes_vocacionais: ItemHistorico[];
  ultimo_teste: ItemHistorico | null;
};

// ── Painel administrativo (/admin/*) ────────────────────────────────────────

export type UsuarioAdmin = { id: number; nome_usuario: string; email: string; tipo: 'aluno' | 'admin' };

export type Automacao = {
  id: number;
  tipo: string;
  executado_em: string | null;
  sucesso: number | boolean | null;
  resumo: string | null;
  status: string | null;
  origem: string | null;
};

export type EstatisticasAdmin = { stats: Record<string, number>; automacoes: Automacao[] };

export type RelatorioValidacao = {
  resumo: {
    total: number;
    ativos: number;
    encerrados: number;
    data_invalida: number;
    sem_faculdade_cadastrada: number;
    falhas: number;
    aplicado: boolean;
  };
  itens: { vestibular_id: number; nome: string; status_validacao: string; cadastrado_ok: boolean; faculdade_nome: string | null }[];
};

/** Resposta das importações do e-MEC (o formato varia: código, lote, UF ou Brasil). */
export type RelatorioImportacao = { success?: boolean; message?: string; [chave: string]: unknown };
