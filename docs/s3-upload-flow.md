# Fluxo de Upload S3 - ADR-002

## 🔄 **Fluxo Completo: Frontend → S3 → Backend**

### **1. Frontend Solicita URL Presigned**

```http
POST /api/v1/documents/upload/presigned
Content-Type: application/json

{
  "filename": "Manual_Redacao_Oficial.pdf",
  "file_size": 52428800,
  "content_type": "application/pdf",
  "title": "Manual de Redação Oficial 2ª Edição",
  "description": "Manual completo de redação oficial",
  "tags": ["ofício", "redação", "manual"]
}
```

**Backend Response:**
```json
{
  "upload_url": "https://s3.us-east-1.amazonaws.com/documents/temp/uuid.pdf?X-Amz-Algorithm=...",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "upload_id": "660e8400-e29b-41d4-a716-446655440001",
  "expires_in": 3600,
  "expires_at": "2024-01-15T11:30:00Z"
}
```

### **2. Frontend Faz Upload Direto para S3**

```javascript
// Frontend JavaScript
const file = document.getElementById('fileInput').files[0];

// Upload direto para S3 usando a URL presigned
const uploadResponse = await fetch(uploadUrl, {
  method: 'PUT',
  body: file,
  headers: {
    'Content-Type': file.type
  }
});

if (uploadResponse.ok) {
  console.log('Upload para S3 concluído!');
  // Agora solicitar processamento
}
```

### **3. Frontend Solicita Processamento**

```http
POST /api/v1/documents/{document_id}/process
Content-Type: application/json

{
  "upload_id": "660e8400-e29b-41d4-a716-446655440001",
  "file_hash": "sha256-hash-opcional"
}
```

**Backend Response:**
```json
{
  "job_id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "uploaded",
  "estimated_time": "2-5 minutes"
}
```

### **4. Backend Processa Documento (Redis Queue)**

#### **4.1. Enfileiramento Redis (NOVO)**
```python
# Backend NÃO processa imediatamente - enfileira no Redis Queue
async def execute(self, request: ProcessDocumentRequestDTO) -> ProcessDocumentResponseDTO:
    # Criar job de processamento
    job = DocumentProcessingJob(...)
    await self.job_repository.save(job)
    
    # 🚀 REDIS QUEUE: Enfileirar processamento assíncrono REAL
    redis_job_id = redis_queue_service.enqueue_document_processing(
        file_upload_id=file_upload.id,
        job_id=job.id,
        priority='normal'
    )
    
    # Salvar ID do job Redis no metadata
    job.metadata['redis_job_id'] = redis_job_id
    await self.job_repository.save(job)
    
    return ProcessDocumentResponseDTO(
        job_id=job.id,
        status=job.status,  # "uploaded" - ainda não processando
        estimated_time="2-5 minutes"
    )
```

#### **4.2. Worker Redis Processa (Background)**
```python
# Worker Redis executa em processo separado
def process_document_job(file_upload_id: str, processing_job_id: str):
    # Download do S3 para arquivo temporário
    with tempfile.NamedTemporaryFile(suffix=file_upload.file_extension, delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    # Worker faz download do S3
    success = await s3_service.download_file(file_upload.s3_key, tmp_path)
    
    # Extrair texto baseado no tipo
    if file_upload.is_pdf:
        text_content = await extract_text_from_pdf(tmp_path)
    # ... outros formatos
    
    return text_content
```

#### **4.3. Pipeline de Processamento (Worker)**
1. **UPLOADED** (0%): Job criado, aguardando worker
2. **EXTRACTING** (5-25%): Worker baixa do S3 e extrai texto
3. **CHECKING_DUPLICATES** (25-35%): Verifica duplicatas por hash
4. **CHUNKING** (35-55%): Divide em chunks com contextualização
5. **EMBEDDING** (55-85%): Gera embeddings OpenAI
6. **COMPLETED** (85-100%): Finaliza e **deleta arquivo do S3**

#### **4.3. Limpeza S3 (CRÍTICO)**
```python
# 🗑️ SEMPRE deletar arquivo do S3 após processamento
async def _cleanup_s3_file(self, file_upload: FileUpload) -> None:
    if not file_upload.s3_key:
        return
    
    success = await self.s3_service.delete_file(file_upload.s3_key)
    if success:
        logger.info(f"Arquivo S3 removido: {file_upload.s3_key.key}")
    
    job.mark_s3_file_deleted()
```

### **5. Frontend Acompanha Progresso**

```javascript
// Polling do status
async function checkProgress(documentId) {
  const response = await fetch(`/api/v1/documents/${documentId}/status`);
  const status = await response.json();
  
  console.log(`Progresso: ${status.progress}% - ${status.current_step}`);
  
  if (status.status === 'completed') {
    console.log('Documento processado com sucesso!');
    return;
  }
  
  if (status.status === 'failed') {
    console.error('Erro no processamento:', status.error);
    return;
  }
  
  // Continuar polling se ainda processando
  if (status.progress < 100) {
    setTimeout(() => checkProgress(documentId), 2000);
  }
}
```

