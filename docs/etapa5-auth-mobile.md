# Etapa 5 — Autenticação do Mobile (e-mail + senha)

> **Escopo:** somente e-mail e senha. Login Google **não** está implementado e nenhuma credencial
> do Google Cloud foi criada. **Status: desenvolvimento/teste** — ver "Antes de produção".

## Modelo
| | Access token | Refresh token |
|---|---|---|
| Duração | 15 min | 30 dias |
| Formato | assinado (itsdangerous/HMAC com `SECRET_KEY`): `{uid, fam, exp}` | opaco, 48 bytes aleatórios |
| Guardado no servidor | não (mas a **sessão** é conferida no banco a cada uso) | **só o SHA-256** (`refresh_tokens.token_hash`) |
| Uso | `Authorization: Bearer …` | uma única vez, em `/auth/refresh` |

**Sessão = família.** Cada login abre uma família (`familia_id`), um dispositivo = uma sessão. Cada
`/auth/refresh` marca o token usado (`usado_em`) e emite outro da mesma família, na mesma transação.

**Reuso = comprometimento.** Reapresentar um refresh já usado revoga a família inteira
(`motivo_revogacao='reuso_de_refresh_token'`) e responde `REFRESH_TOKEN_REUSED`. O `UPDATE` da rotação é
condicional, então se duas requisições usarem o mesmo token ao mesmo tempo só uma vence; a outra cai no mesmo caminho.

**Revogação imediata.** Como o access token é conferido contra a sessão a cada requisição, logout, reuso,
troca de senha e exclusão de conta cortam o acesso na hora (não só ao fim dos 15 min).

## Endpoints (`/api/v1/auth/*`, públicos, JSON)
| | Corpo | Sucesso | Erros |
|---|---|---|---|
| `POST /auth/registrar` | `nome_usuario, email, password` (≥6) | 201 `{usuario, tokens}` | 409 `CONFLICT`, 422 |
| `POST /auth/login` | `email, password` | 200 `{usuario, tokens}` | 401 `INVALID_CREDENTIALS`, 422 |
| `POST /auth/refresh` | `refresh_token` | 200 `{tokens}` | 401 `INVALID_REFRESH_TOKEN`, `REFRESH_TOKEN_EXPIRED`, `REFRESH_TOKEN_REUSED` |
| `POST /auth/logout` | `refresh_token` | 204 (idempotente) | — |

Resposta 401 das rotas protegidas: `UNAUTHENTICATED` (sem token), `TOKEN_EXPIRED` (renovar com `/auth/refresh`),
`INVALID_TOKEN`; todas com `WWW-Authenticate: Bearer`.

## Como o app deve se comportar
1. Guardar os tokens em armazenamento seguro (Keychain/Keystore — `expo-secure-store`).
2. Em `TOKEN_EXPIRED`: chamar `/auth/refresh` **uma vez** (serializar chamadas simultâneas!) e repetir a requisição.
3. Em `REFRESH_TOKEN_REUSED` / `INVALID_REFRESH_TOKEN` / `REFRESH_TOKEN_EXPIRED`: apagar tokens e ir para o login.
4. Sempre substituir o refresh token guardado pelo devolvido em cada renovação.

## Decisões
- **Cookie não autentica a API.** A v1 aceita só Bearer (tira o CSRF por cookie da equação). O site continua com cookie.
- **Mesma identidade da Web:** a conta criada no app faz login no site e vice-versa (mesma tabela `usuarios`).
- **Login só por e-mail** (nome de usuário não loga na API). Mesma resposta e mesmo custo de tempo para e-mail
  inexistente e senha errada (senha "falsa" verificada quando a conta não existe).
- **Trocar a senha encerra as outras sessões do app** — pela API (preserva a sessão de quem trocou), pelo site ou pelo admin.
- **Pronto para o Google:** `token_service.iniciar_sessao(usuario_id, dispositivo)` não sabe como o usuário foi autenticado.
  Um login Google validado no backend só chamará essa função (teste `test_iniciar_sessao_independe_do_metodo_de_login`).
- **Schema:** uma tabela nova aditiva, `refresh_tokens` (com índices por família e usuário; `ON DELETE CASCADE`).
  Nenhuma tabela existente foi alterada.
- **Prazos** em `app/settings.py` (`ACCESS_TOKEN_TTL_SECONDS`, `REFRESH_TOKEN_TTL_DAYS`).

## Antes de produção (pendências conhecidas)
- **Sem limite de tentativas** em `/auth/login` e `/auth/registrar` (força bruta e criação em massa). Precisa de
  armazenamento compartilhado; decidir antes do lançamento.
- ~~Sem limpeza de refresh tokens~~ → resolvido na Etapa 6 (job `limpeza-refresh-tokens`, ver `docs/etapa6-cron.md`).
- **Retentativa após resposta perdida:** se a rede cair *depois* de o servidor rotacionar e antes de o app receber o novo
  token, a retentativa com o token antigo é vista como reuso e a sessão cai (usuário refaz o login). É o custo do
  comportamento estrito definido; uma janela de tolerância exigiria guardar o token novo ou aceitar risco maior.
- **Uma nova `SECRET_KEY` invalida todos os access tokens** (os refresh continuam válidos). Em debug sem chave a chave é efêmera.
- **Registro revela se e-mail/nome já existe** (409), como qualquer cadastro; o login não revela.
- Sem lista de sessões/"sair de todos os dispositivos" (não há tela para isso ainda).
- `itsdangerous` vem junto com o Flask (não foi adicionada dependência), mas convém fixá-lo em `requirements.txt` no deploy.
