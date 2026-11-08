# Etapa 4 — API v1 (contrato oficial do Mobile)

Contrato completo e sempre atualizado: **`GET /api/v1/openapi.json`** (OpenAPI 3.0.3;
o teste `test_openapi_descreve_todas_as_rotas` garante que ele cobre todas as rotas).

## Convenções
| | |
|---|---|
| Sucesso | `{"data": ..., "meta": ...}` |
| Listas paginadas | `?page=1&limit=20` (máx. 100); `meta = {total, page, limit, total_pages}`; valores inválidos viram o padrão |
| Erro | `{"error": {"code", "message", "request_id", "details"?}}` |
| Códigos | `BAD_REQUEST, UNAUTHENTICATED, FORBIDDEN, RESOURCE_NOT_FOUND, METHOD_NOT_ALLOWED, UNSUPPORTED_MEDIA_TYPE, VALIDATION_ERROR, INTERNAL_ERROR` |
| Request ID | Toda resposta (do site inteiro) traz `X-Request-ID`; o cliente pode enviar o seu (`[A-Za-z0-9._-]{1,64}`) |
| Corpo | Requisições `POST/PUT/PATCH` com corpo exigem `Content-Type: application/json` (415 caso contrário) |
| Cache | Endpoints públicos: `Cache-Control: public, max-age=60, s-maxage=300`. Endpoints autenticados/erros: `no-store` |
| 5xx | Mensagem genérica; nunca stack trace, SQL ou detalhe interno |

## Endpoints (todos sob `/api/v1`)

Público
| Método | Caminho | Descrição |
|---|---|---|
| GET | `/cursos` · `/cursos/{id}` | lista (`area, busca, modalidade[], tipo_instituicao[]`) e detalhe |
| GET | `/faculdades` · `/faculdades/{id}` | lista (`tipo_instituicao, uf, cidade, curso, busca, modalidade[]`) e detalhe (com cursos e vestibulares) |
| GET | `/vestibulares` · `/vestibulares/{id}` | lista (`tipo_instituicao, regiao, busca, curso, mes[], incluir_privados`) e detalhe (`status`) |
| GET | `/busca/sugestoes` | autocomplete `q, tipos, limite` → `{local, faculdade, curso}` |
| GET | `/instituicoes` · `/{codigo_emec}` · `/{codigo_emec}/cursos` | API por código e-MEC (existente; agora com envelope de erro) |
| GET | `/teste-vocacional/perguntas` | questionário (sem os pesos) |
| POST | `/teste-vocacional/resultados` | `{"respostas": {"q1": "a", …}}` → resultado calculado no servidor (201). Com usuário autenticado entra no histórico |
| GET | `/openapi.json` | este contrato |

Autenticado (`Authorization: Bearer <access_token>` — ver `docs/etapa5-auth-mobile.md`)
| Método | Caminho | Descrição |
|---|---|---|
| GET | `/me` | perfil |
| PATCH | `/me` | `nome_usuario, email, password+password_confirm` (qualquer `tipo` é rejeitado com 422) |
| GET | `/me/dashboard` | contagem de favoritos, próximas provas, favoritos recentes, testes |
| GET | `/favoritos?tipo=` | lista |
| PUT | `/favoritos/{tipo}/{item_id}` | favorita (idempotente: 201 criou / 200 já existia; 404 se o item não existe; nome vem do banco) |
| DELETE | `/favoritos/{tipo}/{item_id}` | desfavorita (idempotente, 204) |
| GET | `/teste-vocacional/resultados` | histórico do usuário |

Não há endpoints administrativos na v1 (teste `test_v1_nao_tem_endpoints_administrativos`).

## Decisões
- **Reuso, sem duplicar regra:** as rotas chamam os mesmos services da Web (`usuario_service`,
  `favorito_service`, `teste_vocacional_service`, `dashboard_service`, `busca_service`, `paginacao`).
  Novo só o que a API precisa: `favoritar/desfavoritar` (idempotente, valida existência) e `nome_por_id` nos models.
- **DTOs** (`app/api/v1/serializers.py`): nunca se devolve linha do banco (sem `codigo_inep_curso`, `fonte`,
  `cadastrado_ok`, `updated_at`, `senha`…).
- **Erros centralizados** (`app/errors.py`): o mesmo `ErroDeNegocio` vira envelope na v1 e o formato
  `{success:false}` na API legada — o frontend Web não muda.
- **Autenticação isolada em `app/api/v1/auth.py`** (`usuario_atual`). Na Etapa 4 usava o cookie de sessão; a Etapa 5 a trocou por
  Bearer (o cookie deixou de autenticar a API). Sempre consulta o banco (conta removida perde acesso na hora).
- **Corpo só como JSON** (415 caso contrário) — contrato único e defesa em profundidade.
- **Mudança de contrato existente:** os erros de `/api/v1/instituicoes*` eram `{"error": "texto"}` e agora seguem o
  envelope (a chave `error` continua existindo, mas passa a ser um objeto). Sucessos não mudaram.

## Pendências (fora do escopo desta etapa)
- ~~Autenticação Bearer/refresh~~ → feita na Etapa 5 (e-mail + senha). Login Google para mobile: não implementado.
- Sem rate limiting (decisão de armazenamento compartilhado adiada; ver `docs/seguranca-etapa0.md`).
- `PATCH /me` com senha não pede a senha atual (mesma regra da Web). Ao trocar a senha, as outras sessões do app são encerradas.
