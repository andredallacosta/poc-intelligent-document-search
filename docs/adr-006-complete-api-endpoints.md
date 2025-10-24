# ADR 006 — Endpoints Faltantes para Frontend Completo

## Status

🚧 **PLANEJADO** (Sprint 2025.1)

## Contexto

Durante a análise para desenvolvimento do frontend React, identificamos **gaps críticos** na API que impedem a criação de interfaces modernas e completas. Atualmente, o backend possui funcionalidades base implementadas, mas falta exposição de dados essenciais via API.

### **Problemas Identificados**

#### **1. Gerenciamento de Documentos - Incompleto**

**Situação Atual:**
- ✅ Upload com URL presigned funcionando
- ✅ Processamento assíncrono via Redis Queue
- ✅ Status de processamento disponível
- ❌ **Sem listagem de documentos** processados
- ❌ **Sem busca manual** (apenas via chat)
- ❌ **Sem visualização de detalhes** completos
- ❌ **Sem estatísticas** de uso
- ❌ **Sem exclusão/edição** de documentos

**Impacto no Frontend:**
- Impossível criar biblioteca de documentos
- Usuário não vê histórico de uploads
- Admin não consegue gerenciar documentos
- Sem dashboard de documentos

#### **2. Sessões de Chat - Gerenciamento Ausente**

**Situação Atual:**
- ✅ Chat funcionando com sessões Redis
- ✅ Continuidade de conversa por session_id
- ❌ **Sem listagem de sessões** do usuário
- ❌ **Sem histórico de conversas** antigas
- ❌ **Sem renomear/deletar** sessões
- ❌ **Sem exportar** conversas
- ❌ **Sem buscar** em conversas antigas

**Impacto no Frontend:**
- Impossível criar interface tipo ChatGPT
- Usuário perde conversas antigas
- Sem organização de conversas
- UX inferior

#### **3. Prefeituras - CRUD Incompleto**

**Situação Atual:**
- ✅ Criar prefeitura (POST)
- ✅ Listar prefeituras (GET)
- ✅ Ver detalhes (GET by ID)
- ❌ **Sem atualizar** dados (PUT/PATCH)
- ❌ **Sem desativar/ativar** (PATCH)
- ❌ **Sem histórico** de consumo detalhado
- ❌ **Sem relatórios** mensais
- ❌ **Sem listar documentos** da prefeitura

**Impacto no Frontend:**
- Admin não consegue editar dados
- Sem controle de inadimplência
- Sem auditoria de consumo
- Sem visão de uso por prefeitura

#### **4. Dashboard e Métricas - Ausente**

**Situação Atual:**
- ✅ Estatísticas básicas (GET /admin/stats)
- ❌ **Sem métricas de uso** por período
- ❌ **Sem documentos mais consultados**
- ❌ **Sem usuários mais ativos**
- ❌ **Sem gráficos** de consumo
- ❌ **Sem tempo médio** de resposta
- ❌ **Sem taxa de sucesso/falha**
- ❌ **Sem relatórios** exportáveis

**Impacto no Frontend:**
- Dashboard pobre para admins
- Sem análise de performance
- Sem insights de negócio
- Sem relatórios gerenciais

#### **5. Notificações - Sistema Ausente**

**Situação Atual:**
- ❌ **Sem notificações** em tempo real
- ❌ **Sem alertas** de limite de tokens
- ❌ **Sem notificar** documento processado
- ❌ **Sem histórico** de notificações
- ❌ **Sem preferências** de notificação

**Impacto no Frontend:**
- UX sem alertas proativos
- Usuário não sabe quando documento está pronto
- Admin não recebe alertas críticos
- Interface menos moderna

## Decisão

Implementar **endpoints complementares** organizados em 5 fases, mantendo Clean Architecture e sem quebrar APIs existentes.

### **Princípios da Implementação**

1. **Retrocompatibilidade**: Não alterar endpoints existentes
2. **Clean Architecture**: Seguir camadas Domain → Application → Infrastructure → Interface
3. **RESTful**: Seguir convenções REST e HTTP semânticas
4. **Paginação**: Todos os endpoints de listagem devem suportar paginação
5. **Filtros**: Permitir filtros flexíveis via query params
6. **Performance**: Usar índices PostgreSQL e cache Redis quando apropriado
7. **Auditoria**: Registrar todas as operações críticas

---

## Implementação Detalhada

### **FASE 1: Gerenciamento Completo de Documentos**

#### **1.1. Listar Documentos (Implementar)**

