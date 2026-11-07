# Etapa 7 — App mobile (Expo Router): estado e lacunas

Guia de uso do app: `mobile/README.md`. Decisões do proprietário: Expo Router; abas **Explorar | Salvos | Perfil**
(Cursos/Faculdades/Vestibulares/Teste vocacional dentro de Explorar); **login obrigatório**; Google **desabilitado**
(ponto de extensão); o design de referência é o Figma (arquivo `HhMYIH3w5TqKBUE9o40rY0`, página "Mobile").

## Feito
- Backend (aditivo, compatível com a Web): `GET /favoritos` e `PUT /favoritos/{tipo}/{id}` trazem `item` (resumo do
  curso/faculdade/vestibular, em **uma consulta por tipo**, sem N+1; `null` se o item foi removido); os
  `cursos_sugeridos` do teste vocacional trazem `id` (abre `GET /cursos/{id}`).
- App: Expo Router (SDK 57), sessão com `expo-secure-store`, login e cadastro funcionais, porteiro de login, abas,
  esqueletos de todas as rotas (incluindo detalhes compartilhados entre Explorar e Salvos), tela "sem conexão".
- Testes: 26 de lógica de sessão/cliente HTTP, 29 de navegação com as rotas reais, 7 de integração com o Flask real.

## Só interface (sem endpoint)
Recuperação de senha · verificação de e-mail · sucesso após alterar senha · botão "Entrar com Google" (desabilitado) ·
introdução e barra de progresso do teste (conteúdo estático/contagem local).

## Lacunas do backend (não improvisadas no app)
| # | Lacuna | Impacto | Estado |
|---|---|---|---|
| 1 | Recuperação de senha (solicitar/confirmar + envio de e-mail) | tela só UI | **não existe** |
| 2 | Verificação de e-mail (envio, confirmação, coluna) | tela só UI | **não existe** |
| 3 | Login Google (endpoint + credenciais Android/iOS) | botão desabilitado | **não existe** |
| 4 | `PATCH /me` troca a senha **sem pedir a senha atual** | se o Figma tiver "senha atual", falta backend; é também uma fragilidade de segurança | existe, incompleto |
| 5 | Filtros dinâmicos (áreas, modalidades, UFs disponíveis) sem endpoint | o app usa as MESMAS listas fixas do site (`mobile/src/catalogo/filtros.ts`) | falta |
| 6 | `vestibulares.periodo_inscricao` é texto livre; só `data_prova` é estruturada (e pode ser vazia); filtro só por mês (sem ano/intervalo) | calendário e "dias restantes até a prova" ok; "dias para inscrever" não | limitação |
| 7 | Sem "destaques/recomendados" para a Home do Explorar | usar as listas existentes | falta |
| 8 | Perfil só tem nome de usuário e e-mail (avatar só do Google) | foto/telefone/cidade não existem | limitação |
| 9 | Detalhes sem logo, nota, mensalidade, mapa, grade curricular | depende do Figma | a confirmar |
| 10 | Login sem limite de tentativas | risco de segurança antes de publicar | pendente |

## Pendências do app
- Ler o Figma e substituir `src/theme/tokens.ts`; classificar frames (tela × estado × componente × modal).
- Telas reais: Home/Busca/listas/detalhes, teste vocacional (introdução → perguntas → resultado → cursos), Salvos, Perfil
  (editar e alterar senha), calendário de vestibulares.
- Ícones das abas e fontes (dependem do Figma). Nenhuma notificação push, tempo real ou Google OAuth (fora do escopo).

## Etapa A — tema e componentes (feito)
Tokens em `mobile/src/theme/tokens.ts` (cores, fontes Inter/Roboto/Darker Grotesque, raios, sombra) extraídos do
Figma; componentes em `mobile/src/components/ui/`. Diferenças conscientes: login só por e-mail (a API v1 não aceita
nome de usuário), cadastro com o campo "Senha" que falta no frame, avatar com a inicial (o 3D do Figma é ilustração),
Perfil sem Modo noturno/Notificações/Ajuda (sem backend).

## Etapa B — catálogo (feito)
| Tela | Frame do Figma | API |
|---|---|---|
| Home do Explorar | Primeira/Segunda Tela Inicial | `GET /faculdades?tipo_instituicao=…`, `GET /cursos`, `GET /favoritos` |
| Busca | (barra de pesquisa da home) | `GET /busca/sugestoes` → local: `/faculdades?cidade=`, curso: `/faculdades?curso=`, faculdade: detalhe |
| Lista de cursos | — (padrão das listas do Figma) | `GET /cursos` (busca, área, modalidade, tipo — mesmos valores do site) |
| Lista de faculdades | — | `GET /faculdades` (busca, tipo, modalidade com "Híbrido"=semipresencial, cidade/UF/região, curso) |
| Detalhe do curso | Cursos | `GET /cursos/{id}` |
| Detalhe da faculdade | Página Faculdades | `GET /faculdades/{id}` (cursos, vestibulares, endereço, contato) |
| Favoritar (coração) | ícone "favorite" | `PUT`/`DELETE /favoritos/{tipo}/{id}` — estado único em `favoritos/FavoritosProvider.tsx` |

