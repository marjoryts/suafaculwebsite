# Banco de dados e camada de acesso

**Decisão vigente:** SQLite é o banco oficial (`database/suafacul.db`). Não há
migração para PostgreSQL em andamento. A aplicação foi organizada para que
essa troca, quando necessária, não exija reescrever regras de negócio.

## Camadas

```
rotas (app/routes) ─► services (app/services) ─► models/repositórios (app/models) ─► config/database.py ─► SQLite
       HTTP               regras de negócio         ÚNICO lugar com SQL              ÚNICO ponto de conexão
```

- `tests/test_camada_dados.py` **falha** se alguma rota/service voltar a abrir
  conexão ou escrever SQL, ou se surgir construção exclusiva do SQLite fora
  do ponto único (`config/database.py`) e de `database/init_db.py`.
- Não há ORM nem abstração de repositório genérica de propósito: os models
  atuais já são os repositórios.

## O que ficou isolado em `config/database.py` (troca em um só lugar)

| Helper | Papel hoje (SQLite) | Equivalente PostgreSQL |
|---|---|---|
| `get_connection()` | `sqlite3` + PRAGMAs (WAL, foreign_keys) + `row_factory` | psycopg + pool (em serverless, endpoint *pooled*) |
| `inserir()` | `cursor.lastrowid` | `INSERT … RETURNING id` |
| `sql_norm(col)` | função Python `normalizar()` registrada na conexão | `unaccent(lower(col))` ou coluna normalizada persistida |
| `like_ci(col)` | `col LIKE ?` (SQLite ignora caixa em ASCII) | `col ILIKE ?` |
| `agora_utc_str()`, `hoje_iso()` | datas calculadas em Python | idem (portável) |

Removido do código da aplicação nesta etapa: `date('now')`, `datetime('now', …)`,
`strftime('%m', …)`, `COLLATE NOCASE`, `lastrowid`, `INSERT OR IGNORE` (agora
`ON CONFLICT DO NOTHING`, aceito também pelo PostgreSQL) e todo SQL fora de
`app/models/`.

## Dependências de SQLite que AINDA existem (documentadas, não abstraídas)

| # | Onde | Detalhe | Ação futura |
|---|---|---|---|
| 1 | Todos os models | Placeholders `?` e nomeados `:x` (psycopg usa `%s` / `%(x)s`) | Um wrapper `execute()` em `config/database.py` |
| 2 | Todos os models | `sqlite3.Row` / `dict(row)` | `dict_row` do psycopg |
| 3 | `database/init_db.py` | DDL com `AUTOINCREMENT`, `PRAGMA table_info` (migração por `ALTER`), `TIMESTAMP` como texto, `INTEGER` como booleano | Substituir por migrations (Alembic) na migração |
| 4 | Schema | `idx_cursos_nome … COLLATE NOCASE` | Índice em `lower(nome)` / trigram |
| 5 | `vestibulares.data_prova` | Texto; filtro de mês e "próximos" assumem formato ISO `AAAA-MM-DD` (SUBSTR e comparação de texto) | Converter para `DATE` após normalizar dados; o validador aceita também `DD/MM/AAAA` |
| 6 | `models/busca.py`, `faculdade.py` | `LIKE '%x%'` sobre `normalizar()` = varredura completa | `pg_trgm` + `unaccent` (GIN) |
| 7 | Todos | Uma conexão por chamada; alguns models antigos não fecham a conexão em `finally` se ocorrer exceção | Context manager de transação ao migrar |
| 8 | Transações | Cada método faz `commit`; atômicos: `Curso.upsert_por_codigo_inep_lote`, `Vestibular.aplicar_validacoes` | Manter |
| 9 | Locking | WAL = 1 escritor por vez; importações longas seguram o lock (padrão `timeout=5s` para os demais) | Importar em janela de manutenção ou via CLI; PostgreSQL elimina o problema |

## RISCO de infraestrutura (Vercel)

O sistema de arquivos das Vercel Functions não é persistente: **um arquivo
SQLite gravável não sobrevive em produção na Vercel** (cadastros, favoritos,
testes vocacionais e logs se perderiam). SQLite serve para desenvolvimento,
testes e para um servidor com disco persistente. Para produção na Vercel será
necessário um banco externo — decisão adiada a pedido do proprietário; o código
foi preparado para isso (ver acima) sem instalar nada.

## Roteiro de migração (quando for decidido — nada disto foi executado)
1. Escolher o serviço e criar uma instância de **teste**.
2. Gerar a *baseline* do schema (Alembic) a partir do `init_db.py`.
3. Implementar o wrapper `execute()` e os helpers da tabela acima para PostgreSQL.
4. Rodar a suíte contra PostgreSQL (job de CI extra).
5. Migrar uma **cópia** dos dados; comparar contagem por tabela e integridade referencial.
6. Manter `suafacul.db` intacto como backup até a validação.