```http
GET /api/v1/documents
Authorization: Bearer {token}
Query Params:
  - search: string (busca em título/descrição)
  - tags: string[] (filtrar por tags)
  - status: string (uploaded|processing|completed|failed)
  - municipality_id: UUID (apenas superuser)
  - limit: int (default 20, max 100)
  - offset: int (default 0)
  - sort_by: string (created_at|title|file_size)
  - sort_order: string (asc|desc)

Response 200:
{
  "documents": [
    {
      "id": "uuid",
      "title": "Manual de Redação",
      "description": "Manual completo",
      "source": "manual_redacao.pdf",
      "content_type": "application/pdf",
      "file_size": 52428800,
      "status": "completed",
      "tags": ["ofício", "redação"],
      "chunks_count": 45,
      "embeddings_count": 45,
      "uploaded_by": {
        "id": "uuid",
        "full_name": "João Silva"
      },
      "municipality_id": "uuid",
      "created_at": "2025-10-24T10:00:00Z",
      "updated_at": "2025-10-24T10:05:00Z",
      "processed_at": "2025-10-24T10:05:00Z"
    }
  ],
  "total": 150,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

**Implementação:**
- Domain: Adicionar métodos ao `DocumentRepository`
- Application: Criar `ListDocumentsUseCase`
- Infrastructure: Implementar query com filtros e paginação
- Interface: Atualizar endpoint existente

#### **1.2. Obter Documento Específico (Implementar)**

```http
GET /api/v1/documents/{document_id}
Authorization: Bearer {token}

Response 200:
{
  "id": "uuid",
  "title": "Manual de Redação",
  "description": "Manual completo de redação oficial",
  "source": "manual_redacao.pdf",
  "content_type": "application/pdf",
  "file_size": 52428800,
  "status": "completed",
  "tags": ["ofício", "redação", "manual"],
  "chunks": [
    {
      "id": "uuid",
      "chunk_index": 0,
      "content": "Texto do chunk...",
      "metadata": {
        "page": 1,
        "section": "Introdução"
      }
    }
  ],
  "chunks_count": 45,
  "embeddings_count": 45,
  "uploaded_by": {
    "id": "uuid",
    "full_name": "João Silva",
    "email": "joao@exemplo.com"
  },
  "municipality": {
    "id": "uuid",
    "name": "Prefeitura de São Paulo"
  },
  "processing_info": {
    "job_id": "uuid",
    "processing_time": 120.5,
    "completed_at": "2025-10-24T10:05:00Z"
  },
  "usage_stats": {
    "times_referenced": 150,
    "last_referenced": "2025-10-24T15:30:00Z"
  },
  "created_at": "2025-10-24T10:00:00Z",
  "updated_at": "2025-10-24T10:05:00Z"
}

Response 404:
{
  "error": "document_not_found",
  "message": "Documento não encontrado",
  "code": "DOCUMENT_NOT_FOUND"
}
```

**Implementação:**
- Domain: Método `find_by_id_with_details()` no repository
- Application: `GetDocumentDetailsUseCase`
- Infrastructure: Query com JOINs (user, municipality, chunks)
- Interface: Atualizar endpoint existente

#### **1.3. Atualizar Documento**

```http
PATCH /api/v1/documents/{document_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Novo Título",
  "description": "Nova descrição",
  "tags": ["nova", "tag"]
}

Response 200:
{
  "id": "uuid",
  "title": "Novo Título",
  "description": "Nova descrição",
  "tags": ["nova", "tag"],
  "updated_at": "2025-10-24T16:00:00Z"
}

Permissões:
- USER: Apenas próprios documentos
- ADMIN: Documentos da sua prefeitura
- SUPERUSER: Qualquer documento
```

**Implementação:**
- Domain: Método `update_metadata()` na entidade Document
- Application: `UpdateDocumentMetadataUseCase`
- Infrastructure: UPDATE no PostgreSQL com validação de permissões
- Interface: Novo endpoint PATCH

#### **1.4. Deletar Documento**

```http
DELETE /api/v1/documents/{document_id}
Authorization: Bearer {token}

Response 200:
{
  "message": "Documento deletado com sucesso",
  "document_id": "uuid",
  "chunks_deleted": 45,
  "embeddings_deleted": 45
}

Response 404:
{
  "error": "document_not_found",
  "message": "Documento não encontrado"
}

Permissões:
- USER: Não permitido
- ADMIN: Documentos da sua prefeitura
- SUPERUSER: Qualquer documento
```

**Implementação:**
- Domain: Soft delete na entidade Document
- Application: `DeleteDocumentUseCase`
- Infrastructure: 
  - Soft delete (is_deleted = true)
  - Deletar chunks e embeddings do pgvector
  - Auditoria da operação
- Interface: Novo endpoint DELETE

#### **1.5. Busca Semântica Manual (Implementar)**

```http
POST /api/v1/documents/search
Authorization: Bearer {token}
Content-Type: application/json

{
  "query": "como escrever ofício",
  "limit": 10,
  "min_similarity": 0.7,
  "filters": {
    "document_ids": ["uuid1", "uuid2"],
    "tags": ["ofício"],
    "municipality_id": "uuid"  // apenas superuser
  }
}

Response 200:
{
  "results": [
    {
      "document_id": "uuid",
      "chunk_id": "uuid",
      "document_title": "Manual de Redação",
      "source": "manual_redacao.pdf",
      "page": 15,
      "similarity_score": 0.89,
      "content": "Para escrever um ofício oficial...",
      "metadata": {
        "section": "Ofícios",
        "chapter": 3
      }
    }
  ],
  "query": "como escrever ofício",
  "total_results": 15,
  "showing": 10,
  "query_time": 0.12,
  "total_chunks_searched": 1500
}
```

**Implementação:**
- Domain: Usar `VectorRepository` existente
- Application: `SearchDocumentsUseCase`
- Infrastructure: Query pgvector com filtros
- Interface: Implementar endpoint existente

#### **1.6. Estatísticas de Documentos (Implementar)**

```http
GET /api/v1/documents/stats
Authorization: Bearer {token}
Query Params:
  - municipality_id: UUID (opcional, apenas superuser)
  - start_date: date (opcional)
  - end_date: date (opcional)

