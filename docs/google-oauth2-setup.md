# 🔐 Configuração Google OAuth2

Este guia mostra como configurar o Google OAuth2 para o sistema de autenticação.

## 📋 Pré-requisitos

- Conta Google (Gmail)
- Projeto no Google Cloud Console
- Sistema rodando localmente (`http://localhost:8000`)

## 🚀 Passo a Passo

### 1. Criar Projeto no Google Cloud Console

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Clique em **"Select a project"** → **"New Project"**
3. Nome do projeto: `intelligent-document-search`
4. Clique em **"Create"**

### 2. Habilitar Google+ API

1. No menu lateral, vá em **"APIs & Services"** → **"Library"**
2. Procure por **"Google+ API"** ou **"People API"**
3. Clique em **"Enable"**

### 3. Configurar OAuth Consent Screen

1. Vá em **"APIs & Services"** → **"OAuth consent screen"**
2. Escolha **"External"** (para testes)
3. Preencha os campos obrigatórios:
   - **App name**: `Intelligent Document Search`
   - **User support email**: seu email
   - **Developer contact information**: seu email
4. Clique em **"Save and Continue"**
5. Em **"Scopes"**, adicione:
   - `openid`
   - `email` 
   - `profile`
6. Em **"Test users"**, adicione seu email para testes
7. Clique em **"Save and Continue"**

### 4. Criar Credenciais OAuth2

1. Vá em **"APIs & Services"** → **"Credentials"**
2. Clique em **"+ Create Credentials"** → **"OAuth 2.0 Client IDs"**
3. **Application type**: `Web application`
4. **Name**: `Intelligent Document Search Web Client`
5. **Authorized redirect URIs**: adicione:
   ```
   http://localhost:8000/auth/google/callback
   http://localhost:8000/static/oauth2-test.html
   ```
6. Clique em **"Create"**
7. **IMPORTANTE**: Copie o **Client ID** e **Client Secret**

### 5. Configurar Variáveis de Ambiente

Adicione as seguintes variáveis ao seu arquivo `.env`:

```bash
# Google OAuth2 Configuration
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# JWT Configuration (se ainda não tiver)
JWT_SECRET=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRY_DAYS=3
```

### 6. Testar a Configuração

1. **Inicie o servidor**:
   ```bash
   python -m interface.main
   ```

2. **Acesse a página de teste**:
   ```
   http://localhost:8000/static/oauth2-test.html
   ```

3. **Siga os passos na página**:
   - Clique em "Obter URL do Google"
   - Clique em "Fazer Login com Google"
   - Autorize o aplicativo
   - Verifique se o login foi bem-sucedido

## 🧪 Endpoints Disponíveis

### GET `/api/v1/auth/google`
Retorna URL para iniciar fluxo OAuth2:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "redirect_uri": "http://localhost:8000/auth/google/callback"
}
```

### GET `/api/v1/auth/google/callback?code=...`
Processa callback do Google e retorna JWT:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@gmail.com",
    "full_name": "Nome do Usuário",
    "role": "user"
  }
}
```

### POST `/api/v1/auth/google/token`
Login direto com Google ID Token (para SPAs):
```json
{
  "google_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6..."
}
```

## 🔧 Fluxos Suportados

### 1. Authorization Code Flow (Recomendado)
- Usuário é redirecionado para Google
- Google retorna código de autorização
- Servidor troca código por tokens
- Mais seguro para aplicações web

### 2. ID Token Flow (SPAs)
- Frontend obtém ID token diretamente
- Envia token para API validar
- Útil para Single Page Applications

## 🛡️ Segurança

### Validações Implementadas
- ✅ Verificação do issuer (`accounts.google.com`)
- ✅ Validação da assinatura do token
- ✅ Verificação do client ID
- ✅ Verificação de expiração
- ✅ Mapeamento seguro de usuários

### Boas Práticas
- ✅ Client Secret nunca exposto no frontend
- ✅ Tokens JWT com expiração configurável
- ✅ Logs estruturados para auditoria
- ✅ Tratamento de erros específicos

## 🚨 Troubleshooting

### Erro: "Google OAuth2 não configurado"
- Verifique se `GOOGLE_CLIENT_ID` está no `.env`
- Reinicie o servidor após adicionar variáveis

### Erro: "redirect_uri_mismatch"
- Verifique se a URI no Google Console está exata
- Deve incluir protocolo (`http://`) e porta (`:8000`)

### Erro: "invalid_client"
- Verifique se `GOOGLE_CLIENT_SECRET` está correto
- Confirme se o Client ID e Secret são do mesmo projeto

### Erro: "access_denied"
- Usuário cancelou autorização
- Verifique se o usuário está na lista de test users

## 📚 Recursos Adicionais

- [Google OAuth2 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [OAuth2 Playground](https://developers.google.com/oauthplayground/)

## ✅ Checklist de Configuração

- [ ] Projeto criado no Google Cloud Console
- [ ] APIs habilitadas (Google+ ou People API)
- [ ] OAuth Consent Screen configurado
- [ ] Credenciais OAuth2 criadas
- [ ] Redirect URIs configuradas
- [ ] Variáveis de ambiente adicionadas ao `.env`
- [ ] Servidor reiniciado
- [ ] Teste realizado com sucesso

---

🎉 **Parabéns!** Seu Google OAuth2 está configurado e funcionando!
