# SuaFacul

Plataforma web para ajudar estudantes a encontrar faculdades, cursos e
vestibulares — com um painel administrativo para gerenciar esses dados,
incluindo importação automatizada de instituições a partir do e-MEC.

Backend em **Flask + SQLite**, frontend em **HTML/CSS/JS puro** (sem
framework de frontend), servido pelo próprio Flask via Jinja2.

## Requisitos

- Python 3.8+

## Instalação

```bash
pip install -r requirements.txt        # runtime
pip install -r requirements-dev.txt    # + pytest (desenvolvimento)
```

## Executar

```bash
python run.py          # desenvolvimento: inicializa o banco, seed e agendador
```

O import do app não tem efeitos colaterais (`create_app()` em
`app/factory.py`). O entrypoint WSGI é `wsgi.py` (Vercel, gunicorn,
`flask --app wsgi init-db`).

Acesse em: **http://localhost:5000**

O banco SQLite (`database/suafacul.db`) é criado e populado automaticamente
na primeira execução — não precisa rodar nenhum script à parte. Isso vale
tanto para uma instalação nova quanto para atualizar um banco já existente
(as migrações rodam de forma segura a cada start, sem apagar dados).

### Primeiro administrador

Não existe usuário/senha padrão. Em um banco sem nenhum admin, defina no
ambiente (ver `.env.example`) antes de subir o app:

```
SUAFACUL_ADMIN_USER=admin
SUAFACUL_ADMIN_PASSWORD=<senha forte>
```

O admin é criado uma única vez; sem `SUAFACUL_ADMIN_PASSWORD` nenhum admin é
criado (o log avisa). Se um admin antigo ainda usar a senha `admin123`, o app
avisa no log a cada início — troque-a em Dashboard → Editar Perfil.

**Na Vercel, defina `SUAFACUL_ADMIN_PASSWORD`** em Project Settings →
Environment Variables. Lá o banco SQLite fica em `/tmp` e é recriado a cada
inicialização, então trocar a senha pelo painel não persiste — a senha que
vale é sempre a da variável.

### Desenvolvimento local

O modo debug agora é **desligado por padrão**. Para desenvolvimento local,
coloque `FLASK_DEBUG=1` no seu `.env` (recarga automática, chave de sessão
efêmera se `FLASK_SECRET_KEY` faltar). Fora do debug, `FLASK_SECRET_KEY` é
obrigatória e o cookie de sessão é `Secure` (defina `SESSION_COOKIE_SECURE=0`
se rodar sem HTTPS e sem debug). Detalhes em `docs/seguranca-etapa0.md`.

## Estrutura

```
suafacul-main/
├── wsgi.py                     # Entrypoint WSGI (produção/Vercel) — sem efeitos colaterais
├── run.py                      # Servidor de desenvolvimento (init do banco + seed + agendador)
├── requirements.txt / requirements-dev.txt
├── config/
│   └── database.py             # Conexão SQLite
├── database/
│   └── init_db.py              # Cria tabelas, popula dados iniciais e migra bancos já existentes
├── app/
│   ├── factory.py / settings.py / security.py / bootstrap.py / cli.py
│   ├── api/v1/                 # API v1 (contrato do Mobile): rotas, DTOs, OpenAPI
│   ├── routes/                 # Blueprints do site (páginas + API legada): pages, auth_google, api_usuario, api_catalogo, api_vestibulares, api_favoritos, api_teste_vocacional, api_admin, api_v1
│   ├── models/                 # Usuario, Curso, Faculdade, Vestibular, Favorito, TesteVocacional
│   ├── services/
│   │   ├── emec_service.py     # Instituições: CSV oficial (Dados Abertos MEC) como fonte primária, scraping do e-MEC como fallback
│   │   ├── censo_service.py    # Cursos: importação do Censo da Educação Superior (INEP)
│   │   ├── vestibular_service.py  # Validação automática de datas/vínculo dos vestibulares
│   │   ├── oauth_service.py    # Login com Google (Authlib/OIDC)
│   │   ├── automacao_service.py   # Execução das automações (Cron/CLI): trava, log, jobs
│   │   └── seed_service.py     # Autopopula o banco a partir de data/seeds/ num deploy novo
│   └── templates/
│       ├── partials/_header.html  # Header único, reutilizado por todas as páginas
│       ├── partials/_footer.html  # Footer único, reutilizado por todas as páginas
│       └── *.html              # Uma página por rota (home, cursos, faculdades, vestibulares, admin, dashboard...)
├── data/
│   └── seeds/                  # CSVs de seed automático (não versionados — ver seção "Seed automático")
├── tests/                      # Suíte pytest (ver seção "Testes")
└── public/
    ├── css/
    │   ├── base.css             # Tokens de marca, reset, tipografia e componentes compartilhados (modal, form, botões)
    │   ├── components/          # header.css, footer.css, curso-autocomplete.css — componentes únicos reutilizados
    │   └── pages/                  # CSS específico de cada página
    ├── js/                      # Um arquivo JS por página + header.js, favoritos.js e curso-autocomplete.js (compartilhados)
    └── imagens/
```

