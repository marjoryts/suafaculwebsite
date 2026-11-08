# Etapa 8 — Segurança da conta, e-mail e login com Google

Um único sistema de contas para o site e o app: o Flask é a autoridade. O site usa
`/api/usuario/*` (sessão por cookie) e as páginas novas usam `/api/v1/auth/*`; o app
usa `/api/v1`. As regras ficam em `app/services/` (`conta_service`, `codigo_service`,
`limite_service`, `email_service`, `google_service`, `usuario_service`).

## Regras

| Tema | Regra |
|---|---|
| Senha | 8–128 caracteres, com letras e números (só para senhas novas). Hash `scrypt` do Werkzeug. |
| Códigos | 5 dígitos gerados com `secrets`; guardados como HMAC-SHA256 (chave = `FLASK_SECRET_KEY`); uso único; um código novo invalida o anterior. |
| Validade | verificação de e-mail 30 min · recuperação de senha 15 min · troca de e-mail 30 min |
| Tentativas | 5 erros invalidam o código (`TOO_MANY_ATTEMPTS`). Intervalo de 60 s entre envios. |
| Limites (janela deslizante, chaves com hash) | login: 5 falhas/15 min por conta e 30/15 min por IP · cadastro: 10/h por IP · Google: 30/15 min por IP · reenvio de verificação: 5/h por e-mail · recuperação: 3/h por e-mail e 10/h por IP · conferência de códigos: 30/15 min por IP · senha atual: 5/15 min · troca de e-mail: 5/h |
| Enumeração | "Enviar código" e "Esqueci a senha" respondem igual (202) para e-mail cadastrado ou não; conta inexistente e código errado dão o mesmo erro; login com e-mail inexistente também conta para o bloqueio. |
| Recuperação | Redefinir a senha consome o código, confirma o e-mail e encerra **todas** as sessões (refresh tokens do app e cookies do site). |
| Troca de senha logado | Exige a senha atual (exceto conta criada pelo Google sem senha própria). Encerra as outras sessões; a atual continua. |
| Troca de e-mail | Exige a senha atual; o código vai para o endereço **novo**; o e-mail só muda após a confirmação (o antigo vale até lá). Admin que troca o e-mail de alguém deixa o e-mail como não verificado. |
| Sessões do site | O cookie guarda `credencial_versao`; cada requisição confere com o banco — trocar/redefinir a senha derruba os cookies antigos. |
| Logs | Nunca registram códigos, tokens ou senhas (há teste para isso). |

## Contas antigas (transição)

- Contas criadas antes desta etapa ficam com `email_verificado = 0` e **continuam
  entrando normalmente** — nada é apagado nem bloqueado.
- O painel do site e o Perfil do app mostram "Confirme seu e-mail" com o fluxo do código.
- Contas com Google vinculado são migradas como verificadas (o Google já provou o e-mail).
- Contas criadas pelo Google ficam com `senha_definida = 0` (podem criar uma senha sem
  "senha atual").
- **Proteção contra pré-sequestro:** se alguém criou uma conta local com um e-mail que
  não confirmou e o dono verdadeiro entra pelo Google com esse e-mail (verificado pelo
  Google), a conta é vinculada ao Google, a senha local é invalidada e todas as sessões
  são encerradas. Conta local já verificada é vinculada normalmente.

## Endpoints (`/api/v1`)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/registrar` | Cria a conta (e-mail não verificado), envia o código e abre a sessão. `data.verificacao_enviada` |
| POST | `/auth/login` | E-mail + senha (com limites; 429 + `Retry-After`) |
| POST | `/auth/google` | `{id_token}` → sessão (assinatura, `iss`, `aud`, `exp`, `email_verified` conferidos) |
| POST | `/auth/verificacao/enviar` | `{email}` → 202 genérico |
| POST | `/auth/verificacao/confirmar` | `{email, codigo}` → `{usuario}` |
| POST | `/auth/recuperacao/solicitar` | `{email}` → 202 genérico |
| POST | `/auth/recuperacao/validar` | `{email, codigo}` → confere sem consumir |
| POST | `/auth/recuperacao/redefinir` | `{email, codigo, password, password_confirm}` |
| PATCH | `/me` | nome; senha exige `password_atual`; e-mail aqui → 422 `EMAIL_CHANGE_REQUIRES_VERIFICATION` |
| POST | `/me/email` | `{email, password_atual}` → 202, código no endereço novo |
| POST | `/me/email/confirmar` | `{codigo}` → usuário atualizado |

Erros novos: `INVALID_CODE`, `CODE_EXPIRED` (422), `TOO_MANY_ATTEMPTS`, `RESEND_TOO_SOON`,
`RATE_LIMITED` (429, com `details.retry_after` e cabeçalho `Retry-After`),
`INVALID_CURRENT_PASSWORD` (422), `EMAIL_NOT_SENT` (422). Especificação completa em `/api/v1/openapi.json`.

