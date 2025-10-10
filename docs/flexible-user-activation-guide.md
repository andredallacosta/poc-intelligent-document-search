# Guia: Ativação Flexível de Usuários

## 🎯 **Problema Resolvido**

**Antes**: Admin precisava "adivinhar" qual método de autenticação o funcionário usaria.

**Agora**: Usuário escolhe como quer se autenticar **no momento da ativação do convite**.

## 🔄 **Novo Fluxo Completo**

### **1. Admin Cria Usuário (Simplificado)**

```javascript
// Frontend - Admin só precisa dos dados básicos
const createUser = async (userData) => {
  const response = await fetch('/api/v1/users/create', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      email: userData.email,
      full_name: userData.full_name,
      role: userData.role,
      primary_municipality_id: currentUser.primary_municipality_id
      // ✅ Não precisa mais definir auth_provider!
    })
  });
  
  return response.json();
};
```

### **2. Sistema Envia Email Genérico**

Email enviado contém:

- Link: `https://sistema.com/activate?token=abc123`
- Texto: "Clique para ativar sua conta e escolher como fazer login"

### **3. Usuário Abre Link e Escolhe**

Página de ativação mostra:

```html
<h2>Como você quer fazer login?</h2>

<div class="auth-options">
  <button onclick="selectEmailPassword()">
    📧 Email e Senha
    <p>Crie uma senha própria</p>
  </button>
  
  <button onclick="selectGoogleAuth()">
    🔍 Conta Google  
    <p>Use sua conta Gmail existente</p>
  </button>
</div>
```

### **4. Ativação Baseada na Escolha**

#### **Opção A: Email/Senha**

```javascript
// Usuário escolhe email/senha
const activateWithPassword = async () => {
  const response = await fetch('/api/v1/auth/activate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      invitation_token: token,
      auth_provider: 'email_password',  // ✅ Escolha do usuário
      password: userPassword
    })
  });
};
```

#### **Opção B: Google OAuth2**

```javascript
// Usuário escolhe Google OAuth2
const activateWithGoogle = async () => {
  // 1. Redireciona para Google
  const googleUrl = await fetch('/api/v1/auth/google');
  window.location.href = googleUrl.auth_url;
  
  // 2. Após retorno do Google, ativa conta
  const response = await fetch('/api/v1/auth/activate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      invitation_token: token,
      auth_provider: 'google_oauth2',  // ✅ Escolha do usuário
      google_token: googleCode
    })
  });
};
```

### **5. Sistema Configura Auth Provider**

Backend automaticamente:

- ✅ Define `auth_provider` baseado na escolha
- ✅ Configura `password_hash` OU `google_id`
- ✅ Ativa conta com método correto
- ✅ Envia emails de confirmação

## 🛠️ **Implementação Técnica**

### **Entidade User Atualizada**

```python
def activate_account(
    self, 
    password_hash: Optional[str] = None,
    auth_provider: Optional[AuthProvider] = None,  # ✅ Novo parâmetro
    google_id: Optional[str] = None
) -> None:
    """Ativa conta com escolha de método de autenticação"""
    
    # Se auth_provider foi fornecido, atualiza (escolha do usuário)
    if auth_provider:
        self.auth_provider = auth_provider

    # Configura baseado na escolha
    if self.auth_provider == AuthProvider.EMAIL_PASSWORD:
        self.password_hash = password_hash
        self.google_id = None
    elif self.auth_provider == AuthProvider.GOOGLE_OAUTH2:
        self.google_id = google_id
        self.password_hash = None

    self.is_active = True
    self.email_verified = True
    # ...
```

### **DTO de Ativação Flexível**

```python
@dataclass
class ActivateUserDTO:
    """DTO para ativação com escolha de método"""
    
    invitation_token: str
    auth_provider: str = "email_password"  # Escolha do usuário
    password: Optional[str] = None         # Para email_password
    google_token: Optional[str] = None     # Para google_oauth2
```

### **Endpoint de Ativação Inteligente**

```python
@router.post("/activate")
async def activate_user_account(request: ActivateUserRequest):
    """Ativa conta com método escolhido pelo usuário"""
    
    # Processa baseado na escolha
    if request.auth_provider == "email_password":
        # Valida senha e configura password_hash
    elif request.auth_provider == "google_oauth2":
        # Valida token Google e extrai google_id
    
    # Ativa conta com configuração correta
    user.activate_account(
        password_hash=password_hash,
        auth_provider=AuthProvider(request.auth_provider),
        google_id=google_id
    )
```

### **Endpoint de Verificação de Convite**

```python
@router.get("/check-invitation/{token}")
async def check_invitation_token(invitation_token: str):
    """Verifica convite antes da ativação - útil para frontend"""
    
    return {
        "valid": True,
        "user_email": user.email,
        "user_name": user.full_name,
        "invited_by": invited_by_name,
        "expires_at": user.invitation_expires_at.isoformat(),
        "message": f"Convite válido para {user.full_name}"
    }
```

## 🎨 **Interface de Usuário**

### **Página de Ativação Responsiva**

Criamos uma página HTML completa (`activate-account.html`) que:

