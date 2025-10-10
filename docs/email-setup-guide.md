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
   - Acesse: https://myaccount.google.com/apppasswords
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

## 🔒 Segurança

### Boas Práticas

1. **Use senhas de app** em vez de senhas principais
2. **Configure SPF/DKIM** para evitar spam
3. **Use HTTPS** em produção para links seguros
4. **Monitore bounces** e emails rejeitados
5. **Rate limiting** já implementado para evitar spam

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

## 💡 Dicas de Produção

- **Use SendGrid ou Amazon SES** para volume alto
- **Configure webhooks** para tracking de entrega
- **Implemente templates personalizáveis** por prefeitura
- **Adicione unsubscribe links** para compliance
- **Configure backup SMTP** para redundância
