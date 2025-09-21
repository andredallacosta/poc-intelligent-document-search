# Redis Queue - Guia de Uso

## 🎯 **Visão Geral**

O sistema agora usa **Redis Queue (RQ)** para processamento assíncrono real de documentos, seguindo as especificações do ADR-002.

### **✅ O que mudou:**

- ❌ **Antes**: Processamento "assíncrono" falso (bloqueava o servidor)
- ✅ **Agora**: Processamento assíncrono REAL com Redis Queue

## 🚀 **Como Usar**

### **1. Iniciar o Sistema**

```bash
# Terminal 1: Iniciar API
make dev

# Terminal 2: Iniciar Worker Redis
make worker

# Terminal 3: Monitorar filas (opcional)
make queue-info
```

### **2. Fluxo de Upload de Documento**

```bash
# 1. Solicitar URL presigned
curl -X POST http://localhost:8000/api/v1/documents/upload/presigned \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "manual.pdf",
    "file_size": 1048576,
    "content_type": "application/pdf",
    "title": "Manual de Teste"
  }'

# Response:
# {
#   "upload_url": "https://s3.amazonaws.com/...",
#   "document_id": "uuid-1",
#   "upload_id": "uuid-2"
# }

# 2. Upload direto para S3 (frontend faz isso)
curl -X PUT "https://s3.amazonaws.com/..." \
  --data-binary @manual.pdf

# 3. Solicitar processamento (ENFILEIRA NO REDIS)
curl -X POST http://localhost:8000/api/v1/documents/uuid-1/process \
  -H "Content-Type: application/json" \
  -d '{"upload_id": "uuid-2"}'

# Response:
# {
#   "job_id": "uuid-3",
#   "status": "uploaded",
#   "estimated_time": "2-5 minutes"
# }

# 4. Acompanhar progresso
curl http://localhost:8000/api/v1/documents/uuid-1/status
```

### **3. Monitoramento de Filas**

```bash
# Informações das filas
make queue-info

# Health check
make queue-health

# Status de job específico
curl http://localhost:8000/api/v1/queue/job/redis-job-id
```

## 🔧 **Workers**

### **Tipos de Workers**

```bash
# Worker padrão (document_processing)
make worker

# Worker para todas as filas
make worker-all

# Worker apenas para limpeza
make worker-cleanup

# Worker com logs detalhados
make worker-verbose
```

### **Worker em Produção**

```bash
# Executar worker como daemon
nohup python worker.py --all > worker.log 2>&1 &

# Ou usar supervisor/systemd
python worker.py --name production-worker-1
```

## 🗑️ **Tarefas de Limpeza**

### **Limpeza Manual**

```bash
# Limpeza S3 (arquivos > 24h)
make cleanup-s3

# Limpeza de órfãos
make cleanup-orphaned

# Limpeza completa diária
make cleanup-daily
```

### **Limpeza Automática (Cron)**

```bash
# Adicionar ao crontab
crontab -e

# Limpeza diária às 2:00 AM
0 2 * * * cd /path/to/project && source .venv/bin/activate && python scripts/cleanup_scheduler.py --daily

# Limpeza de expirados a cada 6 horas
0 */6 * * * cd /path/to/project && source .venv/bin/activate && python scripts/cleanup_scheduler.py --expired-uploads
```

## 📊 **Endpoints de Monitoramento**

### **Queue Management API**

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/v1/queue/info` | GET | Informações de todas as filas |
| `/api/v1/queue/info/{queue_name}` | GET | Info de fila específica |
| `/api/v1/queue/job/{job_id}` | GET | Status de job Redis |
| `/api/v1/queue/job/{job_id}/cancel` | POST | Cancelar job |
| `/api/v1/queue/job/{job_id}/retry` | POST | Reprocessar job falho |
| `/api/v1/queue/cleanup` | POST | Agendar limpeza |
| `/api/v1/queue/health` | GET | Health check das filas |

### **Exemplo de Response - Queue Info**

```json
[
  {
    "name": "document_processing",
    "length": 3,
    "failed_count": 0,
    "started_count": 1,
    "finished_count": 15,
    "deferred_count": 0
  },
  {
    "name": "cleanup_tasks",
    "length": 0,
    "failed_count": 0,
    "started_count": 0,
    "finished_count": 5,
    "deferred_count": 0
  }
]
```

## 🔍 **Debugging e Troubleshooting**

### **Verificar se Redis está funcionando**

```bash
# Testar conexão Redis
redis-cli ping
# Should return: PONG

# Ver filas ativas
redis-cli keys "rq:queue:*"

# Ver jobs em uma fila
redis-cli llen "rq:queue:document_processing"
```

### **Logs do Worker**

```bash
# Worker com logs detalhados
python worker.py --verbose

# Logs específicos de job
python worker.py --verbose --name debug-worker
```

### **Problemas Comuns**

#### **1. Worker não processa jobs**

```bash
# Verificar se Redis está rodando
redis-cli ping

# Verificar se worker está conectado
python worker.py --verbose
```

#### **2. Jobs ficam travados**

```bash
# Ver jobs em execução
curl http://localhost:8000/api/v1/queue/info

# Cancelar job específico
curl -X POST http://localhost:8000/api/v1/queue/job/JOB_ID/cancel
```

#### **3. Muitos jobs falhando**

```bash
# Ver jobs que falharam
curl http://localhost:8000/api/v1/queue/info/document_processing

# Reprocessar job específico
curl -X POST http://localhost:8000/api/v1/queue/job/JOB_ID/retry
```

## ⚡ **Performance e Escalabilidade**

### **Múltiplos Workers**

```bash
# Terminal 1
python worker.py --name worker-1

# Terminal 2  
python worker.py --name worker-2

# Terminal 3
python worker.py --name worker-3 --queues cleanup_tasks
```

### **Configurações de Performance**

```python
# Em infrastructure/queue/redis_queue.py
self.document_queue = Queue(
    'document_processing', 
    connection=self.redis_conn,
    default_timeout='30m'  # Timeout por job
)
```

### **Monitoramento de Recursos**

```bash
# Ver uso de CPU/memória dos workers
ps aux | grep worker.py

# Monitorar Redis
redis-cli info memory
redis-cli info stats
```

## 🎯 **Diferenças do Sistema Anterior**

| Aspecto | Antes (Síncrono) | Agora (Redis Queue) |
|---------|------------------|---------------------|
| **Processamento** | Bloqueava API | Assíncrono real |
| **Concorrência** | 1 documento por vez | Múltiplos workers |
| **Falhas** | Perdiam processamento | Retry automático |
| **Monitoramento** | Apenas logs | API + Redis stats |
| **Escalabilidade** | Limitada | Horizontal (+ workers) |
| **Isolamento** | Falha afeta API | Workers isolados |

## 🚀 **Próximos Passos**

1. **Configurar monitoramento** (Prometheus + Grafana)
2. **Implementar alertas** (Slack/email para falhas)
3. **Otimizar workers** (batch processing)
4. **Adicionar métricas** (tempo de processamento, throughput)

---

**O sistema agora processa documentos de forma verdadeiramente assíncrona! 🎉**
