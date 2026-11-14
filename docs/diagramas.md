# Diagramas técnicos (fiéis ao código atual)

Versão em Mermaid (renderiza no GitHub/VS Code) dos diagramas da documentação
do projeto, revisados na auditoria técnica de 2026-11. Eles descrevem o código e
o banco **depois** das correções:

- `teste_vocacional_resultados.usuario_id` com `ON DELETE SET NULL`;
- tabela `vestibular_inscricoes` removida;
- pontuação do teste vocacional numa única implementação
  (`teste_vocacional_service.calcular`/`pontuar`).

> Se houver cópias desses diagramas fora do repositório (relatório do TCC,
> slides, ferramenta de modelagem), substitua-as por estas versões. O esquema
> do BD-03 foi gerado a partir de um banco criado pelo `database/init_db.py`
> (`PRAGMA table_info`/`foreign_key_list`) — não à mão.

## BD-00 — Diagrama geral do banco de dados

```mermaid
erDiagram
    usuarios ||--o{ favoritos : "salva (CASCADE)"
    usuarios ||--o{ refresh_tokens : "sessões do app (CASCADE)"
    usuarios |o--o{ teste_vocacional_resultados : "realiza (SET NULL; NULL = anônimo ou usuário excluído)"
    faculdades |o--o{ cursos : "oferece (SET NULL)"
    faculdades |o--o{ vestibulares : "organiza (SET NULL)"
    cursos_catalogo ||..o{ cursos : "mesmo nome (sem FK)"
    favoritos }o..|| cursos : "item_id quando tipo=curso (sem FK)"
    favoritos }o..|| vestibulares : "item_id quando tipo=vestibular (sem FK)"
    favoritos }o..|| faculdades : "item_id quando tipo=faculdade (sem FK)"
    automacao_logs {
        INTEGER id PK
    }
```

Linhas cheias = chave estrangeira real; pontilhadas = associação lógica sem FK.
`automacao_logs` não se relaciona com outras tabelas.

## BD-03 — Diagrama detalhado do banco de dados

```mermaid
erDiagram
    usuarios ||--o{ favoritos : usuario_id
    usuarios ||--o{ refresh_tokens : usuario_id
    usuarios |o--o{ teste_vocacional_resultados : usuario_id
    faculdades |o--o{ cursos : faculdade_id
    faculdades |o--o{ vestibulares : faculdade_id
    automacao_logs {
        INTEGER id PK
        TEXT tipo "NOT NULL"
        TIMESTAMP executado_em
        INTEGER sucesso "NOT NULL"
        TEXT resumo
        TEXT erro
        TEXT execucao_id
        TEXT status
        TEXT origem
        TIMESTAMP iniciado_em
        TIMESTAMP finalizado_em
        INTEGER duracao_ms
    }
    cursos {
        INTEGER id PK
        TEXT nome "NOT NULL"
        TEXT instituicao "NOT NULL"
        INTEGER faculdade_id FK "ON DELETE SET NULL"
        TEXT modalidade "NOT NULL"
        TEXT descricao
        TEXT duracao
        TEXT grau
        TEXT area
        TEXT tipo_instituicao "NOT NULL"
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TEXT codigo_inep_curso UK
    }
    cursos_catalogo {
        INTEGER id PK
        TEXT nome UK "NOT NULL"
        TEXT area
        TEXT grau
        TEXT duracao
        TEXT descricao
        TEXT imagem_url
        INTEGER ordem
        INTEGER seed_versao
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    faculdades {
        INTEGER id PK
        TEXT codigo_emec UK
        TEXT nome "NOT NULL"
        TEXT sigla
        TEXT organizacao_academica
        TEXT tipo_instituicao "NOT NULL"
        TEXT url
        TEXT endereco
        TEXT cidade
        TEXT uf
        TEXT telefone
        TEXT email
        TEXT situacao
        TEXT fonte
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
    favoritos {
        INTEGER id PK
        INTEGER usuario_id FK "ON DELETE CASCADE"
        TEXT tipo "NOT NULL"
        INTEGER item_id "NOT NULL"
        TEXT nome_item "NOT NULL"
        TIMESTAMP created_at
    }
    refresh_tokens {
        INTEGER id PK
        TEXT familia_id "NOT NULL"
        INTEGER usuario_id FK "ON DELETE CASCADE"
        TEXT token_hash UK "NOT NULL"
        TEXT dispositivo
        TIMESTAMP expira_em "NOT NULL"
        TIMESTAMP usado_em
        TIMESTAMP revogado_em
        TEXT motivo_revogacao
        TIMESTAMP created_at
    }
    teste_vocacional_resultados {
        INTEGER id PK
        INTEGER usuario_id FK "ON DELETE SET NULL"
        TEXT perfil_principal "NOT NULL"
        TEXT perfis_json "NOT NULL"
        TEXT respostas_json
        TIMESTAMP created_at
    }
    usuarios {
        INTEGER id PK
        TEXT nome_usuario UK "NOT NULL"
        TEXT email UK "NOT NULL"
        TEXT senha "NOT NULL"
        TEXT tipo "NOT NULL"
        TIMESTAMP created_at
        TIMESTAMP updated_at
        TEXT google_id UK
        TEXT auth_provider "NOT NULL"
        TEXT avatar_url
    }
    vestibulares {
        INTEGER id PK
        TEXT nome "NOT NULL"
        TEXT instituicao
        INTEGER faculdade_id FK "ON DELETE SET NULL"
        TEXT tipo_instituicao "NOT NULL"
        TEXT cidade
        TEXT regiao
        TEXT periodo_inscricao
        TEXT data_prova
        TEXT descricao
        TEXT link_edital
        TEXT taxa_inscricao
        TEXT cursos_oferecidos
        TEXT requisitos
        TEXT fonte
        INTEGER seed_versao
        TEXT status_validacao
        INTEGER cadastrado_ok
        TIMESTAMP ultima_validacao
        TIMESTAMP created_at
        TIMESTAMP updated_at
    }
```