Site (cookie): `POST /api/usuario/perfil` (aceita `password_atual`; troca de e-mail
devolve `email_pendente`), `POST /api/usuario/email/confirmar`. Páginas novas:
`/verificar-email` e `/recuperar-senha`.

## Configurar o envio de e-mail (Gmail com senha de app)

1. Na conta Google que vai enviar os e-mails, ative a **Verificação em duas etapas**
   (myaccount.google.com → Segurança).
2. Em myaccount.google.com → Segurança → **Senhas de app**, crie uma senha para
   "SuaFacul". O Google mostra 16 caracteres **uma única vez**.
3. No `.env` local (e em Vercel → Project → Settings → Environment Variables):
   ```
   EMAIL_MODO=smtp
   SMTP_HOST=smtp.gmail.com
   SMTP_PORTA=587
   SMTP_USUARIO=conta.que.envia@gmail.com
   SMTP_SENHA=<a senha de app, sem espaços>
   EMAIL_REMETENTE=SuaFacul <conta.que.envia@gmail.com>
   ```
4. Reinicie o servidor e faça um cadastro com um e-mail seu: o código deve chegar
   (veja também o spam). Limite do Gmail: ~500 envios/dia.

Sem SMTP configurado o site continua funcionando; os pedidos de código respondem
normalmente, mas nenhum e-mail sai (fica um aviso no log, sem o código).
Para testar no computador sem SMTP: `EMAIL_MODO=arquivo` grava cada e-mail em
`database/emails_dev/*.eml` (pasta ignorada pelo git; recusado na Vercel).

## Configurar o Google

### Site (já existia; revisado)
Google Cloud Console → APIs & Services → Credentials → **OAuth client ID → Web application**:
- Authorized redirect URIs:
  - `http://localhost:5000/auth/google/callback`
  - `https://suafaculwebsite.vercel.app/auth/google/callback`
- Variáveis: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_CALLBACK_URL`
  (a de produção na Vercel). O Authlib gera e confere `state` (anti-CSRF) e `nonce`.

### App Android
1. **Confirme o identificador do app.** O `mobile/app.json` está com
   `android.package` = `app.vercel.suafaculwebsite` (proposto a partir do domínio).
   Depois de criar o cliente OAuth Android, trocar o package exige outro cliente.
2. Gere um development build (o Expo Go não tem o módulo nativo do Google):
   ```
   cd mobile
   npx expo run:android            # local (Android Studio/SDK instalado)
   # ou: npx eas build --profile development --platform android
   ```
3. Pegue o **SHA-1** do certificado que assina esse build:
   - build local: `cd android && ./gradlew signingReport` (variant `debug`), ou
     `keytool -list -v -keystore android/app/debug.keystore -alias androiddebugkey -storepass android -keypass android`
   - EAS: `npx eas credentials` → Android → Keystore (mostra o SHA-1)
   - Play Store: Play Console → Integridade do app → certificado de assinatura do app.
4. Google Cloud → Credentials → **OAuth client ID → Android**: package
   `app.vercel.suafaculwebsite` + o SHA-1. Um cliente por certificado (debug, EAS, Play).
5. No `mobile/.env.local`: `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID=<o mesmo GOOGLE_CLIENT_ID do site>`.
   O token que o app recebe tem o cliente **Web** como audiência — o servidor já o aceita.
   `GOOGLE_ANDROID_CLIENT_ID` no servidor é opcional.
6. Gere o build de novo (variáveis `EXPO_PUBLIC_*` entram no bundle) e teste.

iOS: crie um cliente OAuth iOS com o bundle `app.vercel.suafaculwebsite`, defina
`GOOGLE_IOS_URL_SCHEME` (mobile, só no build) e `GOOGLE_IOS_CLIENT_ID` (servidor).

Nenhum segredo vai para o app: `GOOGLE_CLIENT_SECRET` e `SMTP_SENHA` ficam só no servidor.

## Testes

- Backend: `python -m pytest -q` (inclui `tests/test_seguranca_conta.py`). Os e-mails vão
  para uma caixa em memória (`EMAIL_MODO=memoria`) e o Google é testado com chaves RSA
  geradas no próprio teste — nenhuma conta ou credencial real.
- App: `cd mobile && npx jest` e `npx tsc --noEmit`. O módulo nativo do Google é simulado.

## O que precisa de teste manual com credenciais reais

- Entrega real de e-mail pelo Gmail (depende da senha de app).
- Login com Google no site em produção (depende das URIs cadastradas).
- Login com Google no app (depende do development build + cliente Android com SHA-1).
