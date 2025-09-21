# ADR-001 + Redis Queue - Impacto na Infraestrutura

## 🎯 **Resumo da Situação**

Com a implementação do **Redis Queue** (ADR-002), precisamos reavaliar as decisões de infraestrutura do ADR-001.

### **📋 Decisões Originais ADR-001:**
- **DigitalOcean** em vez de AWS (40% mais barato)
- **PostgreSQL Managed** + **Droplet 2GB** + **Redis local**
- **Custo estimado**: ~$32/mês infra, sobra $68/mês para IA
- **Orçamento total**: R$ 500/mês

## 🔄 **O que Mudou com Redis Queue**

### **✅ Mantemos as Decisões Principais:**

1. **DigitalOcean continua sendo a melhor opção**
   - 40% mais barato que AWS
   - Redis Queue não muda essa vantagem
   - Droplets têm boa performance para workers

2. **PostgreSQL + pgvector mantido**
   - Redis Queue não afeta o banco principal
   - Multi-tenancy e embeddings continuam no PostgreSQL
   - Clean Architecture preservada

3. **Orçamento R$ 500/mês ainda viável**
   - Redis Queue não adiciona custos significativos
   - Workers rodam no mesmo droplet

### **🚀 Novas Necessidades de Infraestrutura:**

#### **1. Redis Mais Robusto**

**Antes (ADR-001):**
```
Redis local (apenas sessões cache)
- Uso: Cache de sessões temporárias
- Criticidade: Baixa (dados não críticos)
- Tamanho: Pequeno
```

**Agora (com Redis Queue):**
```
Redis persistente (sessões + filas de jobs)
- Uso: Cache + Queue management + Job tracking
- Criticidade: ALTA (jobs de processamento)
- Tamanho: Médio (jobs + metadata)
- Persistência: Necessária (não pode perder jobs)
```

#### **2. Configuração de Workers**

**Nova necessidade:**
- Workers Redis executando em background
- Monitoramento de filas
- Restart automático de workers
- Logs estruturados

## 🏗️ **Arquitetura Atualizada**

### **Opção 1: Droplet Único (Recomendada para início)**

```
┌─────────────────────────────────────────┐
│         DigitalOcean Droplet 4GB        │
│                                         │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │   FastAPI   │  │ Redis (persist) │   │
│  │   (port 8000)│  │ - Sessions      │   │
│  └─────────────┘  │ - Job Queues    │   │
│                   │ - Job Status    │   │
│  ┌─────────────┐  └─────────────────┘   │
│  │   Workers   │                        │
│  │ - worker-1  │  ┌─────────────────┐   │
│  │ - worker-2  │  │   Supervisor    │   │
│  │ - cleanup   │  │ (auto-restart)  │   │
│  └─────────────┘  └─────────────────┘   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      PostgreSQL Managed (DO)           │
│   - Documents + Embeddings             │
│   - Multi-tenancy                      │
│   - Job Status                         │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│           AWS S3                        │
│   - Temporary file storage             │
│   - Auto-cleanup after 7 days          │
└─────────────────────────────────────────┘
```

### **Opção 2: Separação de Serviços (Para escala futura)**

```
┌─────────────────┐  ┌─────────────────┐
│   API Droplet   │  │ Worker Droplet  │
│   - FastAPI     │  │ - worker-1      │
│   - Redis       │  │ - worker-2      │
│   (2GB)         │  │ - cleanup       │
└─────────────────┘  │ (2GB)           │
                     └─────────────────┘
```

## 💰 **Impacto nos Custos**

### **Cenário 1: Droplet Único Ampliado**