Response 200:
{
  "total_documents": 150,
  "by_status": {
    "completed": 140,
    "processing": 5,
    "failed": 5
  },
  "total_chunks": 6750,
  "total_embeddings": 6750,
  "storage_used_mb": 450.5,
  "by_type": {
    "pdf": 120,
    "docx": 25,
    "doc": 5
  },
  "by_content_type": {
    "application/pdf": 120,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": 25
  },
  "processing_stats": {
    "average_processing_time_seconds": 125.5,
    "success_rate": 93.3,
    "total_processed_today": 12,
    "total_processed_this_month": 45
  },
  "top_documents": [
    {
      "document_id": "uuid",
      "title": "Manual de Redação",
      "times_referenced": 1500,
      "last_referenced": "2025-10-24T15:30:00Z"
    }
  ],
  "recent_uploads": [
    {
      "document_id": "uuid",
      "title": "Documento Recente",
      "uploaded_at": "2025-10-24T10:00:00Z",
      "uploaded_by": "João Silva"
    }
  ]
}
```

**Implementação:**
- Application: `GetDocumentStatisticsUseCase`
- Infrastructure: 
  - Aggregations no PostgreSQL
  - Cache Redis (TTL 5 minutos)
- Interface: Implementar endpoint existente

---

### **FASE 2: Gerenciamento de Sessões de Chat**

#### **2.1. Listar Sessões do Usuário**

```http
GET /api/v1/chat/sessions
Authorization: Bearer {token}
Query Params:
  - limit: int (default 20, max 100)
  - offset: int (default 0)
  - sort_by: string (created_at|updated_at|message_count)
  - sort_order: string (asc|desc)

