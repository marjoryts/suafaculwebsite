# Migração do banco para o Supabase (PostgreSQL)

## 1. Diagnóstico da arquitetura anterior

| Projeto | O que é | Situação encontrada |
|---|---|---|
| `suafaculwebsite` | Flask (site + API v1 do Mobile) | **Backend de referência.** Único backend funcional e completo: camadas rotas → services → models, 384 testes, API v1 com access/refresh token, login Google, painel admin protegido no servidor, automações (Vercel Cron). Banco: SQLite. |
| `suafaculMobile` | App Expo (JS) — app principal | Já consumia o Flask, mas com um contrato que **nunca existiu** no backend: `/home`, `/busca`, `/auth/register` com `senha`, login com token único, favoritos agrupados, `/resultados/ultimo`, `/api/health`. Cadastro, login e home quebravam. Teste vocacional com escala Likert fixa (1–5) incompatível com o teste real do servidor. Chave do Google Maps (sem uso) exposta no `app.json`. |
| `suafacul-projeto-expo` | Tentativa de backend Express | Não está em nenhum repositório acessível nem no computador — não foi usado. As regras de negócio vivem só no Flask. |
| `suafaculwebsite/mobile` | App Expo (TypeScript, expo-router) | Usa corretamente a API v1; mantido intacto (126 testes passando). |

Riscos do banco antigo: na Vercel o SQLite ficava em `/tmp` e era recriado a cada cold start —
**cadastros, favoritos e testes vocacionais se perdiam em produção**. O script MySQL em
`docs/legado/` já era obsoleto.

## 2. Decisões

1. **Flask continua sendo o backend** (site e Mobile). O Mobile consome só a API v1; nenhuma
   regra é reimplementada no app.
2. **Supabase PostgreSQL é o banco central e único.** O SQLite deixa de ser usado pela
   aplicação; só é lido (em modo somente leitura) pelo comando de migração de dados.
3. **Supabase Auth não foi adotado (por ora).** Motivos:
   - as senhas atuais são hashes do werkzeug (scrypt/pbkdf2), que o Supabase Auth não importa
     — todos os usuários teriam de redefinir a senha;
   - o login web (cookie), a sessão do Mobile (access + refresh rotativo com detecção de reuso),
     o login Google e o papel admin/aluno conferido no banco a cada requisição já funcionam e são
     testados; trocar exigiria reescrever o login dos três clientes;
   - o Flask continua sendo a única autoridade de identidade (sem duas fontes de verdade).
   Se no futuro quiser recuperação de senha por e-mail / verificação de e-mail (telas hoje marcadas
   como "indisponível" no app), o caminho é Supabase Auth com migração gradual (reset no primeiro
   login) — fora do escopo desta etapa.
4. **Modelo de segurança do banco**
   - O backend conecta com o papel **`suafacul_backend`**: só `SELECT/INSERT/UPDATE/DELETE` nas
     tabelas do app; sem DDL, sem `TRUNCATE`, sem acesso a `auth`/`storage`; **sujeito a RLS**
     (política explícita `backend_acesso` em cada tabela).
   - **RLS ligado em todas as tabelas** e **nenhuma permissão nem política para `anon` e
     `authenticated`**: a Data API (PostgREST) do Supabase não lê nem grava nada, mesmo que a
     chave anon vaze. Nenhum frontend recebe chave do Supabase.
   - As regras por usuário (cada um só vê os próprios favoritos/testes; só admin gerencia
     conteúdo) são aplicadas pelo backend, que valida o token e confere o papel no banco a cada
     requisição — como já era.
   - `service_role` e a senha do `postgres` nunca vão para o deploy (só `DATABASE_URL_ADMIN`, na
     máquina de quem administra).

## 3. O que mudou

