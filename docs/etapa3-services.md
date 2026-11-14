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
- O template gera o formulário a partir do backend (`teste_vocacional_service.perguntas_formulario()`); o
  `value` de cada opção são os perfis que ela pontua (`"tecnico,cientifico"`), e a página envia as respostas
  para `POST /api/teste_vocacional/salvar` (`respostas_json`).
- `POST /api/teste_vocacional/responder` e `POST /api/v1/teste-vocacional/resultados` recebem o id da opção
  (`{q1:'a',…}`) e devolvem perfis, áreas e cursos sugeridos.
- **Pontuação com implementação única (auditoria 2026-11):** os três fluxos chamam
  `teste_vocacional_service.calcular(respostas, formato='id'|'valor')`, que converte as respostas na
  alternativa do questionário (`resolver_respostas`) e aplica a única regra (`pontuar`: +1 por perfil listado
  na alternativa; perfis principais = maior pontuação > 0, na ordem `ORDEM_PERFIS`). Antes, `/salvar` usava
  uma cópia da regra em `vocacional_service.calcular_pontuacao` (removida, junto com `validar_respostas`).
  Em cada pergunta id e valor são únicos, então os dois formatos levam à mesma alternativa e à mesma
  pontuação — conferido de forma exaustiva (384 000 combinações) em `tests/test_auditoria_integridade.py`.
  `vocacional_service` ficou só com a compatibilidade com cursos (afinidades e recomendações).
- Contratos preservados: `/salvar` continua respondendo 400 com as mesmas mensagens ("Responda todas as
  perguntas do teste.", "Resposta inválida na pergunta N.") e gravando `respostas_json` no formato valor;
  `/responder` e a API v1 mantêm seus formatos. O ramo legado de `/salvar` sem `respostas_json` (cliente que
  envia `perfil_principal`/`perfis_json` prontos) segue aceito por compatibilidade, com a validação de antes.
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
