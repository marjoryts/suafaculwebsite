# Etapa 3 — Camada de Services

Objetivo: regras de negócio fora de rotas, templates e JavaScript, para que
Web, API v1 (Mobile), CLI e automações usem o **mesmo código**.

```
Web (Jinja/JS) ─┐
API v1 (Mobile)─┼─► rotas (HTTP/sessão/token) ─► services (regras) ─► models (SQL) ─► config/database.py
CLI / Cron ─────┘
```

## Services (`app/services/`)

| Service | Regras que passaram a viver aqui | Antes |
|---|---|---|
| `teste_vocacional_service` + `teste_vocacional_dados` | questionário, pesos, pontuação, empate, persistência, cursos sugeridos, histórico com percentuais | perguntas/pesos no HTML, pontuação e áreas no JS; cliente enviava o resultado pronto |
| `usuario_service` | validação de e-mail/senha, mensagem única de login, regras "não remover o próprio admin / não excluir a própria conta", conflito de nome/e-mail | dentro das rotas (e dependendo do texto de erro do SQLite) |
| `favorito_service` | tipos válidos, `item_id` válido | dentro das rotas (`int()` sem proteção → HTTP 500) |
| `dashboard_service` | resumo do painel do usuário | montado dentro da rota `/dashboard` |
| `paginacao` | `page`/`limit`/`total_pages` | copiado em 4 rotas; `?page=abc` → HTTP 500 |
| `erros` | `ErroDeNegocio` (+ `ValidacaoError`, `NaoEncontradoError`, `PermissaoNegadaError`) | — |
| já existentes | `vestibular_service`, `busca_service`, `emec_service`, `censo_service`, `seed_service` | (Etapa 2 tirou o SQL deles) |

Services levantam `ErroDeNegocio`; cada camada de entrada traduz:
- API legada `/api/*`: `HTTP 200 {"success": false, "message": ...}` (contrato preservado; ver `app/factory.py`).
- API v1 (Etapa 4): envelope estruturado `{"error": {"code", "message", "request_id"}}` usando `code`/`status` da exceção.

## Teste vocacional
- Fonte única: `app/services/teste_vocacional_dados.py` (10 perguntas, 39 opções, 6 perfis).
  A transcrição foi conferida contra o HTML original (texto, ordem, opções e pesos: idêntica).
- O template gera o formulário a partir do backend ({% raw %}`{% for secao in secoes %}`{% endraw %}); o valor de cada opção
  agora é um id (`a`, `b`, …) em vez das tags de perfil.
- Novos endpoints: `GET /api/teste_vocacional/perguntas` e `POST /api/teste_vocacional/responder`
  (`{q1:'a',…}` → perfis, áreas, cursos sugeridos; salva o resultado). **O servidor calcula tudo**: pontuação
  enviada pelo cliente é ignorada.
- `POST /api/teste_vocacional/salvar` está **deprecated** (mantido por compatibilidade) e agora valida o perfil e a pontuação.
- `public/js/testevocacional.js` ficou só com apresentação (e passou a montar o resultado com `textContent`,
  não `innerHTML`, para não injetar nomes de cursos vindos do banco como HTML).

## CLI (`flask --app wsgi …`) — CLI → service → banco
`init-db`, `importar-instituicoes ARQUIVO.csv`, `importar-cursos ARQUIVO.csv`, `validar-vestibulares [--aplicar]`.
Cada execução é registrada em `automacao_logs` (sucesso, resumo ou erro). A CLI não tem lógica de importação:
chama os mesmos services que hoje a rota de admin usa, e que uma fila/Workflow poderá usar no futuro.

## Pendências conhecidas (não são regressões)
- Favoritos não verificam se o item existe nem derivam `nome_item` do banco (mantido por paridade) → tratar na API v1.
- Rotas de importação do admin continuam síncronas (limite de 4,5 MB / duração na Vercel) → usar a CLI; futura fila.
- Models ainda devolvem `{'success': False, 'message': 'Erro: <exceção>'}` em falha de banco (vaza detalhe) → envelope de erros da API v1.
