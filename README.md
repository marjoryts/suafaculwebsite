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
│   │   └── vestibular_service.py  # Validação automática de datas/vínculo dos vestibulares
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
| Cursos | `GET /api/cursos/listar`, `buscar`; `POST /api/cursos/criar` |
| Faculdades | `GET /api/faculdades/listar` (filtros: `busca`, `cidade`, `uf`, `tipo_instituicao`, `curso`, `modalidade`), `buscar`; `POST criar`, `atualizar`, `deletar`, `emec/importar`, `emec/importar-uf`, `emec/importar-brasil` |
| Vestibulares | `GET /api/vestibulares/listar` (filtros: `tipo_instituicao`, `regiao`, `mes`, `busca`, `curso`), `buscar`, `validar`; `POST criar` |
| Favoritos | `POST adicionar`/`remover`; `GET listar`, `verificar`, `listar-ids` |
| Admin | `GET /api/admin/stats` |
| Teste vocacional | `POST /api/teste_vocacional/salvar` |

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