| Área | Arquivos |
|---|---|
| Esquema (fonte da verdade) | `supabase/migrations/2026112600000{1,2,3}_*.sql` — tabelas, FKs, CHECKs, índices (trigram para busca), funções `normalizar()`/`data_iso()`, gatilhos de `updated_at`, RLS e papel do backend |
| Acesso ao banco | `config/database.py` — psycopg 3 + pool compatível com o pooler do Supabase; traduz `?`/`:nome`; devolve datas no mesmo formato de antes (contrato JSON inalterado) |
| Models | ajustes pontuais: datas de prova com `data_iso()`, busca de cursos/vestibulares **sem diferenciar acentos** (antes só faculdades), login por identificador, telefone |
| Inicialização | `database/init_db.py` — aplica migrations pendentes + dados de referência reais numa transação com `pg_advisory_xact_lock` |
| Migração de dados | `database/migracao_sqlite.py` + `flask --app wsgi migrar-sqlite` |
| API v1 (aditivo, compatível) | `POST /auth/login` aceita `identificador`; `PATCH /me` aceita `telefone` e `senha_atual`; `GET /cursos/catalogo`; `GET /faculdades?curso=&exato=true`; `GET /api/health` |
| Deploy | `wsgi.py` não inicializa mais o banco a cada cold start; `requirements.txt` (+psycopg) ; `.env.example` |
| Mobile (`suafaculMobile`) | `src/api/*`, `src/storage.js`, `src/mappers.js`, `context/AuthContext.js`, tela do teste vocacional (alternativas reais), `app.json` sem chave; e2e em `scripts/e2e` |
| Testes | toda a suíte roda contra PostgreSQL real (`tests/conftest.py`), opcionalmente com o papel restrito; novos testes em `tests/test_supabase_integracao.py` e de migração em `tests/test_auditoria_integridade.py` |

### Esquema e integridade

| Tabela | FK | Ao excluir o pai | Restrições |
|---|---|---|---|
| `usuarios` | — | — | `nome_usuario` e `email` únicos; `tipo ∈ {aluno, admin}`; `google_id` único quando presente; telefone com formato |
| `faculdades` | — | — | `codigo_emec` único; `tipo_instituicao ∈ {Pública, Privada}` |
| `cursos` | `faculdade_id → faculdades` | SET NULL | `codigo_inep_curso` único quando presente |
| `vestibulares` | `faculdade_id → faculdades` | SET NULL | `cadastrado_ok ∈ {0,1}`; `data_prova` texto (o validador marca `data_invalida`) |
| `favoritos` | `usuario_id → usuarios` | CASCADE | `(usuario_id, tipo, item_id)` único; `tipo ∈ {curso, vestibular, faculdade}`; `item_id` polimórfico validado no serviço |
| `teste_vocacional_resultados` | `usuario_id → usuarios` (anulável) | SET NULL | — |
| `refresh_tokens` | `usuario_id → usuarios` | CASCADE | `token_hash` único |
| `automacao_logs` | — | — | no máximo uma execução `executando` por tipo (índice único parcial) |
| `cursos_catalogo` | — | — | nome único sem diferenciar maiúsculas |

Ids são `BIGINT IDENTITY`; datas são `TIMESTAMPTZ` (UTC).

## 4. Passo a passo no Supabase (manual)

> Nada disto pôde ser executado a partir do ambiente de desenvolvimento usado na migração
> (não havia acesso ao seu projeto). Tudo foi validado num PostgreSQL 16 com os papéis do
> Supabase simulados (`anon`, `authenticated`, `service_role`). Siga na ordem.

1. **Projeto**: crie (ou use) um projeto no Supabase. Anote o *project ref* e a senha do banco
   (`postgres`).
2. **Aplicar as migrations** (com o papel `postgres`), em ordem:
   - *Opção A — SQL Editor*: cole e execute `20261126000001_esquema_inicial.sql`, depois
     `..._000002_rls_e_permissoes.sql`, depois `..._000003_usuarios_telefone.sql`.
   - *Opção B — CLI*: `supabase init` (mantém a pasta `supabase/migrations`),
     `supabase link --project-ref <ref>`, `supabase db push`.
   - *Opção C*: `DATABASE_URL_ADMIN=<conexão postgres> flask --app wsgi init-db` (aplica as
     pendentes e já semeia o catálogo).
   As migrations são idempotentes: reaplicar não causa problema.
3. **Senha do papel da aplicação** (SQL Editor) — escolha uma senha forte, guarde no
   gerenciador de senhas:
   ```sql
   ALTER ROLE suafacul_backend WITH LOGIN PASSWORD '<senha forte>';
   ```
4. **Strings de conexão** (Painel → *Connect*):
   - `DATABASE_URL` (aplicação, Vercel): **Transaction pooler**, porta **6543**, usuário
     **`suafacul_backend.<project-ref>`**, `?sslmode=require`. (A conexão direta do Supabase é só
     IPv6; a Vercel precisa do pooler.)
   - `DATABASE_URL_ADMIN` (só na sua máquina): **Session pooler** (porta 5432) ou *Direct*, usuário
     `postgres.<project-ref>`.