## 🔑 **Pontos Críticos**

### **✅ Vantagens do Fluxo Frontend → S3 + Redis Queue**

1. **Sem sobrecarga do backend**: Upload não passa pelo servidor
2. **Suporte a arquivos grandes**: Até 5GB nativamente
3. **Melhor UX**: Upload paralelo e mais rápido
4. **Escalabilidade**: Backend não processa uploads simultâneos
5. **🚀 Processamento assíncrono REAL**: Redis Queue com workers isolados
6. **Controle de concorrência**: Múltiplos workers simultâneos
7. **Retry automático**: Falhas são reprocessadas automaticamente
8. **Monitoramento completo**: Status de filas e jobs via API

### **⚠️ Responsabilidades Claras**

- **Frontend**: Upload direto para S3 + solicitar processamento
- **Backend API**: Enfileirar jobs no Redis (resposta instantânea)
- **Workers Redis**: Download do S3 + processamento + limpeza
- **S3**: Armazenamento temporário (7 dias máximo)
- **Redis**: Gerenciamento de filas e jobs

### **🗑️ Limpeza Automática**

1. **Após processamento**: Backend sempre deleta arquivo
2. **Lifecycle Policy**: S3 auto-deleta após 7 dias (backup)
3. **Job de limpeza**: Remove arquivos órfãos diariamente

### **🔒 Segurança**

- **Presigned URLs**: Expiram em 1 hora
- **Validação rigorosa**: Apenas PDF, DOC, DOCX
- **Tamanho limitado**: Máximo 5GB por arquivo

## 📊 **Custos S3 Otimizados**

```
Cenário: 1000 documentos/mês
- Upload temporário: ~$0.50/mês
- Downloads para processamento: ~$0.40/mês  
- Deletes após processamento: ~$0.50/mês
- Total S3: ~$1.40/mês (muito baixo)
```

**Documentos finais ficam no PostgreSQL como embeddings, não no S3.**

## 🚀 **Exemplo Completo Frontend**

```javascript
class DocumentUploader {
  async uploadDocument(file, metadata) {
    try {
      // 1. Solicitar URL presigned
      const presignedResponse = await fetch('/api/v1/documents/upload/presigned', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          file_size: file.size,
          content_type: file.type,
          ...metadata
        })
      });
      
      const { upload_url, document_id, upload_id } = await presignedResponse.json();
      
      // 2. Upload direto para S3
      await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': file.type }
      });
      
      // 3. Solicitar processamento
      const processResponse = await fetch(`/api/v1/documents/${document_id}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ upload_id })
      });
      
      const { job_id } = await processResponse.json();
      
      // 4. Acompanhar progresso
      return this.trackProgress(document_id);
      
    } catch (error) {
      console.error('Erro no upload:', error);
      throw error;
    }
  }
  
  async trackProgress(documentId) {
    return new Promise((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const response = await fetch(`/api/v1/documents/${documentId}/status`);
          const status = await response.json();
          
          // Emitir evento de progresso
          this.onProgress?.(status);
          
          if (status.status === 'completed') {
            resolve(status);
          } else if (status.status === 'failed') {
            reject(new Error(status.error));
          } else {
            // Continuar polling
            setTimeout(checkStatus, 2000);
          }
        } catch (error) {
          reject(error);
        }
      };
      
      checkStatus();
    });
  }
}
```

---

## 🔧 **Como Iniciar o Sistema Completo**

### **1. Iniciar Serviços**

```bash
# Terminal 1: API (responde instantaneamente)
make dev

# Terminal 2: Worker Redis (processa jobs em background)
make worker

# Terminal 3: Monitorar filas (opcional)
make queue-info
```

### **2. Testar Fluxo Completo**

```bash
# 1. Solicitar URL presigned
curl -X POST http://localhost:8000/api/v1/documents/upload/presigned \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.pdf", "file_size": 1024, "content_type": "application/pdf"}'

# 2. Upload direto para S3 (frontend faz isso)
# PUT para a URL retornada

# 3. Solicitar processamento (enfileira no Redis)
curl -X POST http://localhost:8000/api/v1/documents/{document_id}/process \
  -H "Content-Type: application/json" \
  -d '{"upload_id": "{upload_id}"}'

# 4. Monitorar progresso
curl http://localhost:8000/api/v1/documents/{document_id}/status

# 5. Verificar filas Redis
curl http://localhost:8000/api/v1/queue/info
```

### **3. Comandos Úteis**

```bash
# Workers
make worker              # Worker padrão (document_processing)
make worker-all          # Worker para todas as filas
make worker-verbose      # Worker com logs detalhados

# Monitoramento
make queue-info          # Status das filas
make queue-health        # Health check

# Limpeza
make cleanup-s3          # Limpeza S3 manual
make cleanup-daily       # Limpeza completa
```

---

**Este fluxo garante processamento assíncrono REAL com Redis Queue, otimizando performance, custos e escalabilidade.**
