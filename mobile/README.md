# SuaFacul — app mobile (Expo + React Native + TypeScript)

Cliente do backend Flask. **Toda a regra de negócio fica no backend** (pontuação do teste vocacional,
validação de cadastro, favoritos, status dos vestibulares...). O app só exibe dados e chama a API
`/api/v1` (contrato: `GET /api/v1/openapi.json`; guias em `../docs/etapa4-api-v1.md` e `../docs/etapa5-auth-mobile.md`).

> **Estado atual:** autenticação funcional (login e cadastro, sessão com tokens no SecureStore) e a
> navegação principal (Explorar | Salvos | Perfil). As demais telas são **esqueletos** ("Em construção")
> que aguardam o Figma. O visual atual (`src/theme/tokens.ts`) é **provisório**.

## Navegação (Expo Router)
Login obrigatório. Abas principais: **Explorar**, **Salvos** e **Perfil**. Cursos, Faculdades, Vestibulares e
Teste vocacional ficam **dentro** de Explorar.

```
src/app/
├── _layout.tsx                 provedor de sessão + porteiro (Stack.Protected) + splash
├── (auth)/                     só para quem NÃO está logado
│   ├── login.tsx  cadastro.tsx                          FUNCIONAIS
│   └── recuperar-senha.tsx  verificar-email.tsx  senha-alterada.tsx   só interface
└── (app)/                      só para quem está logado → abas
    ├── (explorar)/   index · busca · cursos/ · faculdades/ · vestibulares/ · teste-vocacional/{index,perguntas,resultado}
    ├── (salvos)/     salvos
    ├── (perfil)/     perfil (ver + sair) · editar · alterar-senha
    └── cursos|faculdades|vestibulares/[id]   detalhes, presentes em Explorar E em Salvos (o voltar respeita a aba)
```

## Pastas
```
src/
├── app/            SÓ rotas e layouts
├── api/            client.ts (HTTP + Bearer + renovação), auth.ts, tipos.ts
├── auth/           SessaoProvider (React), gerenciadorDeSessao (lógica pura), tokenStorage (SecureStore)
├── components/ui/  Tela, Botao, CampoTexto, EmConstrucao, TelaSemConexao
├── screens/        telas compartilhadas entre abas (detalhes)
├── theme/          tokens (cores, espaços, bordas) — trocar pelos do Figma
└── config.ts       URL da API (EXPO_PUBLIC_API_URL)
__tests__/          testes (fora de src/app, que só pode ter rotas)
```

## Sessão e tokens
- `POST /auth/login|registrar|refresh|logout`. O **access token** (15 min) fica só na memória; o **refresh token**
  (30 dias, de uso único) fica no `expo-secure-store` (Keychain/Keystore).
- Ao abrir o app: lê o refresh guardado → renova → `GET /me`. Sem sessão → login. **Sem rede NÃO desloga**
  (mostra "Sem conexão" com "Tentar novamente").
- O refresh é de uso único: renovações simultâneas esperam **a mesma** (senão o servidor revoga a sessão por "reuso").
  Em `TOKEN_EXPIRED` o cliente renova uma vez e repete a requisição; em `INVALID_TOKEN`/refresh revogado volta ao login.

## Rodar
```bash
cd mobile
npm install            # primeira vez
npm start              # QR code → Expo Go (Android) ou Câmera (iPhone), mesma rede Wi-Fi
```
O app encontra o backend sozinho: em desenvolvimento usa o mesmo computador que roda o Expo (o IP do QR code),
porta 5000 — trocar de rede Wi-Fi não exige editar nada. Só crie `mobile/.env.local` (veja `.env.example`) para
apontar para outro servidor. Suba o Flask aceitando conexões da rede, **sem debug**:
```powershell
cd ..
$env:FLASK_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
flask --app wsgi run --host 0.0.0.0 --port 5000
```
Com `run.py` (que por padrão escuta só em `127.0.0.1`, inalcançável pelo celular): `$env:HOST = "0.0.0.0"; python run.py`
(precisa de `FLASK_SECRET_KEY` e recusa subir com `FLASK_DEBUG=1` nesse modo).
Reinicie o `npm start` depois de mudar o `.env.local` ou as dependências. O Firewall do Windows pode pedir permissão (rede **privada**).

## Verificações
```bash
npm run typecheck          # TypeScript
npm test                   # Jest: sessão, cliente HTTP, navegação com as rotas reais
npx expo-doctor            # diagnóstico do projeto
```
Integração com o backend real (opcional): suba o Flask em uma porta de teste e rode
`INTEGRACAO=1 EXPO_PUBLIC_API_URL=http://127.0.0.1:5060 npm test -- integracao`.

## Observações
- **Não deixe o projeto dentro do OneDrive (nem Dropbox/Google Drive).** Ele transforma os arquivos de `node_modules`
  em "reparse points" e o Metro (Expo) falha com `EINVAL readlink` / erro 500 no Expo Go. Mantenha em uma pasta comum,
  ex.: `C:\dev\suafacul`.
- **IP do computador muda** (DHCP). Se o app disser que não conecta, confira `ipconfig` e o `EXPO_PUBLIC_API_URL` do
  `.env.local`, e reinicie o `npm start` com `npx expo start --go --clear`. Em desenvolvimento a mensagem de erro mostra
  o endereço que o app está usando.
- Android e iOS apenas (`npm run web` não é suportado; o site já existe).
- API em HTTP só para desenvolvimento; em produção use **HTTPS** (Android bloqueia HTTP em builds de release).
- O botão "Entrar com Google" aparece **desabilitado** (ponto de extensão; o OAuth não existe ainda).
- `npm audit` aponta vulnerabilidades em dependências **transitivas** das ferramentas do Expo/React Native.
  Não use `npm audit fix --force`; atualize junto com o SDK.