Response 200:
{
  "sessions": [
    {
      "id": "uuid",
      "title": "Como escrever ofícios",  // gerado automaticamente ou personalizado
      "message_count": 15,
      "first_message_preview": "Como escrever um ofício oficial?",
      "last_message_at": "2025-10-24T15:30:00Z",
      "created_at": "2025-10-24T10:00:00Z",
      "token_usage_total": 5000
    }
  ],
  "total": 50,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

**Implementação:**
- Domain: 
  - Nova entidade `ChatSession` persistida (atualmente só Redis)
  - Repository `ChatSessionRepository`
- Application: `ListChatSessionsUseCase`
- Infrastructure: 
  - Tabela `chat_sessions` no PostgreSQL
  - Manter Redis para mensagens (performance)
  - Sync Redis → PostgreSQL após cada conversa
- Interface: Novo endpoint GET

#### **2.2. Obter Histórico de Sessão**

```http
GET /api/v1/chat/sessions/{session_id}
Authorization: Bearer {token}
Query Params:
  - limit: int (default 50)
  - offset: int (default 0)

Response 200:
{
  "session_id": "uuid",
  "title": "Como escrever ofícios",
  "created_at": "2025-10-24T10:00:00Z",
  "updated_at": "2025-10-24T15:30:00Z",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "content": "Como escrever um ofício oficial?",
      "created_at": "2025-10-24T10:00:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "content": "Para escrever um ofício oficial...",
      "sources": [
        {
          "document_id": "uuid",
          "source": "manual_redacao.pdf",
          "page": 15,
          "similarity_score": 0.89
        }
      ],
      "token_usage": {
        "prompt_tokens": 150,
        "completion_tokens": 75,
        "total_tokens": 225
      },
      "created_at": "2025-10-24T10:00:05Z"
    }
  ],
  "message_count": 15,
  "total_token_usage": 5000,
  "has_more": false
}

Response 404:
{
  "error": "session_not_found",
  "message": "Sessão não encontrada"
}
```

**Implementação:**
- Application: `GetChatSessionHistoryUseCase`
- Infrastructure: 
  - Buscar do Redis primeiro (cache)
  - Fallback PostgreSQL se Redis expirou
- Interface: Novo endpoint GET

#### **2.3. Renomear Sessão**

```http
PATCH /api/v1/chat/sessions/{session_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "Novo título da conversa"
}

Response 200:
{
  "session_id": "uuid",
  "title": "Novo título da conversa",
  "updated_at": "2025-10-24T16:00:00Z"
}
```

**Implementação:**
- Domain: Método `update_title()` em ChatSession
- Application: `UpdateChatSessionUseCase`
- Infrastructure: UPDATE PostgreSQL + Redis
- Interface: Novo endpoint PATCH

#### **2.4. Deletar Sessão**

```http
DELETE /api/v1/chat/sessions/{session_id}
Authorization: Bearer {token}

Response 200:
{
  "message": "Sessão deletada com sucesso",
  "session_id": "uuid",
  "messages_deleted": 15
}
```

**Implementação:**
- Application: `DeleteChatSessionUseCase`
- Infrastructure: 
  - Soft delete no PostgreSQL
  - Deletar do Redis
- Interface: Novo endpoint DELETE

#### **2.5. Exportar Conversa**

```http
GET /api/v1/chat/sessions/{session_id}/export
Authorization: Bearer {token}
Query Params:
  - format: string (json|txt|pdf)

Response 200:
Content-Type: application/json | text/plain | application/pdf

// JSON
{
  "session_id": "uuid",
  "title": "Como escrever ofícios",
  "exported_at": "2025-10-24T16:00:00Z",
  "messages": [...],
  "metadata": {
    "total_messages": 15,
    "total_tokens": 5000
  }
}

// TXT
Conversa: Como escrever ofícios
Data: 24/10/2025

[Você]: Como escrever um ofício oficial?
[Assistente]: Para escrever um ofício oficial...

// PDF (gerado dinamicamente)
```

**Implementação:**
- Application: `ExportChatSessionUseCase`
- Infrastructure: 
  - JSON: Serialização direta
  - TXT: Template simples
  - PDF: Biblioteca ReportLab ou WeasyPrint
- Interface: Novo endpoint GET

#### **2.6. Buscar em Conversas**

```http
GET /api/v1/chat/sessions/search
Authorization: Bearer {token}
Query Params:
  - query: string (busca em mensagens)
  - limit: int (default 20)
  - offset: int (default 0)

Response 200:
{
  "results": [
    {
      "session_id": "uuid",
      "session_title": "Como escrever ofícios",
      "message_id": "uuid",
      "message_role": "user",
      "message_content": "Como escrever um ofício oficial?",
      "message_created_at": "2025-10-24T10:00:00Z",
      "match_highlight": "...escrever um <mark>ofício</mark> oficial..."
    }
  ],
  "total": 50,
  "query_time": 0.05
}
```

**Implementação:**
- Application: `SearchChatSessionsUseCase`
- Infrastructure: 
  - PostgreSQL Full Text Search (tsvector)
  - Índice GIN para performance
- Interface: Novo endpoint GET

---

### **FASE 3: CRUD Completo de Prefeituras**

#### **3.1. Atualizar Prefeitura**

```http
PATCH /api/v1/admin/municipalities/{municipality_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Novo Nome",
  "token_quota": 100000,
  "monthly_token_limit": 50000,
  "active": true
}

Response 200:
{
  "id": "uuid",
  "name": "Novo Nome",
  "token_quota": 100000,
  "monthly_token_limit": 50000,
  "active": true,
  "updated_at": "2025-10-24T16:00:00Z"
}

Permissões:
- USER: Não permitido
- ADMIN: Não permitido
- SUPERUSER: Permitido
```

**Implementação:**
- Domain: Métodos `update_name()`, `update_quota()` em Municipality
- Application: `UpdateMunicipalityUseCase`
- Infrastructure: UPDATE PostgreSQL com auditoria
- Interface: Novo endpoint PATCH

#### **3.2. Desativar/Ativar Prefeitura**

```http
PATCH /api/v1/admin/municipalities/{municipality_id}/status
Authorization: Bearer {token}
Content-Type: application/json

{
  "active": false,
  "reason": "Inadimplência"
}

Response 200:
{
  "id": "uuid",
  "name": "Prefeitura de São Paulo",
  "active": false,
  "deactivated_at": "2025-10-24T16:00:00Z",
  "deactivation_reason": "Inadimplência"
}

Efeito:
- Bloqueia chat para todos os usuários
- Mantém dados históricos
- Permite reativação
```

**Implementação:**
- Domain: Métodos `deactivate()`, `activate()` em Municipality
- Application: `ToggleMunicipalityStatusUseCase`
- Infrastructure: 
  - UPDATE PostgreSQL
  - Invalidar cache Redis
  - Auditoria
- Interface: Novo endpoint PATCH

#### **3.3. Histórico de Consumo Detalhado**

```http
GET /api/v1/admin/municipalities/{municipality_id}/consumption
Authorization: Bearer {token}
Query Params:
  - start_date: date (default: início do mês)
  - end_date: date (default: hoje)
  - group_by: string (day|week|month)

Response 200:
{
  "municipality_id": "uuid",
  "municipality_name": "Prefeitura de São Paulo",
  "period": {
    "start": "2025-10-01",
    "end": "2025-10-24"
  },
  "consumption_by_period": [
    {
      "date": "2025-10-01",
      "tokens_consumed": 1500,
      "messages_sent": 50,
      "documents_referenced": 25
    },
    {
      "date": "2025-10-02",
      "tokens_consumed": 2000,
      "messages_sent": 67,
      "documents_referenced": 30
    }
  ],
  "consumption_by_user": [
    {
      "user_id": "uuid",
      "user_name": "João Silva",
      "tokens_consumed": 5000,
      "messages_sent": 150
    }
  ],
  "top_documents": [
    {
      "document_id": "uuid",
      "document_title": "Manual de Redação",
      "times_referenced": 500
    }
  ],
  "totals": {
    "total_tokens": 45000,
    "total_messages": 1500,
    "average_tokens_per_message": 30
  }
}
```

**Implementação:**
- Application: `GetMunicipalityConsumptionUseCase`
- Infrastructure: 
  - Aggregations PostgreSQL
  - JOINs (messages, users, documents)
  - Cache Redis (TTL 1 hora)
- Interface: Novo endpoint GET

#### **3.4. Relatório Mensal**

```http
GET /api/v1/admin/municipalities/{municipality_id}/reports/monthly
Authorization: Bearer {token}
Query Params:
  - year: int (default: ano atual)
  - month: int (default: mês atual)
  - format: string (json|pdf)

Response 200 (JSON):
{
  "municipality_id": "uuid",
  "municipality_name": "Prefeitura de São Paulo",
  "report_period": "2025-10",
  "generated_at": "2025-10-31T23:59:59Z",
  
  "summary": {
    "total_tokens_consumed": 45000,
    "total_messages": 1500,
    "total_documents": 150,
    "active_users": 25,
    "new_users": 5
  },
  
  "usage_by_day": [...],
  "usage_by_user": [...],
  "top_documents": [...],
  
  "billing": {
    "base_limit": 20000,
    "extra_credits_purchased": 10000,
    "total_available": 30000,
    "consumed": 25000,
    "remaining": 5000,
    "overage": 0,
    "estimated_cost_usd": 7.50
  }
}

Response 200 (PDF):
Content-Type: application/pdf
Content-Disposition: attachment; filename="relatorio_2025-10.pdf"
[PDF Binary]
```

**Implementação:**
- Application: `GenerateMunicipalityReportUseCase`
- Infrastructure: 
  - Aggregations complexas
  - Template PDF com gráficos (ReportLab)
  - Cache gerado (não regenerar sempre)
- Interface: Novo endpoint GET

#### **3.5. Listar Documentos da Prefeitura**

```http
GET /api/v1/admin/municipalities/{municipality_id}/documents
Authorization: Bearer {token}
Query Params:
  - limit: int
  - offset: int
  - status: string
  - sort_by: string

Response 200:
{
  "municipality_id": "uuid",
  "municipality_name": "Prefeitura de São Paulo",
  "documents": [...],  // igual ao GET /documents
  "total": 150,
  "has_more": true
}
```

**Implementação:**
- Application: Reutilizar `ListDocumentsUseCase` com filtro
- Interface: Novo endpoint GET

---

### **FASE 4: Dashboard e Métricas Avançadas**

#### **4.1. Métricas de Uso por Período**

```http
GET /api/v1/analytics/usage
Authorization: Bearer {token}
Query Params:
  - start_date: date
  - end_date: date
  - group_by: string (hour|day|week|month)
  - municipality_id: UUID (opcional, apenas superuser)

Response 200:
{
  "period": {
    "start": "2025-10-01",
    "end": "2025-10-24",
    "group_by": "day"
  },
  "metrics": [
    {
      "date": "2025-10-01",
      "messages_sent": 150,
      "tokens_consumed": 4500,
      "documents_uploaded": 5,
      "unique_users": 25,
      "average_response_time_seconds": 2.3,
      "success_rate": 98.5
    }
  ],
  "totals": {
    "total_messages": 3600,
    "total_tokens": 108000,
    "total_documents": 120,
    "total_unique_users": 50
  }
}
```

**Implementação:**
- Domain: Novo repository `AnalyticsRepository`
- Application: `GetUsageMetricsUseCase`
- Infrastructure: 
  - Time-series queries PostgreSQL
  - Cache Redis (TTL variável)
- Interface: Novo módulo `/analytics`

#### **4.2. Documentos Mais Consultados**

```http
GET /api/v1/analytics/top-documents
Authorization: Bearer {token}
Query Params:
  - start_date: date
  - end_date: date
  - limit: int (default 10)
  - municipality_id: UUID (opcional)

Response 200:
{
  "period": {
    "start": "2025-10-01",
    "end": "2025-10-24"
  },
  "top_documents": [
    {
      "rank": 1,
      "document_id": "uuid",
      "title": "Manual de Redação",
      "source": "manual_redacao.pdf",
      "times_referenced": 1500,
      "unique_users": 45,
      "average_similarity_score": 0.85,
      "last_referenced": "2025-10-24T15:30:00Z"
    }
  ]
}
```

**Implementação:**
- Application: `GetTopDocumentsUseCase`
- Infrastructure: Aggregation com COUNT e DISTINCT
- Interface: Endpoint no módulo `/analytics`

#### **4.3. Usuários Mais Ativos**

```http
GET /api/v1/analytics/top-users
Authorization: Bearer {token}
Query Params:
  - start_date: date
  - end_date: date
  - limit: int (default 10)
  - municipality_id: UUID (opcional)

Response 200:
{
  "period": {
    "start": "2025-10-01",
    "end": "2025-10-24"
  },
  "top_users": [
    {
      "rank": 1,
      "user_id": "uuid",
      "full_name": "João Silva",
      "email": "joao@exemplo.com",
      "messages_sent": 350,
      "tokens_consumed": 10500,
      "sessions_created": 25,
      "last_activity": "2025-10-24T15:30:00Z"
    }
  ]
}
```

**Implementação:**
- Application: `GetTopUsersUseCase`
- Infrastructure: Aggregation com GROUP BY user_id
- Interface: Endpoint no módulo `/analytics`

#### **4.4. Performance da IA**

```http
GET /api/v1/analytics/ai-performance
Authorization: Bearer {token}
Query Params:
  - start_date: date
  - end_date: date
  - municipality_id: UUID (opcional)

Response 200:
{
  "period": {
    "start": "2025-10-01",
    "end": "2025-10-24"
  },
  "performance": {
    "average_response_time_seconds": 2.3,
    "median_response_time_seconds": 2.1,
    "p95_response_time_seconds": 3.5,
    "p99_response_time_seconds": 5.0,
    "success_rate": 98.5,
    "error_rate": 1.5,
    "timeout_rate": 0.5
  },
  "token_usage": {
    "average_tokens_per_message": 30,
    "average_prompt_tokens": 150,
    "average_completion_tokens": 75,
    "total_tokens": 108000,
    "estimated_cost_usd": 32.40
  },
  "quality_metrics": {
    "average_similarity_score": 0.82,
    "sources_used_average": 2.5,
    "messages_with_sources": 95.0
  }
}
```

**Implementação:**
- Application: `GetAIPerformanceMetricsUseCase`
- Infrastructure: 
  - Aggregations estatísticas
  - Percentis (P95, P99)
  - Cache Redis
- Interface: Endpoint no módulo `/analytics`

#### **4.5. Exportar Relatórios**

```http
POST /api/v1/analytics/reports/generate
Authorization: Bearer {token}
Content-Type: application/json

{
  "report_type": "usage_summary|detailed_usage|cost_analysis|user_activity",
  "format": "json|csv|pdf|xlsx",
  "filters": {
    "start_date": "2025-10-01",
    "end_date": "2025-10-24",
    "municipality_id": "uuid"  // opcional
  }
}

Response 202 (Accepted):
{
  "job_id": "uuid",
  "status": "processing",
  "estimated_time": "30 seconds"
}

// Polling
GET /api/v1/analytics/reports/{job_id}

Response 200 (completed):
{
  "job_id": "uuid",
  "status": "completed",
  "download_url": "https://api.example.com/analytics/reports/download/uuid",
  "expires_at": "2025-10-25T10:00:00Z",
  "file_size": 524288
}

// Download
GET /api/v1/analytics/reports/download/{job_id}
Response 200:
Content-Type: application/pdf | text/csv | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="report_2025-10.pdf"
[Binary Data]
```

**Implementação:**
- Application: 
  - `GenerateReportUseCase`
  - `GetReportStatusUseCase`
- Infrastructure: 
  - Redis Queue para processamento
  - Worker gera relatório
  - S3 temporário para download (7 dias)
  - Bibliotecas: pandas, openpyxl, ReportLab
- Interface: Novo módulo `/analytics/reports`

---

### **FASE 5: Sistema de Notificações**

#### **5.1. Listar Notificações do Usuário**

```http
GET /api/v1/notifications
Authorization: Bearer {token}
Query Params:
  - unread_only: bool (default false)
  - limit: int (default 20)
  - offset: int (default 0)
  - type: string (filtrar por tipo)

Response 200:
{
  "notifications": [
    {
      "id": "uuid",
      "type": "token_warning",  // token_warning, token_exceeded, document_completed, document_failed, user_invited, user_activated
      "title": "Limite de tokens próximo",
      "message": "Sua prefeitura consumiu 85% do limite mensal",
      "severity": "warning",  // info, warning, error, success
      "data": {
        "municipality_id": "uuid",
        "usage_percentage": 85.0,
        "remaining_tokens": 3000
      },
      "action_url": "/admin/tokens",
      "is_read": false,
      "created_at": "2025-10-24T15:30:00Z",
      "expires_at": "2025-10-31T23:59:59Z"
    }
  ],
  "unread_count": 5,
  "total": 50,
  "has_more": true
}
```

**Implementação:**
- Domain: 
  - Entidade `Notification`
  - Repository `NotificationRepository`
- Infrastructure: 
  - Tabela `notifications`
  - Índices (user_id, is_read, created_at)
- Interface: Novo módulo `/notifications`

#### **5.2. Marcar como Lida**

```http
PATCH /api/v1/notifications/{notification_id}/read
Authorization: Bearer {token}

Response 200:
{
  "id": "uuid",
  "is_read": true,
  "read_at": "2025-10-24T16:00:00Z"
}

// Marcar todas como lidas
POST /api/v1/notifications/mark-all-read
Response 200:
{
  "marked_count": 5
}
```

**Implementação:**
- Application: 
  - `MarkNotificationAsReadUseCase`
  - `MarkAllNotificationsAsReadUseCase`
- Infrastructure: UPDATE PostgreSQL
- Interface: Endpoints PATCH e POST

#### **5.3. Deletar Notificação**

```http
DELETE /api/v1/notifications/{notification_id}
Authorization: Bearer {token}

Response 200:
{
  "message": "Notificação deletada"
}
```

#### **5.4. Preferências de Notificação**

```http
GET /api/v1/notifications/preferences
Authorization: Bearer {token}

Response 200:
{
  "email_notifications": true,
  "push_notifications": false,
  "notification_types": {
    "token_warning": true,
    "token_exceeded": true,
    "document_completed": true,
    "document_failed": false,
    "user_invited": true,
    "user_activated": false
  }
}

PATCH /api/v1/notifications/preferences
{
  "email_notifications": false,
  "notification_types": {
    "document_completed": false
  }
}
```

**Implementação:**
- Domain: Value object `NotificationPreferences` no User
- Application: `UpdateNotificationPreferencesUseCase`
- Infrastructure: JSON column no PostgreSQL
- Interface: Endpoints GET e PATCH

#### **5.5. WebSocket para Notificações em Tempo Real**

```python
# WebSocket endpoint
WS /api/v1/notifications/ws
Authorization: Bearer {token} (via query param ou header)

# Client conecta
ws = new WebSocket('ws://localhost:8000/api/v1/notifications/ws?token=...')

# Server envia quando nova notificação
{
  "type": "notification",
  "data": {
    "id": "uuid",
    "type": "document_completed",
    "title": "Documento processado",
    "message": "Seu documento foi processado com sucesso",
    "severity": "success",
    "data": { ... },
    "created_at": "2025-10-24T16:00:00Z"
  }
}

# Client pode enviar "ping" para manter conexão
{
  "type": "ping"
}

# Server responde "pong"
{
  "type": "pong"
}
```

**Implementação:**
- Infrastructure: 
  - FastAPI WebSocket
  - Redis Pub/Sub para broadcast
  - Manter conexões ativas em memória
- Application: `NotificationBroadcastService`
- Triggers:
  - Após documento processado
  - Quando tokens atingem threshold
  - Quando usuário é convidado

#### **5.6. Sistema de Alertas Automáticos**

```python
# Background job (executado a cada hora)
async def check_token_alerts():
    """Verifica limites de tokens e cria notificações"""
    
    # 80% do limite
    municipalities_warning = await municipality_repo.find_by_usage_percentage(min=80, max=90)
    for muni in municipalities_warning:
        await notification_service.create_notification(
            user_ids=await get_admin_users(muni.id),
            type='token_warning',
            title='Limite de tokens próximo',
            message=f'{muni.name} consumiu {muni.consumption_percentage}% do limite',
            severity='warning',
            data={'municipality_id': str(muni.id), 'usage_percentage': muni.consumption_percentage}
        )
    
    # 100% do limite
    municipalities_exceeded = await municipality_repo.find_by_exhausted_quota()
    for muni in municipalities_exceeded:
        await notification_service.create_notification(
            user_ids=await get_admin_users(muni.id),
            type='token_exceeded',
            title='Limite de tokens excedido',
            message=f'{muni.name} esgotou o limite mensal de tokens',
            severity='error',
            data={'municipality_id': str(muni.id)}
        )

# Após processamento de documento
async def on_document_processed(document_id: UUID, status: str, error: str | None):
    """Notifica usuário quando documento é processado"""
    
    document = await document_repo.find_by_id(document_id)
    
    if status == 'completed':
        await notification_service.create_notification(
            user_ids=[document.uploaded_by_id],
            type='document_completed',
            title='Documento processado',
            message=f'"{document.title}" foi processado com sucesso',
            severity='success',
            data={'document_id': str(document_id)},
            action_url=f'/documents/{document_id}'
        )
    elif status == 'failed':
        await notification_service.create_notification(
            user_ids=[document.uploaded_by_id],
            type='document_failed',
            title='Erro no processamento',
            message=f'"{document.title}" falhou: {error}',
            severity='error',
            data={'document_id': str(document_id), 'error': error}
        )
```

**Implementação:**
- Infrastructure: 
  - Scheduled job (APScheduler ou Celery Beat)
  - Hooks no worker de processamento
- Application: `NotificationService`
- Interface: Background tasks

---

## Impacto Técnico

### **Banco de Dados - Novas Tabelas**

```sql
-- Chat Sessions (persistência)
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) NOT NULL,
    municipality_id UUID REFERENCES municipalities(id) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message_count INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    first_message_preview TEXT,
    last_message_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id, created_at DESC);
CREATE INDEX idx_chat_sessions_municipality ON chat_sessions(municipality_id);

-- Messages (persistência com full-text search)
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user' | 'assistant'
    content TEXT NOT NULL,
    content_tsvector TSVECTOR,  -- Full-text search
    sources JSONB,
    token_usage JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_messages_session ON messages(session_id, created_at);
CREATE INDEX idx_messages_fts ON messages USING GIN(content_tsvector);

-- Trigger para atualizar tsvector
CREATE TRIGGER messages_tsvector_update BEFORE INSERT OR UPDATE
ON messages FOR EACH ROW EXECUTE FUNCTION
tsvector_update_trigger(content_tsvector, 'pg_catalog.portuguese', content);

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) NOT NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,  -- 'info' | 'warning' | 'error' | 'success'
    data JSONB,
    action_url VARCHAR(500),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);
CREATE INDEX idx_notifications_type ON notifications(type);

-- Document Usage Tracking
CREATE TABLE document_references (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) NOT NULL,
    chunk_id UUID REFERENCES document_chunks(id) NOT NULL,
    message_id UUID REFERENCES messages(id) NOT NULL,
    similarity_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_document_refs_document ON document_references(document_id, created_at DESC);
CREATE INDEX idx_document_refs_chunk ON document_references(chunk_id);

-- Analytics Cache (materializada)
CREATE MATERIALIZED VIEW analytics_daily_usage AS
SELECT
    DATE(created_at) as date,
    municipality_id,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_messages,
    SUM(total_tokens) as total_tokens,
    AVG(processing_time) as avg_response_time
FROM messages
JOIN chat_sessions ON messages.session_id = chat_sessions.id
GROUP BY DATE(created_at), municipality_id;

CREATE UNIQUE INDEX ON analytics_daily_usage(date, municipality_id);
-- Refresh diário: REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_daily_usage;
```

### **Redis - Novas Estruturas**

```python
# WebSocket connections tracking
"ws:connections:{user_id}" = SET[connection_id]

# Notification broadcast
"notifications:broadcast" = PubSub channel

# Analytics cache
"analytics:usage:{municipality_id}:{date}" = HASH {
    "messages": 150,
    "tokens": 4500,
    "unique_users": 25
}  # TTL: 1 hora

# Report jobs
"report:job:{job_id}" = HASH {
    "status": "processing",
    "progress": 50,
    "file_path": "s3://..."
}  # TTL: 7 dias
```

### **Performance Considerations**

#### **Índices Críticos**
- `chat_sessions`: (user_id, created_at DESC)
- `messages`: (session_id, created_at), GIN(content_tsvector)
- `notifications`: (user_id, is_read, created_at DESC)
- `document_references`: (document_id, created_at DESC)

#### **Cache Strategy**
- Analytics: Redis cache (TTL 1 hora)
- Materialized views: Refresh diário (3am)
- Session history: Redis + PostgreSQL fallback

#### **Query Optimization**
- Usar EXPLAIN ANALYZE em todas as queries complexas
- Limitar OFFSET máximo (max 10.000)
- Cursor-based pagination para grandes resultados

---

## Cronograma de Implementação

### **Sprint 1 (2 semanas) - Fase 1**
- Semana 1: Endpoints de documentos (listar, detalhes, atualizar, deletar)
- Semana 2: Busca semântica, estatísticas, testes E2E

### **Sprint 2 (2 semanas) - Fase 2**
- Semana 1: Persistência de chat sessions, listagem, histórico
- Semana 2: Renomear, deletar, exportar, busca em conversas

### **Sprint 3 (2 semanas) - Fase 3**
- Semana 1: CRUD prefeituras, ativar/desativar
- Semana 2: Histórico de consumo, relatórios mensais

### **Sprint 4 (2 semanas) - Fase 4**
- Semana 1: Analytics básicos (métricas de uso, top documents/users)
- Semana 2: Performance AI, exportar relatórios

### **Sprint 5 (2 semanas) - Fase 5**
- Semana 1: Notificações (CRUD, preferências)
- Semana 2: WebSocket, alertas automáticos, testes E2E

**Total: 10 semanas (~2.5 meses)**

---

## Testes e Validação

### **Testes Unitários**
- Cada Use Case com cobertura > 80%
- Mocks de repositories e services

### **Testes de Integração**
- Endpoints com banco de dados real
- Validação de permissões por role
- Paginação e filtros

### **Testes E2E**
- Fluxos completos (upload → processo → chat → notificação)
- WebSocket connection handling
- Rate limiting e throttling

### **Performance Testing**
- Load testing com Locust
- Target: < 100ms P95 para listagens
- Target: < 500ms P95 para analytics

---

## Monitoramento

### **Métricas a Monitorar**
- Latência por endpoint (P50, P95, P99)
- Taxa de erro por endpoint
- WebSocket connections ativas
- Redis memory usage
- PostgreSQL query performance (slow queries)
- Tamanho das filas Redis

### **Alertas**
- Latência > 1s (P95)
- Taxa de erro > 5%
- Redis memory > 80%
- PostgreSQL connections > 80%
- WebSocket connections > 10.000

---

## Riscos e Mitigações

### **Risco 1: Performance de Analytics**
**Mitigação:**
- Materialized views
- Cache Redis agressivo
- Background jobs para relatórios pesados

### **Risco 2: Escalabilidade do WebSocket**
**Mitigação:**
- Redis Pub/Sub para múltiplas instâncias
- Load balancer com sticky sessions
- Heartbeat para detectar conexões mortas

### **Risco 3: Consistência Chat (Redis + PostgreSQL)**
**Mitigação:**
- Write-through cache
- Background sync job
- Fallback para PostgreSQL

### **Risco 4: Storage de Relatórios**
**Mitigação:**
- S3 temporário (7 dias)
- Cleanup job diário
- Limite de tamanho (100MB)

---

## Conclusão

Esta ADR define **endpoints essenciais** para um frontend moderno e completo. A implementação será **incremental** (5 fases) para permitir entrega contínua de valor.

**Prioridades:**
1. ✅ **Fase 1** (documentos) - essencial para biblioteca
2. ✅ **Fase 2** (chat sessions) - essencial para UX ChatGPT-like
3. 🔄 **Fase 3** (prefeituras) - importante para admins
4. 📊 **Fase 4** (analytics) - importante para insights
5. 🔔 **Fase 5** (notificações) - nice to have

**Benefícios:**
- Frontend completo e moderno
- UX comparable a ChatGPT
- Dashboards ricos para admins
- Insights de negócio
- Notificações em tempo real

**Próximos Passos:**
1. Revisar ADR com time
2. Estimar esforço detalhado por endpoint
3. Criar issues no GitHub
4. Iniciar Sprint 1 (Fase 1)


