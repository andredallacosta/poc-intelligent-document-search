# Guia de Configuração do Sistema de Emails

## 📧 Visão Geral

O sistema de emails permite enviar:

- **Convites de usuários** com token de ativação
- **Emails de boas-vindas** após ativação
- **Redefinição de senha** (preparado para futuro)
- **Confirmação de ativação** de conta

## ⚙️ Configuração SMTP

### Variáveis de Ambiente (.env)

Adicione as seguintes configurações ao seu arquivo `.env`:

```bash
# === CONFIGURAÇÃO DE EMAIL ===

# Servidor SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true

# Credenciais
SMTP_USERNAME=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_de_app

# Configurações de envio
SMTP_FROM_EMAIL=noreply@suaempresa.com  # Opcional, usa SMTP_USERNAME se não definido
SMTP_FROM_NAME=Sistema de Documentos Inteligentes

# URL base para links nos emails
BASE_URL=http://localhost:8000  # Ou sua URL de produção
```

## 🔧 Configuração por Provedor

### Gmail (Recomendado para desenvolvimento)

1. **Ative a verificação em duas etapas** na sua conta Google
2. **Gere uma senha de app**:
   - Acesse: <https://myaccount.google.com/apppasswords>
   - Selecione "App" → "Outro (nome personalizado)"
   - Digite "Sistema de Documentos"
   - Use a senha gerada no `SMTP_PASSWORD`

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=seu_email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop  # Senha de app (16 caracteres)
```

### Outlook/Hotmail

```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=seu_email@outlook.com
SMTP_PASSWORD=sua_senha
```

### SendGrid (Produção)

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.sua_api_key_aqui
SMTP_FROM_EMAIL=noreply@suaempresa.com
```

### Mailtrap (Desenvolvimento/Teste)

```bash
SMTP_HOST=live.smtp.mailtrap.io
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=2bd3d21d684829  # Token do Mailtrap (não é email)
SMTP_PASSWORD=sua_senha_mailtrap
SMTP_FROM_EMAIL=noreply@suaempresa.com  # OBRIGATÓRIO para Mailtrap
```

### Amazon SES (Produção)

```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=sua_access_key_id
SMTP_PASSWORD=sua_secret_access_key
SMTP_FROM_EMAIL=noreply@suaempresa.com
```

## 🧪 Testando o Sistema

### Teste Rápido via Script

```bash
# Testa todos os tipos de email
python scripts/test_email_system.py --email seu_email@gmail.com --type all

# Testa apenas convite
python scripts/test_email_system.py --email seu_email@gmail.com --type invitation

# Testa apenas boas-vindas
python scripts/test_email_system.py --email seu_email@gmail.com --type welcome
```

### Teste via API

```bash
# 1. Faça login como admin
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@teste.com", "password": "123456"}'

# 2. Use o token para criar usuário (enviará email automaticamente)
curl -X POST http://localhost:8000/api/v1/users/create \
  -H "Authorization: Bearer SEU_TOKEN_AQUI" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "novo_usuario@gmail.com",
    "full_name": "Novo Usuário",
    "role": "user",
    "primary_municipality_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

## 📋 Templates de Email

### Email de Convite

- **Assunto**: "Convite para acessar o Sistema de Documentos Inteligentes"
- **Conteúdo**: Link de ativação com token
- **Expiração**: 7 dias
- **Formato**: HTML + Texto

### Email de Boas-vindas

- **Assunto**: "Bem-vindo ao Sistema de Documentos Inteligentes!"
- **Conteúdo**: Instruções de uso
- **Enviado**: Após ativação da conta

### Email de Confirmação

- **Assunto**: "Conta ativada com sucesso!"
- **Conteúdo**: Confirmação de ativação
- **Enviado**: Imediatamente após ativação

## 🔒 Segurança e Anti-Spam

### Boas Práticas

1. **Use senhas de app** em vez de senhas principais
2. **Configure SPF/DKIM** para evitar spam
3. **Use HTTPS** em produção para links seguros
4. **Monitore bounces** e emails rejeitados
5. **Rate limiting** já implementado para evitar spam

### ⚠️ Prevenção de Spam - CRÍTICO

**IMPORTANTE**: O sistema foi atualizado para corrigir problemas comuns que causam emails serem marcados como spam:

#### Problemas Corrigidos ✅

- **Missing Date header** (1.4 pontos) - ✅ CORRIGIDO: Cabeçalho Date adicionado automaticamente
- **Missing Message-ID header** (0.1 pontos) - ✅ CORRIGIDO: Message-ID único gerado para cada email
- **Gmail From header mismatch** (1.0 pontos) - ✅ CORRIGIDO: Usa email autenticado como From
- **High bit body without Message-ID** (3.6 pontos) - ✅ CORRIGIDO: Headers obrigatórios adicionados

#### Configuração Anti-Spam

```bash
# CENÁRIO 1: SMTP_USERNAME é um email (Gmail, Outlook)
SMTP_USERNAME=seu_email@gmail.com
SMTP_FROM_EMAIL=noreply@suaempresa.com  # Opcional, vai para Reply-To

