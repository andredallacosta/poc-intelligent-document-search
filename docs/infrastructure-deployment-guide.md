# 🏗️ Infrastructure & Deployment Guide

## 📋 **Visão Geral**

Este documento consolida todas as decisões de infraestrutura (ADR-001 + Redis Queue) e define estratégias de deployment para produção.

## 🎯 **Arquitetura Final Definida**

### **Decisões Consolidadas:**
- ✅ **DigitalOcean** (40% mais barato que AWS)
- ✅ **PostgreSQL Managed** + **pgvector** (embeddings + dados relacionais)
- ✅ **Redis persistente** (sessões + filas + jobs)
- ✅ **Droplet 4GB** (API + Workers no mesmo servidor)
- ✅ **AWS S3** (storage temporário de arquivos)
- ✅ **Docker** para API + Workers

### **Custos Finais:**
| Item | Custo Mensal | Observações |
|------|--------------|-------------|
| **Droplet 4GB** | $24/mês | API + Workers + Redis |
| **PostgreSQL Managed** | $15/mês | Backup automático |
| **AWS S3** | ~$2/mês | Storage temporário |
| **Total Infra** | **$41/mês** | ~R$ 205/mês |
| **Sobra para IA** | **$59/mês** | ~R$ 295/mês |
| **Orçamento Total** | **R$ 500/mês** | ✅ Dentro do limite |

## 🐳 **Estratégia de Deployment com Docker**

### **1. FastAPI - Imagem Docker**

#### **Dockerfile para API:**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependências Python
COPY pyproject.toml .
RUN pip install -e .

# Copiar código da aplicação
COPY . .

# Expor porta
EXPOSE 8000