## Papéis de usuário (admin / aluno)

Todo usuário tem um `tipo`: `aluno` (padrão) ou `admin`. Rotas e endpoints
administrativos são protegidos tanto na navegação (`/admin` redireciona
quem não é admin) quanto na API (endpoints retornam 403 para quem não é
admin) — a validação nunca depende só do frontend. Um admin pode promover
outros usuários pela própria tela de Admin → Usuários.

## Painel administrativo (`/admin`)

- **Usuários** — listar, editar, promover/rebaixar tipo, excluir.
- **Faculdades** — CRUD manual, ou importar do e-MEC:
  - por código de uma instituição específica;
  - por UF (todas as instituições em atividade daquele estado);
  - Brasil inteiro (percorre as 27 UFs, com intervalo entre requisições).
- **Vestibulares** — botão que valida automaticamente se as datas ainda
  estão no futuro e se a instituição de cada vestibular já está cadastrada
  em Faculdades.
- **Dashboard de estatísticas** — contagem de usuários, cursos, faculdades
  e vestibulares em tempo real.

> O e-MEC não tem API REST oficial — a importação usa o mesmo endpoint
> interno de consulta que o próprio site do e-MEC utiliza. Por isso pode
> falhar ou ficar lento se o e-MEC estiver instável; dados como
> telefone/e-mail de contato não vêm nessa importação e ficam para
> completar manualmente.

## Principais endpoints da API

| Recurso | Endpoints |
|---|---|
| Usuários | `POST /api/usuario/registrar`, `login`, `logout`, `listar`, `buscar`, `atualizar`, `definir-tipo`, `deletar` |
| Login com Google | `GET /auth/google`, `/auth/google/callback` |
| Cursos | `GET /api/cursos/listar`, `buscar`, `sugestoes` (autocomplete); `POST /api/cursos/criar`, `censo/importar-csv` |
| Faculdades | `GET /api/faculdades/listar` (filtros: `busca`, `cidade`, `uf`, `tipo_instituicao`, `curso`, `modalidade`), `buscar`; `POST criar`, `atualizar`, `deletar`, `emec/importar`, `emec/importar-uf`, `emec/importar-csv`, `emec/importar-brasil` |
| Vestibulares | `GET /api/vestibulares/listar` (filtros: `tipo_instituicao`, `regiao`, `mes`, `busca`, `curso`), `buscar`, `validar`; `POST criar` |
| Favoritos | `POST adicionar`/`remover`; `GET listar`, `verificar`, `listar-ids` |
| Admin | `GET /api/admin/stats` |
| Teste vocacional | `GET /api/teste_vocacional/perguntas`; `POST /api/teste_vocacional/responder` (pontuação no servidor). `salvar` está *deprecated* — ver `docs/etapa3-services.md` |
| API v1 (Mobile / externa) | `/api/v1/*` — catálogo, busca, teste vocacional, favoritos, perfil e dashboard. Contrato: `GET /api/v1/openapi.json` · guias: `docs/etapa4-api-v1.md`, `docs/etapa5-auth-mobile.md` (login por e-mail, access 15 min + refresh rotativo 30 dias) |

Endpoints marcados como administrativos exigem sessão de admin (retornam
`403` caso contrário).

## Modelo de dados

`usuarios` (com `tipo`) · `faculdades` · `cursos` (linkado a `faculdades`
por `faculdade_id`) · `vestibulares` (linkado a `faculdades`, com
`status_validacao`/`cadastrado_ok` preenchidos pela automação de
validação) · `favoritos` · `teste_vocacional_resultados` ·
`vestibular_inscricoes`.

## Design system

Todas as páginas compartilham o mesmo header (`partials/_header.html` +
`components/header.css` + `header.js`) e o mesmo rodapé
(`partials/_footer.html` + `components/footer.css`), além dos mesmos
tokens de marca, tipografia e componentes de UI (`base.css`) — botões,
badges, alertas, modais e formulários seguem um padrão único em vez de
serem redefinidos por página.

## Login com Google

