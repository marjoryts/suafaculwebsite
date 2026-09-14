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
pip install -r requirements.txt
```

## Executar

```bash
python app.py
```

Acesse em: **http://localhost:5000**

O banco SQLite (`database/suafacul.db`) é criado e populado automaticamente
na primeira execução — não precisa rodar nenhum script à parte. Isso vale
tanto para uma instalação nova quanto para atualizar um banco já existente
(as migrações rodam de forma segura a cada start, sem apagar dados).

### Login padrão

Se nenhum usuário administrador existir ainda, um é criado automaticamente
no primeiro start:

```
usuário: admin
senha:   admin123
```

**Troque essa senha assim que entrar** (Dashboard → Editar Perfil).

## Estrutura

```
suafacul-main/
├── app.py                      # Aplicação Flask: rotas de página + API REST
├── requirements.txt
├── config/
│   └── database.py             # Conexão SQLite
├── database/
│   └── init_db.py              # Cria tabelas, popula dados iniciais e migra bancos já existentes
├── app/
│   ├── models/                 # Usuario, Curso, Faculdade, Vestibular, Favorito, TesteVocacional
│   ├── services/
│   │   ├── emec_service.py     # Importação de instituições a partir do e-MEC (por código ou por UF)
│   │   ├── vestibular_service.py  # Validação automática de datas/vínculo dos vestibulares
│   │   └── oauth_service.py    # Login com Google (Authlib/OIDC)
│   └── templates/
│       ├── partials/_header.html  # Header único, reutilizado por todas as páginas
│       └── *.html              # Uma página por rota (home, cursos, faculdades, vestibulares, admin, dashboard...)
└── public/
    ├── css/
    │   ├── base.css             # Tokens de marca, reset, tipografia e componentes compartilhados (modal, form, botões)
    │   ├── components/header.css   # Header/navbar único
    │   └── pages/                  # CSS específico de cada página
    ├── js/                      # Um arquivo JS por página + header.js (menu mobile) e favoritos.js (compartilhado)
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
| Cursos | `GET /api/cursos/listar`, `buscar`, `sugestoes` (autocomplete); `POST /api/cursos/criar` |
| Faculdades | `GET /api/faculdades/listar` (filtros: `busca`, `cidade`, `uf`, `tipo_instituicao`, `curso`, `modalidade`), `buscar`; `POST criar`, `atualizar`, `deletar`, `emec/importar`, `emec/importar-uf`, `emec/importar-brasil` |
| Vestibulares | `GET /api/vestibulares/listar` (filtros: `tipo_instituicao`, `regiao`, `mes`, `busca`, `curso`), `buscar`, `validar`; `POST criar` |
| Favoritos | `POST adicionar`/`remover`; `GET listar`, `verificar`, `listar-ids` |
| Admin | `GET /api/admin/stats` |
| Teste vocacional | `POST /api/teste_vocacional/salvar` |
| API própria (v1) | `GET /api/v1/instituicoes`, `/api/v1/instituicoes/<codigo_emec>`, `/api/v1/instituicoes/<codigo_emec>/cursos` — ver seção própria abaixo |

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
`components/header.css` + `header.js`) e os mesmos tokens de marca,
tipografia e componentes de UI (`base.css`) — botões, badges, alertas,
modais e formulários seguem um padrão único em vez de serem redefinidos
por página.

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

## Pesquisa dinâmica e autocomplete

Na home e em `/faculdades`, os filtros (curso, faculdade, cidade,
modalidade, tipo de instituição) já disparam a busca sozinhos ao mudar —
texto com debounce (~450ms), checkboxes/radios na hora — sem precisar
clicar em "Buscar" ou apertar Enter (`public/js/faculdades.js`). Usa a
mesma `GET /api/faculdades/listar` de sempre; um contador de requisição
evita que uma resposta antiga (fora de ordem) sobrescreva um resultado
mais novo.

O campo "curso" tem um endpoint de autocomplete pronto
(`GET /api/cursos/sugestoes?q=...`, retorna nomes de curso já cadastrados
que começam com o termo digitado) — ainda sem um componente de frontend
consumindo ele.

## API própria (v1)

Toda consulta de instituições — pelo site e por qualquer consumidor
externo — passa por esta API, que lê da base local (nunca do e-MEC
diretamente). Pública, somente leitura, sem autenticação.

| Endpoint | Descrição |
|---|---|
| `GET /api/v1/instituicoes` | Lista, com filtros `uf`, `cidade`, `tipo_instituicao`, `busca` e paginação `page`/`limit` (máx. 100) |
| `GET /api/v1/instituicoes/<codigo_emec>` | Detalhe de uma instituição |
| `GET /api/v1/instituicoes/<codigo_emec>/cursos` | Cursos de graduação cadastrados para essa instituição |

Resposta no formato `{"data": ..., "meta": {...}}` (listagem) ou
`{"data": {...}}` (detalhe); `404` com `{"error": ...}` quando não
encontrado.