| Item | ADR-001 Original | Com Redis Queue | Diferença |
|------|------------------|-----------------|-----------|
| **Droplet** | 2GB - $18/mês | 4GB - $24/mês | +$6/mês |
| **PostgreSQL** | Managed - $15/mês | Managed - $15/mês | $0 |
| **Redis** | Local (incluído) | Local (incluído) | $0 |
| **S3** | Não previsto | ~$2/mês | +$2/mês |
| **Total Infra** | ~$33/mês | ~$41/mês | +$8/mês |
| **Sobra para IA** | $67/mês | $59/mês | -$8/mês |

### **Cenário 2: Droplets Separados (Escala)**

| Item | Custo |
|------|-------|
| **API Droplet** | 2GB - $18/mês |
| **Worker Droplet** | 2GB - $18/mês |
| **PostgreSQL** | Managed - $15/mês |
| **S3** | ~$2/mês |
| **Total Infra** | ~$53/mês |
| **Sobra para IA** | $47/mês |

## 🔧 **Configuração Recomendada**

### **Fase 1: Droplet Único (Início)**

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
      - POSTGRES_HOST=${POSTGRES_HOST}
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
  
  worker:
    build: .
    command: python worker.py --all
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
    deploy:
      replicas: 2

volumes:
  redis_data:
```

### **Supervisor para Workers**

```ini
# /etc/supervisor/conf.d/workers.conf
[program:document-worker]
command=/path/to/venv/bin/python worker.py --name document-worker
directory=/path/to/project
user=app
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/document-worker.log

[program:cleanup-worker]
command=/path/to/venv/bin/python worker.py --queues cleanup_tasks --name cleanup-worker
directory=/path/to/project
user=app
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/cleanup-worker.log
```

## 📊 **Monitoramento Necessário**

### **Métricas Redis Queue:**
- Tamanho das filas
- Jobs falhando
- Tempo médio de processamento
- Workers ativos

### **Recursos do Sistema:**
- CPU usage (workers consomem mais)
- Memória Redis (jobs + cache)
- Disk I/O (downloads S3)
- Network (S3 transfers)

### **Alertas Críticos:**
- Worker down
- Fila muito grande (>100 jobs)
- Redis down
- Disk space baixo

## 🎯 **Recomendação Final**

### **Para Começar (Próximos 3-6 meses):**

✅ **Droplet Único 4GB** - $24/mês
- Custo adicional: apenas +$6/mês
- Simplicidade operacional
- Fácil de monitorar
- Suporta até 50 usuários tranquilamente

### **Para Escalar (6+ meses):**

🚀 **Droplets Separados**
- API dedicada (2GB) - $18/mês
- Workers dedicados (2GB) - $18/mês
- Escalabilidade independente
- Isolamento de falhas

### **Configuração Redis:**

```bash
# Redis com persistência
redis-server --appendonly yes --save 900 1 --save 300 10
```

## 📋 **Checklist de Migração**

### **Infraestrutura:**
- [ ] Upgrade Droplet 2GB → 4GB
- [ ] Configurar Redis com persistência
- [ ] Instalar Supervisor para workers
- [ ] Configurar logs estruturados
- [ ] Setup monitoramento básico

### **Deploy:**
- [ ] Docker Compose com Redis
- [ ] Workers como serviços
- [ ] Health checks
- [ ] Backup Redis (jobs críticos)

### **Monitoramento:**
- [ ] Dashboard Redis Queue
- [ ] Alertas Slack/email
- [ ] Métricas de performance
- [ ] Logs centralizados

## 🎉 **Conclusão**

**✅ ADR-001 continua válido com pequenos ajustes:**

1. **DigitalOcean mantido** - Ainda 40% mais barato
2. **PostgreSQL + pgvector mantido** - Core do sistema
3. **Custo adicional mínimo** - Apenas +$6-8/mês
4. **Orçamento R$ 500/mês viável** - Sobra $59/mês para IA
5. **Escalabilidade preservada** - Pode separar droplets depois

**🚀 Redis Queue adiciona valor sem quebrar o orçamento!**

A infraestrutura do ADR-001 suporta perfeitamente o Redis Queue com ajustes mínimos e custo baixo.