Login/registro via Google (OpenID Connect), além do login local. Requer
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `GOOGLE_CALLBACK_URL` no
`.env` (ver `.env.example`) — credenciais criadas em
[console.cloud.google.com](https://console.cloud.google.com/) > APIs &
Services > Credentials > OAuth client ID > Web application, com a
`GOOGLE_CALLBACK_URL` cadastrada em "Authorized redirect URIs". Sem essas
variáveis configuradas, o app continua funcionando normalmente — só o
login com Google fica desabilitado (erro amigável, não quebra o site).

Contas são vinculadas por e-mail **apenas quando o Google confirma que o
e-mail é verificado**, para não permitir que alguém tome conta de uma
conta local existente com um e-mail não confirmado.

## Segurança da conta e e-mail

Verificação de e-mail por código, recuperação de senha, troca de e-mail com
confirmação, limites contra força bruta e login com Google no app: regras,
endpoints, variáveis (`EMAIL_MODO`, `SMTP_*`, `EMAIL_REMETENTE`) e o passo a
passo do Gmail (senha de app) e do Google Cloud (cliente Android + SHA-1) em
[docs/etapa8-seguranca-conta.md](docs/etapa8-seguranca-conta.md).

## Automações (Vercel Cron)

Em produção (Vercel) as automações rodam por **Vercel Cron**, que chama por GET
`/api/cron/<job>` com `Authorization: Bearer <CRON_SECRET>` (sem `CRON_SECRET`
os endpoints ficam desligados). Agendamentos em `vercel.json` (UTC; compatíveis
com o plano Hobby, 1x/dia):

| Job | Horário (UTC) | O que faz |
|---|---|---|
| `validacao-vestibulares` | 06:00 (03:00 Brasília) | reavalia status (ativo/encerrado/data inválida) e vínculo com faculdades |
| `limpeza-refresh-tokens` | 06:30 | apaga refresh tokens expirados há mais de 7 dias |

Cada execução tem um `execucao_id`, estado (sucesso/falha/ignorada), origem, duração e erro
em `automacao_logs`; há trava contra execução concorrente e janela anti-duplicata.
Localmente: `flask --app wsgi executar-automacao validacao-vestibulares [--forcar]`.
Detalhes e limites da Vercel: `docs/etapa6-cron.md`.

## Dados de instituições (e-MEC) — por que não é consulta em tempo real

O e-MEC (`emec.mec.gov.br`) **não tem API pública oficial** e fica atrás
de uma proteção que bloqueia com `403 Forbidden` chamadas automatizadas
(scripts, `requests` do Python) mesmo com headers de navegador — isso
inclui, às vezes, até o CSV oficial hospedado em outro portal do MEC. Por
isso o site **não consulta o e-MEC ao vivo a cada busca do usuário**: ele
consulta sempre a própria base local (`faculdades`), populada
periodicamente.

**Como alimentar a base:**
1. **Recomendado — upload manual do CSV oficial.** Baixe o CSV de
   "Instituições de Educação Superior do Brasil" em
   [dadosabertos.mec.gov.br/indicadores-sobre-ensino-superior](https://dadosabertos.mec.gov.br/indicadores-sobre-ensino-superior)
   pelo navegador (funciona — o bloqueio é só para chamadas de servidor) e
   suba o arquivo em **Admin → Faculdades → Importar CSV oficial**. Importa
   o Brasil inteiro de uma vez, sem nenhuma chamada ao e-MEC.
2. **Best-effort — download automático.** Os botões "Importar do e-MEC" /
   "Importar todas as IES da UF" tentam baixar automaticamente (primeiro o
   CSV oficial, depois scraping do e-MEC como último recurso). Podem
   funcionar dependendo de onde o servidor está hospedado (o bloqueio
   observado parece ser por faixa de IP/fingerprint de rede, não algo
   universal) — trate como bônus, não como caminho garantido.

Cursos de graduação são importados do Censo da Educação Superior (INEP)
— ver seção abaixo — ou cadastrados manualmente pelo admin quando não
vierem do Censo.

## Importar cursos do Censo da Educação Superior (INEP)

Além das instituições, dá pra importar os cursos de graduação de cada
uma a partir do arquivo oficial `MICRODADOS_CADASTRO_CURSOS_<ano>.CSV`
(dentro do ZIP do Censo, em
[gov.br/inep](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior)).
Em **Admin → Faculdades → Importar cursos (Censo INEP)**, suba esse
arquivo (~400MB, processado em streaming — não precisa dar zoom, o
upload leva um tempo mas funciona).

Só importa cursos de instituições **já cadastradas** localmente (casa
pelo código e-MEC/`CO_IES`) — importe as instituições primeiro. O
mesmo curso aparece várias vezes no arquivo oficial (uma vez por polo de
EAD); o importador deduplica automaticamente por curso, não por linha.

## Seed automático (evita reimportar manualmente em cada deploy)

Os dados importados ficam salvos no `database/suafacul.db` e **persistem
entre reinícios normais** (mesma máquina) — não é preciso reimportar
toda vez que reinicia o servidor.

Só é preciso reimportar quando o **banco é recriado do zero** (deploy
num servidor novo, ambiente de CI, etc.). Pra automatizar isso: depois
de importar uma vez pelo admin, copie os dois arquivos originais que
você baixou para:

```
data/seeds/instituicoes.csv   (o CSV de instituições do MEC)
data/seeds/cursos.csv         (o MICRODADOS_CADASTRO_CURSOS_<ano>.CSV do INEP)
```

Esses dois nomes exatos, nessa pasta. Na próxima vez que o app subir com
um banco sem nenhuma importação real ainda feita, ele se autopopula
sozinho a partir desses arquivos — sem precisar clicar em nada no admin
(`app/services/seed_service.py`, chamado por `python run.py`, por
`flask --app wsgi init-db` e, na Vercel, pelo `wsgi.py`). Idempotente: se os dados já foram importados antes (seed
anterior ou upload manual), não reimporta por cima.

Esses CSVs **não vão para o Git** (`data/seeds/*.csv` está no
`.gitignore`, junto do `.env`) — copie/leve junto do deploy como
qualquer outro dado específico do ambiente.

## Pesquisa dinâmica e autocomplete

Na home e em `/faculdades`, os filtros (curso, faculdade, cidade,
modalidade, tipo de instituição) já disparam a busca sozinhos ao mudar —
texto com debounce (~450ms), checkboxes/radios na hora — sem precisar
clicar em "Buscar" ou apertar Enter (`public/js/faculdades.js`). Usa a
mesma `GET /api/faculdades/listar` de sempre; um contador de requisição
evita que uma resposta antiga (fora de ordem) sobrescreva um resultado
mais novo.

O campo "curso" tem autocomplete (`public/js/curso-autocomplete.js` +
`components/curso-autocomplete.css`, componente único injetado em
qualquer `.text-input[placeholder*="curso"]` da página — funciona igual
na home e em `/faculdades`): digitar "Engenharia" sugere os nomes de
curso já cadastrados que começam com esse termo (`GET
/api/cursos/sugestoes?q=...`), navegável por ↑↓/Enter/Esc. Selecionar uma
sugestão preenche o campo e dispara a busca automaticamente.

## Testes

```bash
pytest tests/
```

Cada teste roda contra um banco SQLite temporário isolado (não usa nem
mexe no `database/suafacul.db` de desenvolvimento). Cobre autenticação
(local e Google, com mocks — sem chamar o Google de verdade), busca de
faculdades/cursos, autocomplete, footer, a automação diária de
vestibulares, importação e-MEC/Censo e o seed automático.

## API própria (v1)

Toda consulta de instituições — pelo site e por qualquer consumidor
externo — passa por esta API, que lê da base local (nunca do e-MEC
diretamente). Pública, somente leitura, sem autenticação.

| Endpoint | Descrição |
|---|---|
| `GET /api/v1/instituicoes` | Lista, com filtros `uf`, `cidade`, `tipo_instituicao`, `busca` e paginação `page`/`limit` (máx. 100) |
| `GET /api/v1/instituicoes/<codigo_emec>` | Detalhe de uma instituição |

Resposta no formato `{"data": ..., "meta": {...}}` (listagem) ou
`{"data": {...}}` (detalhe); `404` com `{"error": ...}` quando não
encontrado.


## Deploy na Vercel

- Entrypoint: `wsgi.py` (configurado em `pyproject.toml` → `[tool.vercel] entrypoint`), que cria o app por `app/factory.py` e, na Vercel, inicializa o banco. Localmente: `python run.py`.
- Banco: na Vercel o código fica em disco somente leitura; o SQLite é criado em `/tmp/suafacul.db` (detectado pela variável `VERCEL`). **Esse arquivo é temporário**: some quando a instância é reciclada e não é compartilhado entre instâncias. Para dados permanentes (usuários, favoritos) em produção é preciso um banco externo.
- Automações diárias: na Vercel rodam via Vercel Cron (`vercel.json` → `/api/cron/validacao-vestibulares` às 06:00 UTC = 03:00 em São Paulo e `/api/cron/limpeza-refresh-tokens`), protegidas por `CRON_SECRET` (detalhes em `docs/etapa6-cron.md`).
- Variáveis em *Settings → Environment Variables*: `FLASK_SECRET_KEY`, `CRON_SECRET` e, para login com Google, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_CALLBACK_URL` (https do domínio da Vercel).
