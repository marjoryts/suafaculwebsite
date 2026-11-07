# Etapa 0 — Correções de segurança críticas

Cada item: problema → risco → menor correção → teste. Testes em
`tests/test_security.py` (a suíte completa passa: 134 testes).

## Corrigido

### 1. Debug ligado por padrão
- **Problema:** `FLASK_DEBUG` assumia `1` quando ausente (`app.py`, `.env.example`).
- **Risco:** o console do Werkzeug permite execução remota de código; em um
  deploy sem a variável, qualquer visitante poderia explorá-lo.
- **Correção:** padrão passou a `0`. Debug só liga com `FLASK_DEBUG=1`.
- **Teste:** `test_debug_desligado_quando_flask_debug_nao_definido`.

### 2. Chave de sessão hardcoded
- **Problema:** sem `FLASK_SECRET_KEY`, o app usava uma chave pública do
  código-fonte.
- **Risco:** qualquer pessoa forja um cookie de sessão válido (inclusive de admin).
- **Correção:** fora do debug o app **não sobe** sem chave (ou com a chave
  legada). Em debug usa chave aleatória efêmera.
- **Testes:** `test_sem_secret_key_fora_do_debug_nao_sobe`,
  `test_chave_legada_publica_e_rejeitada`, `test_sem_secret_key_em_debug_usa_chave_efemera`.

### 3. Credencial administrativa padrão + auto-promoção
- **Problema:** `init_db` criava `admin/admin123` e, se não houvesse admin,
  promovia o primeiro usuário cadastrado.
- **Risco:** login conhecido publicamente; em deploy novo (ou cold start),
  quem se registrasse primeiro virava admin.
- **Correção:** admin só é criado se `SUAFACUL_ADMIN_PASSWORD` for definida;
  auto-promoção removida. Se algum admin existente ainda usa `admin123`, o
  app **apenas avisa** no log (não altera credenciais).
- **Testes:** `test_banco_novo_sem_senha_de_bootstrap_nao_tem_admin_padrao`,
  `test_bootstrap_cria_admin_somente_com_senha_explicita`,
  `test_primeiro_usuario_registrado_nao_vira_admin`.

### 4. Cookie de sessão sem flags
- **Problema:** sem `SameSite`/`Secure` explícitos.
- **Risco:** CSRF em POSTs de outro site; cookie trafegando em HTTP.
- **Correção:** `HttpOnly`, `SameSite=Lax`, `Secure` (padrão ligado fora do
  debug; `SESSION_COOKIE_SECURE=0` para desligar em ambiente local sem HTTPS).
- **Testes:** `test_cookie_secure_por_padrao_fora_do_debug`,
  `test_cookie_de_sessao_emitido_com_httponly_e_samesite`.

### 5. Papel de admin confiado ao cookie
- **Problema:** `admin_required` lia `tipo` da sessão (validade 7 dias).
- **Risco:** admin rebaixado/excluído mantinha acesso até 7 dias.
- **Correção:** `admin_required` consulta o usuário no banco a cada requisição
  (falha fechada: sem usuário → 401).
- **Testes:** `test_admin_rebaixado_perde_acesso_imediatamente`,
  `test_usuario_excluido_perde_sessao_admin`.

### 6. Enumeração de usuários e senha fraca no registro
- **Problema:** login distinguia "usuário não encontrado" de "senha incorreta";
  registro aceitava senha de 1 caractere.
- **Correção:** mensagem única; mínimo de 6 caracteres (igual à edição de perfil).
- **Testes:** `test_login_nao_revela_se_usuario_existe`, `test_registro_exige_senha_minima`.

### 7. Testes dependiam do `.env` real
- Os testes agora isolam o ambiente (`tests/conftest.py::load_app`). Os 2
  testes de Google que falhavam por causa do `.env` local voltaram a passar.

## Ação necessária do proprietário (não alterei)
- O banco local **ainda tem o admin `admin` com a senha `admin123`**. Troque em
  Dashboard → Editar Perfil (ou peça um reset explícito).
- Para desenvolvimento local, adicione `FLASK_DEBUG=1` ao `.env`.
- Em produção defina `FLASK_SECRET_KEY` (forte) e, se o banco for novo,
  `SUAFACUL_ADMIN_PASSWORD`.

## Identificado e **não** corrigido nesta etapa (vai para as próximas)
| Item | Motivo de adiar |
|---|---|
| Sem rate limit / bloqueio de força bruta no login | Precisa de armazenamento compartilhado (serverless); decidir junto com a infraestrutura |
| `GET /api/usuario/logout` e `/logout` | Baixo risco com `SameSite=Lax`; muda com a API v1 |
| Respostas `Erro: <exceção>` vazam detalhes do SQLite | Exige envelope de erros estruturado (Etapa API) |
| `int()` sem validação → HTTP 500 | Validação de entrada na API v1 |
| `POST /api/teste_vocacional/salvar` aceita anônimos sem limite | Definir regra de negócio + rate limit |
| Uploads de CSV sem limite útil (400 MB+) | Depende de onde a importação vai rodar (ver análise Vercel) |