Observações:

- `usuarios.google_id` e `cursos.codigo_inep_curso` são únicos só quando não nulos (índice parcial).
- `automacao_logs` tem índice único parcial em `tipo WHERE status='executando'` (trava de execução).
- Índices de apoio: `idx_teste_vocacional_usuario`, `idx_cursos_faculdade`, `idx_cursos_nome`,
  `idx_vestibulares_nome`, `idx_refresh_tokens_familia`, `idx_refresh_tokens_usuario`,
  `idx_automacao_tipo_status`.
- CHECKs: `usuarios.tipo IN ('aluno','admin')`, `faculdades.tipo_instituicao IN ('Pública','Privada')`,
  `favoritos.tipo IN ('curso','vestibular','faculdade')`; `UNIQUE(usuario_id, tipo, item_id)` em `favoritos`.

## SD-12 — Exclusão de usuário pelo painel administrativo

Os dois painéis (site e app) chegam ao mesmo `usuario_service.excluir` e ao mesmo
`DELETE`; as regras de FK do SQLite fazem o resto numa única instrução.

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant Web as Site /admin (admin.js)
    participant App as App Mobile (admin)
    participant R1 as POST /api/usuario/deletar<br/>(@admin_required)
    participant R2 as DELETE /api/v1/admin/usuarios/{id}<br/>(@requer_admin)
    participant AS as admin_service.excluir_usuario
    participant US as usuario_service.excluir
    participant M as Usuario.deletar
    participant DB as SQLite (foreign_keys=ON)

    alt Painel web
        Admin->>Web: Excluir usuário
        Web->>R1: id (cookie de sessão)
        R1->>US: excluir(ator_id, id)
    else App (API v1)
        Admin->>App: Excluir usuário
        App->>R2: Bearer token
        R2->>AS: excluir_usuario(ator_id, id)
        AS->>M: buscar_por_id(id)
        alt não existe
            AS-->>R2: NaoEncontradoError → 404
        end
        AS->>US: excluir(ator_id, id)
    end
    alt id == ator_id
        US-->>Admin: PermissaoNegadaError ("não pode excluir seu próprio usuário")
    end
    US->>M: deletar(id)
    M->>DB: DELETE FROM usuarios WHERE id=?
    Note over DB: favoritos do usuário → apagados (CASCADE)<br/>refresh_tokens → apagados (CASCADE)<br/>teste_vocacional_resultados.usuario_id → NULL (SET NULL)<br/>os resultados continuam na tabela e nas estatísticas
    DB-->>M: OK
    M-->>US: {success: true}
    US-->>R1: JSON {success: true}
    AS-->>R2: 204 No Content