5. **Data API** (defesa extra, recomendado): o app não usa PostgREST. Em *Project Settings → Data
   API*, desative a Data API **ou** remova `public` dos *Exposed schemas*. Mesmo sem isso, RLS e a
   ausência de GRANT já bloqueiam `anon`/`authenticated`.
6. **Security Advisor** (*Advisors → Security*): deve mostrar RLS habilitado em todas as tabelas.
   Avisos de "RLS enabled, no policy" para `anon/authenticated` são esperados (é o bloqueio).
7. **Opcional**: *Database → Settings → SSL enforcement* ligado; *Network restrictions* se tiver
   IPs fixos; backups/PITR conforme o plano.
8. **Migrar os dados do SQLite** (na máquina que tem o `database/suafacul.db` real):
   ```bash
   export DATABASE_URL_ADMIN='postgresql://postgres.<ref>:<senha>@aws-0-<regiao>.pooler.supabase.com:5432/postgres?sslmode=require'
   flask --app wsgi migrar-sqlite database/suafacul.db --simular   # relatório, nada é gravado
   flask --app wsgi migrar-sqlite database/suafacul.db             # grava (transação única)
   flask --app wsgi init-db                                       # completa o catálogo, se faltar algo
   ```
   - o SQLite é aberto **somente para leitura** e não é alterado — **não apague o arquivo** até
     concluir a validação (item 10);
   - ids, hashes de senha (os usuários entram com a mesma senha), favoritos, resultados e logs
     são preservados; as sequências continuam de onde o SQLite parou;
   - o comando recusa gravar se o destino já tiver usuários (use `--substituir` só se for
     intencional); catálogo semeado antes por um `init-db` é substituído pelo do SQLite para manter
     os ids referenciados pelos favoritos;
   - vínculos inválidos são tratados pela regra da FK e listados no relatório.
   Se não houver um SQLite com dados reais, pule para o `init-db` (cria o esquema, o catálogo e o
   primeiro admin a partir de `SUAFACUL_ADMIN_PASSWORD`).
9. **Vercel** (*Project Settings → Environment Variables*): `DATABASE_URL`, `FLASK_SECRET_KEY`,
   `CRON_SECRET`, `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` (se usar). **Não** cadastre
   `DATABASE_URL_ADMIN` nem a senha do `postgres`. Faça o redeploy.
10. **Validação**:
    - `GET https://<app>/api/health` → `{"status":"ok","database":"ok"}`;
    - painel admin: totais de usuários/favoritos/testes iguais aos do relatório da migração;
    - login de um usuário antigo com a senha de sempre; favoritos dele no site e no app;
    - cadastrar uma conta nova, favoritar, fazer o teste, sair e entrar de novo (persistência);
    - no SQL Editor: `select count(*) from usuarios;` etc. Só depois disso arquive o SQLite.

## 5. Como testar localmente

```bash
# Backend — PostgreSQL local (ex.: `supabase start`, ou um Postgres 15+ com unaccent/pg_trgm)
pip install -r requirements-dev.txt
export TEST_DATABASE_URL=postgresql://postgres:<senha>@localhost:5432/postgres
# opcional: a aplicação usa o papel restrito (prova que RLS/GRANTs bastam)
export TEST_DATABASE_APP_USER=suafacul_backend TEST_DATABASE_APP_PASSWORD=<senha>
pytest -q
```

Mobile (`suafaculMobile/scripts/e2e`): ver `README_API.md` — roda a camada de API real do app
contra o backend real.

Resultados nesta migração (PostgreSQL 16, papel restrito): **417 testes do backend**, **35/35 no
e2e do Mobile** (incluindo renovação automática do token e revogação no logout), **23/23 no teste
da web em navegador** (páginas, cadastro, favoritos, dashboard, bloqueio do admin para aluno,
CRUD admin) e **126 testes do app TypeScript**. Migração de um SQLite gerado pela versão anterior
do app: todas as linhas e ids preservados, login com a senha antiga funcionando, arquivo de origem
inalterado (hash conferido).

## 6. Reversão

O código anterior (SQLite) está no histórico do Git. O banco antigo não é alterado pela migração;
para voltar, faça o deploy do commit anterior com o arquivo SQLite original.