Testes: `__tests__/catalogo.test.tsx` (telas), `__tests__/hooks.test.ts` (paginação/formatação) e 3 testes novos de
integração com o Flask real (`INTEGRACAO=1`).

### Lacunas encontradas na Etapa B (não improvisadas no app)
| # | Lacuna | Efeito no app |
|---|---|---|
| 11 | Sem fotos de faculdades/cursos no banco | cards usam os tons de roxo do Figma em vez de fotos |
| 12 | Sem "compatibilidade %", disciplinas e descrição da faculdade | blocos omitidos; os cards de cursos mostram a modalidade |
| 13 | 369 faculdades com cidade/UF gravadas como o texto `"null"` (importação e-MEC) | o app esconde esses valores; o site e as sugestões da busca ainda mostram "null/null" — **corrigir os dados ou o DTO** |
| 14 | Só 11 cursos e 11 vestibulares no banco | listas e seções curtas |
| 15 | Listas de faculdades em ordem alfabética, sem "destaques" | as seções da home mostram as primeiras 8 por ordem alfabética |

## Fase de paridade com o site (Etapas C–G + admin)

### Matriz website × app
| Funcionalidade do site | No app | API usada | Teste |
|---|---|---|---|
| Login e cadastro (e-mail e senha) | sim | `POST /auth/login`, `/auth/registrar` | navegação + integração |
| Login com Google | backend pronto; botão aguarda development build + client ID Android | `POST /auth/google` | 13 testes backend + sessão no app |
| Home: faculdades, cursos, próximos vestibulares, salvos | sim | `/faculdades`, `/cursos`, `/vestibulares`, `/favoritos` | catalogo/vestibulares |
| Busca dinâmica (local, faculdade, curso) | sim | `/busca/sugestoes` | catalogo |
| Cursos: lista, filtros, detalhe | sim | `/cursos`, `/cursos/{id}` | catalogo + integração |
| Faculdades: lista, filtros, detalhe | sim | `/faculdades`, `/faculdades/{id}` | catalogo + integração |
| Vestibulares: calendário, filtros (instituição, regiões, meses, curso), detalhe com taxa/cursos/requisitos/edital | sim | `/vestibulares` (`regiao` repetível), `/vestibulares/{id}` | vestibulares + integração |
| Teste vocacional: uma pergunta por vez, resultado, compatibilidade (%) | sim | `/teste-vocacional/perguntas`, `POST /resultados`, `/recomendacoes` (novo) | testeVocacional + integração |
| Favoritos (cursos, faculdades, vestibulares) | sim | `/favoritos` | perfil + catalogo |
| Painel do aluno (contadores, próximas provas, perfil vocacional) | sim (aba Perfil) | `/me/dashboard` | perfil + integração |
| Editar perfil / trocar senha | sim | `PATCH /me` | perfil + integração |
| Ajuda (FAQ com busca) e Sobre nós | sim (respostas adaptadas ao app) | — (conteúdo) | perfil |
| Admin: indicadores e automações | sim | `GET /admin/estatisticas` (novo) | admin (app + backend) |
| Admin: usuários (criar, editar, tipo, excluir) | sim | `/admin/usuarios` (novo) | admin |
| Admin: faculdades (cadastrar, editar, excluir, importar e-MEC por código/UF/Brasil) | sim | `/admin/faculdades`, `/admin/faculdades/importacoes` (novos) | admin |
| Admin: cursos (cadastrar) | sim | `POST /admin/cursos` (novo) | admin |
| Admin: vestibulares (cadastrar, validar/aplicar) | sim | `/admin/vestibulares`, `/admin/vestibulares/validacao` (novos) | admin |
| Admin: importar CSV do MEC / Censo INEP | **só no site** | — | arquivos de centenas de MB, acima do limite da hospedagem |

Permissões: toda rota `/admin/*` exige Bearer de conta admin, conferida no banco a cada requisição
(aluno: 403; rebaixar um admin tira o acesso na hora). As regras do painel ficam em `app/services/admin_service.py`,
usado pelo site e pelo app.

### Pendências
- **Google no app:** criar o client OAuth Android (nome do pacote + SHA-1) no Google Cloud, definir
  `GOOGLE_ANDROID_CLIENT_ID` no servidor, trocar o pacote `com.anonymous.suafacul`, instalar
  `@react-native-google-signin/google-signin` e gerar um development build (não roda no Expo Go).
- Diferenças de design intencionais: alternativas do teste num estilo único (o Figma desenha uma escala
  Concordo/Discordo que não corresponde às perguntas reais); sem fotos, mapa embutido, lembretes/notificações,
  modo noturno e telefone (sem dados ou fora do escopo).