```

## SD-10 — Teste vocacional (envio das respostas)

Três entradas, uma regra: todas passam por `teste_vocacional_service.calcular`.

```mermaid
sequenceDiagram
    autonumber
    actor Aluno
    participant P as Página /testevocacional
    participant S as POST /api/teste_vocacional/salvar
    participant RS as POST /api/teste_vocacional/responder
    participant V1 as POST /api/v1/teste-vocacional/resultados
    participant TVS as teste_vocacional_service
    participant TV as TesteVocacional (model)
    participant DB as SQLite

    alt Página web
        Aluno->>P: responde as 10 perguntas
        P->>S: respostas_json {q1: "tecnico,cientifico", ...}
        S->>TVS: calcular(respostas, formato="valor")
    else Cliente legado (sessão)
        Aluno->>RS: {q1: "a", ...}
        RS->>TVS: submeter(respostas, usuario_id)
        TVS->>TVS: calcular(respostas, formato="id")
    else App Mobile
        Aluno->>V1: {"respostas": {"q1": "a", ...}}
        V1->>TVS: submeter(respostas, usuario_id ou None)
        TVS->>TVS: calcular(respostas, formato="id")
    end
    TVS->>TVS: resolver_respostas() → alternativa de cada pergunta<br/>(falta/inválida → ValidacaoError)
    TVS->>TVS: pontuar() → scores + perfis_principais
    alt /salvar
        S->>TV: salvar_resultado(usuario_id ou None, perfil, perfis_json, respostas_json)
    else /responder e API v1
        TVS->>TV: salvar_resultado(...)
    end
    TV->>DB: INSERT INTO teste_vocacional_resultados
    alt /salvar sem login
        S->>S: session["teste_pendente_id"] = id<br/>(vinculado à conta no login/cadastro)
        S-->>P: {success, id, redirect} → página de resultado
    else /responder
        RS-->>Aluno: {success, scores, pontuacoes, perfis + cursos_sugeridos}
    else API v1
        V1-->>Aluno: 201 {data: mesmo formato}
    end
```

Depois do envio, a página de resultado (`GET /api/teste_vocacional/resultado` e
`/recomendacoes`) e o app (`GET /api/v1/teste-vocacional/recomendacoes`) leem o
resultado salvo e calculam a compatibilidade com `vocacional_service.recomendar_cursos`.

## CL-05 — Classes do teste vocacional

Os serviços são módulos Python (funções), representados como classes `<<service>>`.

```mermaid
classDiagram
    direction LR
    class teste_vocacional_dados {
        <<module>>
        +PERFIS: dict
        +ORDEM_PERFIS: list
        +SECOES: list
    }
    class teste_vocacional_service {
        <<service>>
        +FORMATOS_RESPOSTA = ("id", "valor")
        +questionario() dict
        +perguntas_formulario() list
        +valor_da_opcao(opcao) str
        +resolver_respostas(respostas, formato) list
        +pontuar(opcoes) dict  «REGRA ÚNICA»
        +calcular(respostas, formato="id") dict
        +submeter(respostas, usuario_id) dict
        +historico(usuario_id, limite) list
        +pontuacoes(scores) list
        +nome_perfil(chave) str
        +recomendacoes(usuario_id, resultado_id, limite) dict
    }
    class vocacional_service {
        <<service>>
        +PERFIS
        +DESCRICOES
        +PONTOS_POSSIVEIS
        +afinidades(scores) dict
        +perfis_do_curso(nome, area) tuple
        +compatibilidade(perfis, afin) int
        +recomendar_cursos(scores, limite) dict
        +ler_scores(perfis_json) dict
    }
    class TesteVocacional {
        <<model>>
        +salvar_resultado(dados) dict
        +buscar_por_id(id) dict
        +ultimo_do_usuario(usuario_id) dict
        +vincular_a_usuario(resultado_id, usuario_id) bool
        +listar_por_usuario(usuario_id, limite) list
    }
    class Curso {
        <<model>>
        +listar(filtros) list
        +agrupados_por_nome_e_area() list
    }
    class api_teste_vocacional {
        <<blueprint /api/teste_vocacional>>
        +perguntas()
        +responder()
        +salvar()
        +resultado()
        +recomendacoes()
    }
    class api_v1_teste_vocacional {
        <<blueprint /api/v1>>
        +teste_perguntas()
        +teste_enviar_respostas()
        +teste_historico()
        +teste_recomendacoes()
    }
    class dashboard_service {
        <<service>>
        +resumo(usuario_id)
    }
    api_teste_vocacional ..> teste_vocacional_service : calcular / submeter / pontuacoes
    api_teste_vocacional ..> vocacional_service : recomendar_cursos / ler_scores
    api_teste_vocacional ..> TesteVocacional : salvar_resultado (/salvar)
    api_v1_teste_vocacional ..> teste_vocacional_service
    dashboard_service ..> teste_vocacional_service : historico
    teste_vocacional_service ..> teste_vocacional_dados
    teste_vocacional_service ..> vocacional_service : recomendar_cursos
    teste_vocacional_service ..> TesteVocacional
    teste_vocacional_service ..> Curso : cursos sugeridos
    vocacional_service ..> teste_vocacional_dados
    vocacional_service ..> Curso
```

Removidos nesta revisão: `vocacional_service.calcular_pontuacao`,
`vocacional_service.validar_respostas` e `vocacional_service.RespostasInvalidas`
(eram a segunda implementação da pontuação, usada só por `/salvar`).