- ✅ **Verifica convite** automaticamente via API
- ✅ **Mostra dados do usuário** (nome, quem convidou)
- ✅ **Apresenta opções visuais** para escolha do método
- ✅ **Formulários dinâmicos** baseados na escolha
- ✅ **Integração Google OAuth2** completa
- ✅ **Feedback visual** de sucesso/erro
- ✅ **Redirecionamento automático** após ativação

### **Fluxo Visual**

```
1. [Loading...] Verificando convite...

2. [User Info] 
   👤 João Silva
   Convidado por: Admin User

3. [Choice]
   📧 Email e Senha     🔍 Conta Google
   [Crie uma senha]     [Use Gmail existente]

4. [Form]
   Senha: [______]      [Continuar com Google]
   [Ativar Conta]

5. [Success]
   ✅ Conta ativada!
   Redirecionando para login...
```

## 🚀 **Vantagens da Implementação**

### **Para o Admin**

- ✅ **Processo simplificado**: Só precisa email + nome + role
- ✅ **Sem decisões técnicas**: Não precisa saber sobre auth providers
- ✅ **Interface limpa**: Formulário mais simples

### **Para o Usuário**

- ✅ **Autonomia total**: Escolhe como quer se autenticar
- ✅ **Experiência moderna**: Interface intuitiva e responsiva
- ✅ **Flexibilidade**: Pode usar Gmail ou criar senha própria
- ✅ **Sem confusão**: Processo guiado passo a passo

### **Para o Sistema**

- ✅ **Arquitetura limpa**: Separação clara de responsabilidades
- ✅ **Flexibilidade futura**: Fácil adicionar novos métodos de auth
- ✅ **Validação robusta**: Verificações em todas as camadas
- ✅ **Logs detalhados**: Auditoria completa do processo

## 📝 **Exemplos de Uso**

### **Cenário 1: Funcionário com Gmail**

1. **Admin**: Cria "João Silva" com email `joao@gmail.com`
2. **Sistema**: Envia email genérico para João
3. **João**: Abre link, vê opções, escolhe "Conta Google"
4. **Sistema**: Redireciona para Google OAuth2
5. **João**: Autoriza no Google, volta para sistema
6. **Sistema**: Ativa conta como `google_oauth2`, envia confirmação
7. **João**: Faz login via "Login com Google"

### **Cenário 2: Funcionário sem Gmail**

1. **Admin**: Cria "Maria Santos" com email `maria@hotmail.com`
2. **Sistema**: Envia email genérico para Maria
3. **Maria**: Abre link, vê opções, escolhe "Email e Senha"
4. **Maria**: Digita senha desejada, clica "Ativar"
5. **Sistema**: Ativa conta como `email_password`, envia confirmação
6. **Maria**: Faz login via email/senha

## 🔧 **Configuração e Deploy**

### **Variáveis de Ambiente**

Nenhuma configuração adicional necessária! O sistema usa as mesmas configurações existentes:

```bash
# JWT (já configurado)
JWT_SECRET=seu_jwt_secret

# Google OAuth2 (já configurado)  
GOOGLE_CLIENT_ID=seu_client_id
GOOGLE_CLIENT_SECRET=seu_client_secret

# Email (já configurado)
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=seu_email
SMTP_PASSWORD=sua_senha_app
```

### **Arquivos Estáticos**

```bash
# Adicione ao servidor web
interface/static/activate-account.html  # Página de ativação
interface/static/oauth2-test.html      # Página de teste (já existe)
```

## 🧪 **Testando o Sistema**

### **1. Criar Usuário (Admin)**

```bash
curl -X POST http://localhost:8000/api/v1/users/create \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@gmail.com",
    "full_name": "Usuário Teste",
    "role": "user",
    "primary_municipality_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

### **2. Verificar Convite**

```bash
curl http://localhost:8000/api/v1/auth/check-invitation/TOKEN_DO_EMAIL
```

### **3. Ativar com Email/Senha**

```bash
curl -X POST http://localhost:8000/api/v1/auth/activate \
  -H "Content-Type: application/json" \
  -d '{
    "invitation_token": "TOKEN_DO_EMAIL",
    "auth_provider": "email_password",
    "password": "minha_senha_123"
  }'
```

### **4. Ativar com Google OAuth2**

```bash
curl -X POST http://localhost:8000/api/v1/auth/activate \
  -H "Content-Type: application/json" \
  -d '{
    "invitation_token": "TOKEN_DO_EMAIL", 
    "auth_provider": "google_oauth2",
    "google_token": "GOOGLE_ID_TOKEN"
  }'
```

## 🎉 **Resultado Final**

Esta implementação transforma o processo de criação de usuários de:

**❌ Complexo**: Admin precisa saber detalhes técnicos
**✅ Simples**: Admin só informa dados básicos, usuário escolhe como quer se autenticar

**❌ Rígido**: Método definido na criação
**✅ Flexível**: Método escolhido na ativação

**❌ Confuso**: Usuário não sabe como foi configurado
**✅ Intuitivo**: Usuário vê opções claras e escolhe

O sistema agora oferece uma **experiência moderna e user-friendly** que coloca o controle nas mãos do usuário final, simplificando o trabalho do admin e garantindo que cada pessoa possa usar o método de autenticação que preferir! 🚀