# Comando para API
CMD ["uvicorn", "interface.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### **Docker Compose para Desenvolvimento:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=${POSTGRES_HOST}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - REDIS_DSN=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AWS_ACCESS_KEY=${AWS_ACCESS_KEY}
      - AWS_SECRET_KEY=${AWS_SECRET_KEY}
      - S3_BUCKET=${S3_BUCKET}
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --save 900 1 --save 300 10
    restart: unless-stopped

  worker-documents:
    build: .
    command: python worker.py --queues document_processing --name document-worker
    environment:
      - POSTGRES_HOST=${POSTGRES_HOST}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - REDIS_DSN=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AWS_ACCESS_KEY=${AWS_ACCESS_KEY}
      - AWS_SECRET_KEY=${AWS_SECRET_KEY}
      - S3_BUCKET=${S3_BUCKET}
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    deploy:
      replicas: 2

  worker-cleanup:
    build: .
    command: python worker.py --queues cleanup_tasks --name cleanup-worker
    environment:
      - POSTGRES_HOST=${POSTGRES_HOST}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - REDIS_DSN=redis://redis:6379/0
      - AWS_ACCESS_KEY=${AWS_ACCESS_KEY}
      - AWS_SECRET_KEY=${AWS_SECRET_KEY}
      - S3_BUCKET=${S3_BUCKET}
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

volumes:
  redis_data:
```

### **2. Workers - Mesma Imagem Docker**

#### **Estratégia: Uma Imagem, Múltiplos Comandos**

✅ **Recomendado: Mesma imagem Docker para API e Workers**

**Vantagens:**
- ✅ **Consistência**: Mesmo ambiente para API e Workers
- ✅ **Simplicidade**: Uma imagem para manter
- ✅ **Deploy sincronizado**: Versão única
- ✅ **Dependências idênticas**: Sem conflitos

**Como funciona:**
```bash
# Mesma imagem, comandos diferentes:

# API
docker run app:latest uvicorn interface.main:app --host 0.0.0.0 --port 8000

# Worker Documents
docker run app:latest python worker.py --queues document_processing

# Worker Cleanup
docker run app:latest python worker.py --queues cleanup_tasks
```

#### **Alternativa: Imagens Separadas (NÃO recomendado)**

❌ **Não recomendado para este projeto:**
- Complexidade desnecessária
- Dependências compartilhadas (domain, infrastructure)
- Deploy mais complexo
- Possibilidade de versões desalinhadas

## 🚀 **Deployment em Produção**

### **Opção 1: Docker Compose no Droplet (Recomendada)**

#### **Estrutura no Servidor:**
```
/opt/intelligent-document-search/
├── docker-compose.prod.yml
├── .env.prod
├── nginx/
│   └── nginx.conf
├── logs/
├── backups/
└── scripts/
    ├── deploy.sh
    ├── backup.sh
    └── health-check.sh
```

#### **docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - api
    restart: unless-stopped

  api:
    image: your-registry/intelligent-document-search:latest
    command: uvicorn interface.main:app --host 0.0.0.0 --port 8000 --workers 2
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    env_file:
      - .env.prod
    volumes:
      - ./logs/api:/app/logs
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M

  worker-documents:
    image: your-registry/intelligent-document-search:latest
    command: python worker.py --queues document_processing --name document-worker-${HOSTNAME}
    env_file:
      - .env.prod
    volumes:
      - ./logs/workers:/app/logs
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  worker-cleanup:
    image: your-registry/intelligent-document-search:latest
    command: python worker.py --queues cleanup_tasks --name cleanup-worker-${HOSTNAME}
    env_file:
      - .env.prod
    volumes:
      - ./logs/workers:/app/logs
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M

volumes:
  redis_data:
```

#### **Script de Deploy:**
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "🚀 Iniciando deploy..."

# Backup antes do deploy
./scripts/backup.sh

# Pull da nova imagem
docker-compose -f docker-compose.prod.yml pull

# Deploy com zero downtime
docker-compose -f docker-compose.prod.yml up -d --remove-orphans

# Health check
sleep 10
./scripts/health-check.sh

echo "✅ Deploy concluído!"
```

### **Opção 2: Kubernetes (Futuro)**

Para quando escalar além de 1 servidor:

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: your-registry/intelligent-document-search:latest
        command: ["uvicorn", "interface.main:app", "--host", "0.0.0.0", "--port", "8000"]
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: workers
spec:
  replicas: 4
  selector:
    matchLabels:
      app: workers
  template:
    metadata:
      labels:
        app: workers
    spec:
      containers:
      - name: worker
        image: your-registry/intelligent-document-search:latest
        command: ["python", "worker.py", "--all"]
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
```

## 🔧 **Configuração do Servidor**

### **Setup Inicial do Droplet:**

```bash
#!/bin/bash
# setup-server.sh

# Atualizar sistema
apt update && apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker $USER

# Instalar Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Instalar Nginx (proxy reverso)
apt install nginx -y

# Configurar firewall
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# Criar estrutura de diretórios
mkdir -p /opt/intelligent-document-search/{logs,backups,ssl,scripts}
cd /opt/intelligent-document-search

# Configurar logrotate
cat > /etc/logrotate.d/intelligent-document-search << EOF
/opt/intelligent-document-search/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 root root
}
EOF

echo "✅ Servidor configurado!"
```

### **Nginx Configuration:**

```nginx
# nginx/nginx.conf
upstream api {
    server api:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # API routes
    location /api/ {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long uploads
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }

    # Health check
    location /health {
        proxy_pass http://api/health;
        access_log off;
    }

    # Static files (if needed)
    location /static/ {
        alias /opt/intelligent-document-search/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 📊 **Monitoramento & Logs**

### **Health Checks:**

```bash
#!/bin/bash
# scripts/health-check.sh

API_URL="http://localhost:8000"
REDIS_URL="redis://localhost:6379"

echo "🏥 Verificando saúde dos serviços..."

# API Health
if curl -f -s "$API_URL/health" > /dev/null; then
    echo "✅ API: OK"
else
    echo "❌ API: FALHOU"
    exit 1
fi

# Redis Health
if redis-cli -u "$REDIS_URL" ping | grep -q PONG; then
    echo "✅ Redis: OK"
else
    echo "❌ Redis: FALHOU"
    exit 1
fi

# Queue Health
QUEUE_INFO=$(curl -s "$API_URL/api/v1/queue/health")
if echo "$QUEUE_INFO" | grep -q '"status":"healthy"'; then
    echo "✅ Queue: OK"
else
    echo "❌ Queue: FALHOU"
    exit 1
fi

echo "✅ Todos os serviços OK!"
```

### **Logging Strategy:**

```yaml
# docker-compose.prod.yml (logging section)
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=api"

  worker-documents:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=worker-documents"
```

### **Backup Strategy:**

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/opt/intelligent-document-search/backups"
DATE=$(date +%Y%m%d_%H%M%S)

echo "💾 Iniciando backup..."

# Backup Redis
docker exec redis redis-cli BGSAVE
docker cp redis:/data/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# Backup logs importantes
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" /opt/intelligent-document-search/logs/

# Cleanup backups antigos (manter 7 dias)
find "$BACKUP_DIR" -name "*.rdb" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "✅ Backup concluído!"
```

## 🔄 **CI/CD Pipeline**

### **GitHub Actions:**

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t intelligent-document-search:${{ github.sha }} .
        docker tag intelligent-document-search:${{ github.sha }} intelligent-document-search:latest
    
    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push intelligent-document-search:${{ github.sha }}
        docker push intelligent-document-search:latest
    
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /opt/intelligent-document-search
          docker-compose -f docker-compose.prod.yml pull
          docker-compose -f docker-compose.prod.yml up -d --remove-orphans
          sleep 10
          ./scripts/health-check.sh
```

## 📋 **Checklist de Deploy**

### **Pré-Deploy:**
- [ ] Servidor configurado (Docker, Nginx, firewall)
- [ ] Certificados SSL instalados
- [ ] Variáveis de ambiente configuradas
- [ ] PostgreSQL Managed criado no DigitalOcean
- [ ] Bucket S3 criado na AWS
- [ ] DNS apontando para o droplet

### **Deploy:**
- [ ] Imagem Docker buildada e testada
- [ ] docker-compose.prod.yml configurado
- [ ] Scripts de deploy e health check testados
- [ ] Backup strategy implementada
- [ ] Logs configurados
- [ ] Monitoramento básico ativo

### **Pós-Deploy:**
- [ ] Health checks passando
- [ ] Workers processando jobs
- [ ] API respondendo
- [ ] SSL funcionando
- [ ] Logs sendo gerados
- [ ] Backup automático configurado

## 🎯 **Resumo das Decisões**

### **✅ Arquitetura Final:**
1. **Uma imagem Docker** para API + Workers
2. **Docker Compose** para orquestração
3. **Nginx** como proxy reverso
4. **Droplet 4GB** hospedando tudo
5. **PostgreSQL Managed** externo
6. **Redis local** no droplet

### **✅ Deployment Strategy:**
1. **Build única** para API e Workers
2. **Comandos diferentes** na mesma imagem
3. **Zero downtime** com Docker Compose
4. **Health checks** automáticos
5. **Backup** e **logs** estruturados

### **✅ Custos Finais:**
- **Total: $41/mês** (~R$ 205/mês)
- **Sobra: $59/mês** para IA (~R$ 295/mês)
- **Orçamento: R$ 500/mês** ✅ Respeitado

**🚀 Infraestrutura pronta para produção com alta disponibilidade e baixo custo!**
