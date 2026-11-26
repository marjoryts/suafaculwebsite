# Banco de dados e camada de acesso

**Decisão vigente:** o banco oficial é o **PostgreSQL do Supabase** (único banco do
site e do app Mobile). Diagnóstico, decisões, RLS e o passo a passo de implantação:
[`migracao-supabase.md`](migracao-supabase.md). O SQLite (`database/suafacul.db`)
não é mais usado pela aplicação; só é lido pelo comando `flask --app wsgi migrar-sqlite`.

## Camadas

```
rotas (app/routes) ─► services (app/services) ─► models/repositórios (app/models) ─► config/database.py ─► PostgreSQL (Supabase)
       HTTP               regras de negócio         ÚNICO lugar com SQL              ÚNICO ponto de conexão
```

- `tests/test_camada_dados.py` **falha** se alguma rota/service voltar a abrir
  conexão ou escrever SQL, ou se surgir construção exclusiva do SQLite no código.
- Não há ORM nem abstração de repositório genérica de propósito: os models
  atuais já são os repositórios.

## Esquema atual e regras de integridade

Fonte da verdade: `supabase/migrations/*.sql` (aplicadas pelo Supabase CLI, pelo
SQL Editor ou por `flask --app wsgi init-db`). Diagramas: BD-00 e BD-03 em
[`diagramas.md`](diagramas.md).

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
- **Migração de bancos SQLite antigos:** `database/migracao_sqlite.py` aplica a mesma regra
  (vínculos órfãos viram NULL, listados no relatório) e preserva ids e o contador de ids.

### Tabela removida: `vestibular_inscricoes`

Criada por versões antigas do `init_db.py`, nunca teve model, serviço, rota, tela ou
uso no app Mobile (acompanhar inscrições é feito pelos favoritos de vestibular). Não
existe no esquema PostgreSQL; se um SQLite antigo tiver linhas nela, a migração de
dados avisa e as mantém no arquivo de origem.

### Script legado

`database/Suafacul_crud.sql` (MySQL, tabela `Candidato` e procedure inexistentes,
colunas faltando) não era usado por nada e contradizia o `init_db.py`. Foi movido
para `docs/legado/Suafacul_crud_mysql_OBSOLETO.sql`, marcado como obsoleto. Para ver
o esquema real: `supabase/migrations/` ou *Database → Tables* no painel do Supabase.

### `faculdades.fonte`

`manual` (admin/catálogo), `emec` (importação por código/UF/Brasil — download
automático ou scraping) e `emec_csv_upload` (upload do CSV oficial e seed
automático). As duas últimas formam `FONTES_EMEC` (`app/models/faculdade.py`),
usada pela estatística "importadas do e-MEC" e pelo seed. Cada faculdade tem uma
única `fonte` (o upsert por `codigo_emec` não duplica), então a contagem não repete
registros.

## Ponto único de acesso (`config/database.py`)

| Helper | Papel |
|---|---|
| `get_connection()` | conexão do pool psycopg 3 (compatível com o pooler do Supabase: sem prepared statements no servidor) |
| `inserir()` | `INSERT … RETURNING id` |
| `sql_norm(col)` / `contem_sem_acento(col)` | `public.normalizar(col)` (unaccent + lower), indexada por trigram |
| `like_ci(col)` | `ILIKE` |
| `data_iso_sql(col)` | `public.data_iso(col)`: texto ISO → DATE, NULL se inválido |
| `agora_utc_str()`, `hoje_iso()` | datas calculadas em Python |

Os models continuam escrevendo `?`/`:nome` e lendo `linha['coluna']`: a tradução para o
psycopg e a conversão de datas para o formato de sempre (`AAAA-MM-DD HH:MM:SS`, UTC) ficam
nesse arquivo. Conexões esquecidas abertas voltam ao pool sozinhas.
