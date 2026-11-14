# Arquivos legados (somente histórico)

Arquivos mantidos apenas como registro da evolução do projeto. **Nada aqui é
usado pela aplicação, pelos testes ou pelo deploy** (a pasta `docs/` nem vai
para o bundle da Vercel — ver `.vercelignore`).

| Arquivo | O que era | Por que é obsoleto |
|---|---|---|
| `Suafacul_crud_mysql_OBSOLETO.sql` | Script MySQL da primeira versão do banco (antes `database/Suafacul_crud.sql`) | O sistema usa SQLite; o script referencia uma tabela `Candidato` e uma procedure que não existem, não tem várias tabelas/colunas atuais e diverge de `database/init_db.py` |

O esquema oficial é o criado e migrado por `database/init_db.py`; a
documentação está em [`docs/banco-de-dados.md`](../banco-de-dados.md).