# CENÁRIO 2: SMTP_USERNAME é um token (Mailtrap, SendGrid)
SMTP_USERNAME=2bd3d21d684829  # Token do Mailtrap
SMTP_FROM_EMAIL=noreply@suaempresa.com  # OBRIGATÓRIO neste caso

# O sistema automaticamente:
# - Usa SMTP_USERNAME como From se for email válido
# - Usa SMTP_FROM_EMAIL como From se SMTP_USERNAME for token
# - Adiciona Reply-To quando necessário
# - Inclui headers obrigatórios (Date, Message-ID, X-Mailer)
```

### Configuração de DNS (Produção)

Para evitar que emails sejam marcados como spam:

```dns
# SPF Record
TXT @ "v=spf1 include:_spf.google.com ~all"

# DKIM (configure no provedor)
TXT google._domainkey "v=DKIM1; k=rsa; p=SUA_CHAVE_PUBLICA"

# DMARC
TXT _dmarc "v=DMARC1; p=quarantine; rua=mailto:dmarc@suaempresa.com"
```

## 🚨 Troubleshooting

### Emails marcados como SPAM

**Se seus emails ainda estão indo para spam após as correções:**

1. **Verifique o score de spam**:

   ```bash
   # Teste com Mail Tester
   # Envie um email para: test-xxxxx@mail-tester.com
   python scripts/test_email_system.py --email test-xxxxx@mail-tester.com --type invitation
   ```

2. **Problemas restantes comuns**:
   - `FREEMAIL_FROM` (0.0 pontos): Use domínio profissional em produção
   - `DKIM_ADSP_CUSTOM_MED` (0.0 pontos): Configure DKIM no seu domínio
   - `WEIRD_PORT` (0.0 pontos): Use porta 587 (TLS) ou 465 (SSL)

3. **Configuração recomendada para produção**:

   ```bash
   # Use provedor profissional (SendGrid, Amazon SES)
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=SG.sua_api_key
   SMTP_FROM_EMAIL=noreply@seudominio.com  # Domínio próprio
   ```

### Erro: "Authentication failed"

- ✅ Verifique se a senha de app está correta
- ✅ Confirme se a verificação em duas etapas está ativa
- ✅ Teste com um cliente de email primeiro

### Erro: "Connection refused"

- ✅ Verifique SMTP_HOST e SMTP_PORT
- ✅ Confirme se TLS está configurado corretamente
- ✅ Teste conectividade: `telnet smtp.gmail.com 587`

### Emails não chegam

- ✅ Verifique pasta de spam
- ✅ Confirme se o email de destino está correto
- ✅ Verifique logs do sistema: `docker-compose logs api`

### Rate limiting

- ✅ Gmail: 500 emails/dia para contas gratuitas
- ✅ Use provedores profissionais para volume alto
- ✅ Implemente filas para envios em massa

## 📊 Monitoramento

### Logs Estruturados

O sistema gera logs para:

- `email_sent_successfully`: Email enviado com sucesso
- `email_send_failed`: Falha no envio
- `invitation_email_sent`: Convite enviado
- `welcome_email_sent`: Boas-vindas enviado

### Métricas Recomendadas

- Taxa de entrega de emails
- Emails rejeitados por dia
- Tempo de resposta SMTP
- Convites ativados vs enviados

## 🔄 Próximos Passos

1. **Configure as variáveis de ambiente**
2. **Teste com o script de validação**
3. **Crie um usuário de teste via API**
4. **Configure DNS para produção**
5. **Implemente monitoramento de bounces**

## ✅ Testando as Melhorias Anti-Spam

### Teste Rápido

```bash
# 1. Teste o sistema atualizado
python scripts/test_email_system.py --email seu_email@gmail.com --type invitation

# 2. Verifique se o email chegou na caixa de entrada (não spam)
# 3. Inspecione os headers do email recebido para confirmar:
#    - Date: presente
#    - Message-ID: presente e único
#    - From: usando email autenticado
#    - Reply-To: configurado se SMTP_FROM_EMAIL diferente
```

### Teste com Mail Tester (Recomendado)

```bash
# 1. Acesse https://www.mail-tester.com/
# 2. Copie o email de teste (ex: test-12345@mail-tester.com)
# 3. Execute:
python scripts/test_email_system.py --email test-12345@mail-tester.com --type invitation

# 4. Verifique o score no site (deve ser > 8/10 agora)
```

### Verificação de Headers

Os emails agora incluem automaticamente:

```
Date: Mon, 13 Oct 2025 10:30:00 -0300
Message-ID: <unique-id@gmail.com>
From: Sistema de Documentos Inteligentes <seu_email@gmail.com>
Reply-To: Sistema de Documentos Inteligentes <noreply@suaempresa.com>
X-Mailer: Sistema de Documentos Inteligentes v2.0
MIME-Version: 1.0
```

## 💡 Dicas de Produção

- **Use SendGrid ou Amazon SES** para volume alto
- **Configure webhooks** para tracking de entrega
- **Implemente templates personalizáveis** por prefeitura
- **Adicione unsubscribe links** para compliance
- **Configure backup SMTP** para redundância
