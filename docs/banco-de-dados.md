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

## Esquema atual e regras de integridade

Fonte da verdade: `database/init_db.py` (cria as tabelas num banco novo e migra
bancos existentes a cada inicialização, sem apagar dados). Diagramas: BD-00 e
BD-03 em [`diagramas.md`](diagramas.md). `PRAGMA foreign_keys=ON` em toda conexão.

| Tabela | Chaves estrangeiras | Regra ao excluir o pai |
|---|---|---|
| `usuarios` | — | — |
| `faculdades` | — | — |
| `cursos` | `faculdade_id` → `faculdades.id` | `SET NULL` |
| `vestibulares` | `faculdade_id` → `faculdades.id` | `SET NULL` |
| `favoritos` | `usuario_id` → `usuarios.id` | `CASCADE` (favoritos são do usuário) |
| `refresh_tokens` | `usuario_id` → `usuarios.id` | `CASCADE` (sessões do usuário) |
| `teste_vocacional_resultados` | `usuario_id` → `usuarios.id` (anulável) | **`SET NULL`** |
| `cursos_catalogo`, `automacao_logs` | — | — |

`favoritos.item_id` é polimórfico (curso/vestibular/faculdade conforme `tipo`) e
por isso **não** tem FK — validado no serviço.

### `teste_vocacional_resultados.usuario_id` — `ON DELETE SET NULL` (auditoria 2026-11)

- **Problema:** a FK não tinha regra de exclusão; com `foreign_keys=ON`, excluir pelo
  admin (Web `/api/usuario/deletar` ou API v1 `DELETE /api/v1/admin/usuarios/{id}`)
  um usuário que já fez o teste falhava com `FOREIGN KEY constraint failed`.
- **Por que SET NULL e não CASCADE:** os resultados alimentam a estatística
  `total_testes_vocacionais` do painel. `usuario_id` já era anulável (testes
  anônimos), e todo o código que lê a tabela filtra por `usuario_id = ?` do usuário
  logado (histórico, recomendações, dashboard) — linhas com NULL nunca aparecem
  para outra conta. O resultado preservado não contém dado pessoal (só perfil,
  pontuação, alternativas e data), então fica anonimizado.
- **Teste anônimo × resultado de usuário excluído:** ambos têm `usuario_id` NULL. Um
  resultado anônimo só é visto/vinculado por quem tem o id dele no cookie de sessão
  assinado (`teste_pendente_id`), que é apagado no login. Um resultado de usuário
  excluído nunca esteve nesse cookie, então não pode ser "adotado" por outra conta
  (coberto por teste).
- **Migração** (`_migrar_fk_teste_vocacional`): SQLite não altera FK com `ALTER TABLE`,
  então a tabela é reconstruída pelo procedimento oficial (foreign_keys desligado,
  transação única, cópia, `DROP`/`RENAME`, `foreign_key_check` antes do `COMMIT`).
  Preserva ids, datas e o contador `AUTOINCREMENT`; é idempotente (só roda se a regra
  ainda não for `SET NULL`). Vínculos órfãos (usuário inexistente — só possíveis se o
  banco já rodou com FK desligada) viram NULL, que é o estado que a nova regra produz.
  Também cria `idx_teste_vocacional_usuario`.
- A DDL da tabela existe uma única vez (`_DDL_TESTE_VOCACIONAL`), usada na criação e na
  reconstrução.

### Tabela removida: `vestibular_inscricoes`

Criada por versões antigas do `init_db.py`, nunca teve model, serviço, rota, tela ou
uso no app Mobile (acompanhar inscrições é feito pelos favoritos de vestibular). Foi
retirada do esquema; em bancos existentes `_remover_vestibular_inscricoes` a apaga
**somente se estiver vazia** — se alguém tiver inserido linhas fora do app, a tabela
é mantida e o log avisa para exportar e remover manualmente.

### Script legado

`database/Suafacul_crud.sql` (MySQL, tabela `Candidato` e procedure inexistentes,
colunas faltando) não era usado por nada e contradizia o `init_db.py`. Foi movido
para `docs/legado/Suafacul_crud_mysql_OBSOLETO.sql`, marcado como obsoleto. Para ver
o esquema real de um banco: `sqlite3 database/suafacul.db ".schema"`.

### `faculdades.fonte`

`manual` (admin/catálogo), `emec` (importação por código/UF/Brasil — download
automático ou scraping) e `emec_csv_upload` (upload do CSV oficial e seed
automático). As duas últimas formam `FONTES_EMEC` (`app/models/faculdade.py`),
usada pela estatística "importadas do e-MEC" e pelo seed. Cada faculdade tem uma
única `fonte` (o upsert por `codigo_emec` não duplica), então a contagem não repete
registros.

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
| 3 | `database/init_db.py` | DDL com `AUTOINCREMENT`, `PRAGMA table_info`/`foreign_key_list` (migração por `ALTER` e reconstrução de tabela), `TIMESTAMP` como texto, `INTEGER` como booleano | Substituir por migrations (Alembic) na migração |
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
