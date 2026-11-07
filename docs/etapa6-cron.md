# Etapa 6 — Automações via Vercel Cron

O APScheduler em processo foi **removido** (não funciona em serverless: a função nasce e morre por
requisição) e o job diário passou a ser chamado pelo Vercel Cron. Importações longas continuam na CLI.

## O que a Vercel garante (documentação consultada em 2026-09; revalidar antes do deploy)
| Fato | Consequência no projeto |
|---|---|
| Chama por **GET** a URL de **produção**; `User-Agent: vercel-cron/1.0`; header `x-vercel-cron-schedule` | Rotas `GET /api/cron/<job>`; não confiamos no User-Agent (falsificável) |
| Envia `Authorization: Bearer <CRON_SECRET>` se a variável existir (recomendado ≥16 caracteres) | Único mecanismo de autenticação; sem segredo (ou <16) o cron fica **desligado** |
| Fuso **sempre UTC**; dia do mês e dia da semana não juntos | `0 6 * * *` = 03:00 em Brasília |
| **Não repete** se falhar; entrega "best effort": pode **perder** e pode **duplicar** uma execução | Jobs idempotentes e reconciliadores (ver abaixo) |
| Pode disparar 2ª instância enquanto a 1ª roda; recomenda lock | Trava no banco (índice único parcial), sem Redis |
| Duração = limites de Functions (Hobby 300 s; Pro 300 s padrão, até 800 s) | Jobs são curtos (ms a segundos) |
| Não segue redirects; rota inexistente = 404 mas ainda "executa" | Rotas sem redirect |
| **Hobby:** no máximo 1x/dia, em qualquer minuto da hora agendada. **Pro:** precisão de minuto | Agendamento diário, funciona nos dois planos (há teste que exige "1x por dia") |

> O plano (Hobby/Pro) ainda não foi escolhido; o desenho funciona em ambos. Pro só permitiria frequência maior.

## Jobs (`app/services/automacao_service.py`, agendados em `vercel.json`)
| Job (URL/CLI) | UTC | Faz | Por que é idempotente |
|---|---|---|---|
| `validacao-vestibulares` | 06:00 | recalcula `status_validacao`, `cadastrado_ok`, `faculdade_id` de todos os vestibulares | o resultado depende só do estado atual e da data de hoje; uma execução perdida é compensada pela seguinte |
| `limpeza-refresh-tokens` | 06:30 | apaga refresh tokens expirados há > 7 dias | `DELETE` pelo mesmo critério; repetir remove 0 |

## Mecanismo de execução
1. **Identificação:** cada execução gera um `execucao_id` (uuid) gravado em `automacao_logs`, com `origem`
   (`cron`/`cli`/`manual`), `status` (`executando|sucesso|falha|ignorada`), `iniciado_em`, `finalizado_em`,
   `duracao_ms`, `resumo`, `erro`.
2. **Anti-duplicata:** se o mesmo job terminou com sucesso há menos de 30 min, a nova entrega é registrada como
   `ignorada` (HTTP 200) sem rodar. `flask ... executar-automacao NOME --forcar` ignora só esta janela.
3. **Trava de concorrência:** existe no máximo uma linha `executando` por tipo (`CREATE UNIQUE INDEX ... WHERE status='executando'`).
   Quem não consegue a trava é `ignorada` ("já existe uma execução em andamento"). Trava presa há > 15 min
   (processo morto) é marcada `falha` e liberada.
4. **Falha:** exceção → `status=falha`, `sucesso=0`, erro+traceback (até 4000 caracteres) **só no banco**; resposta HTTP 500
   genérica (`{"job","status":"falha","execucao_id"}`) para a Vercel registrar. A trava é liberada; a próxima execução tenta de novo
   (a Vercel não repete sozinha).
5. **Log estruturado:** `suafacul.automacao` registra início, fim, status e duração com o `execucao_id` (sem segredos).
6. **Segurança:** `hmac.compare_digest`; sem cookie/sessão; `Cache-Control: no-store`; jobs desconhecidos só são
   revelados a quem tem o segredo.

## Configuração
- Variável de ambiente **`CRON_SECRET`** (Vercel → Project → Settings → Environment Variables): `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- `vercel.json` já contém `crons`. Os testes garantem que os jobs agendados = os jobs registrados e que cada um roda ≤1x/dia.
- Localmente: `flask --app wsgi executar-automacao validacao-vestibulares [--forcar]` ou
  `curl -H "Authorization: Bearer $CRON_SECRET" http://localhost:5000/api/cron/validacao-vestibulares`.

## Schema (aditivo; nada apagado)
`automacao_logs` ganhou `execucao_id, status, origem, iniciado_em, finalizado_em, duracao_ms` e dois índices; linhas antigas
recebem `status` conforme `sucesso`. Teste com banco no formato antigo confirma a migração sem perda.

## Riscos e pendências
- **SQLite não persiste na Vercel.** A trava e o histórico vivem no banco: com SQLite em disco efêmero, o Cron rodaria mas
  os registros/efeitos se perderiam. **O Cron só é confiável em produção com banco persistente** (decisão adiada).
- **Entrega best-effort:** uma execução pode simplesmente não acontecer; a reconciliação cobre a defasagem, mas o status
  dos vestibulares pode ficar até ~24 h defasado. O cliente não deve tratar `status` como tempo real.
- **Hobby:** a hora exata varia dentro da hora agendada; a janela anti-duplicata (30 min) não conflita com isso.
- Não há alerta ativo de falha: hoje só o log (`automacao_logs` + logs da Vercel). Monitoramento fica para a fase de observabilidade.
- Importações e-MEC/INEP continuam manuais (CLI); não foram movidas para Cron (arquivos grandes e execuções longas).
- O `vercel.json` e o entrypoint `wsgi.py` **nunca foram validados em um deploy real**; validar em staging antes de confiar.
