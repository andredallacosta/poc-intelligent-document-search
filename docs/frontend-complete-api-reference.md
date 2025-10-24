# 📱 Frontend Complete API Reference - Intelligent Document Search

> **Documentação completa para desenvolvimento do frontend React - Versão com TODOS os endpoints**
> 
> Versão: 2.0.0 | Última atualização: 24/10/2025
> 
> ⚠️ **Nota**: Este documento inclui endpoints planejados da ADR-006. Alguns ainda estão em desenvolvimento.

## 🎯 Visão Geral

Sistema completo de busca inteligente em documentos com IA conversacional, multi-tenancy (prefeituras), controle de tokens, notificações em tempo real e analytics avançados.

### Base URL

```
Development: http://localhost:8000
Production: https://api.example.com
```

### Prefixo da API

```
/api/v1
```

---

## 🔐 Autenticação

### Setup do Cliente HTTP

```typescript
// src/services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### Roles e Permissões

```typescript
type UserRole = 'user' | 'admin' | 'superuser';

interface Permissions {
  chat: boolean;
  uploadDocuments: boolean;
  manageDocuments: boolean;
  viewOwnData: boolean;
  manageMunicipality: boolean;
  manageUsers: boolean;
  viewTokens: boolean;
  viewAllStats: boolean;
  manageNotifications: boolean;
}

const rolePermissions: Record<UserRole, Permissions> = {
  user: {
    chat: true,
    uploadDocuments: false,
    manageDocuments: false,
    viewOwnData: true,
    manageMunicipality: false,
    manageUsers: false,
    viewTokens: false,
    viewAllStats: false,
    manageNotifications: false,
  },
  admin: {
    chat: true,
    uploadDocuments: true,
    manageDocuments: true,
    viewOwnData: true,
    manageMunicipality: true,
    manageUsers: true,
    viewTokens: true,
    viewAllStats: false,
    manageNotifications: false,
  },
  superuser: {
    chat: true,
    uploadDocuments: true,
    manageDocuments: true,
    viewOwnData: true,
    manageMunicipality: true,
    manageUsers: true,
    viewTokens: true,
    viewAllStats: true,
    manageNotifications: true,
  }
};
```

---

## 🔑 1. AUTENTICAÇÃO (`/api/v1/auth`)

### 1.1. Login com Email/Senha

```typescript
// POST /api/v1/auth/login
interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>('/api/v1/auth/login', {
    email,
    password,
  });
  
  localStorage.setItem('access_token', response.data.access_token);
  localStorage.setItem('user', JSON.stringify(response.data.user));
  
  return response.data;
}

// Hook de autenticação
function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    
    api.get<User>('/api/v1/auth/me')
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
      })
      .finally(() => setLoading(false));
  }, []);
  
  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
    window.location.href = '/login';
  };
  
  return { user, loading, logout, isAuthenticated: !!user };
}
```

### 1.2. Login com Google OAuth2

```typescript
// GET /api/v1/auth/google
async function getGoogleAuthUrl(): Promise<string> {
  const response = await api.get<{ auth_url: string }>('/api/v1/auth/google');
  return response.data.auth_url;
}

// POST /api/v1/auth/google/token
async function loginWithGoogleToken(googleToken: string): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>('/api/v1/auth/google/token', {
    google_token: googleToken,
  });
  
  localStorage.setItem('access_token', response.data.access_token);
  localStorage.setItem('user', JSON.stringify(response.data.user));
  
  return response.data;
}
```

### 1.3. Ativação de Conta

```typescript
// GET /api/v1/auth/check-invitation/{token}
interface InvitationCheck {
  valid: boolean;
  expired: boolean;
  user: {
    email: string;
    full_name: string;
  };
  invited_by: {
    full_name: string;
  };
  expires_at: string;
  message: string;
}

// POST /api/v1/auth/activate
interface ActivateAccountRequest {
  invitation_token: string;
  auth_provider: 'email_password' | 'google_oauth2';
  password?: string;
  google_token?: string;
}
```

---

## 💬 2. CHAT COM DOCUMENTOS (`/api/v1/chat`)

### 2.1. Enviar Mensagem

```typescript
// POST /api/v1/chat/ask
interface ChatRequest {
  message: string;
  session_id?: string;
  metadata?: Record<string, any>;
}

interface ChatResponse {
  response: string;
  session_id: string;
  sources: DocumentSource[];
  metadata: Record<string, any>;
  processing_time: number;
  token_usage?: TokenUsage;
}

function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  
  const sendMessage = async (message: string) => {
    setLoading(true);
    setMessages((prev) => [...prev, { role: 'user', content: message }]);
    
    try {
      const response = await api.post<ChatResponse>('/api/v1/chat/ask', {
        message,
        session_id: sessionId,
      });
      
      if (!sessionId) setSessionId(response.data.session_id);
      
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.data.response,
          sources: response.data.sources,
        },
      ]);
      
      return response.data;
    } finally {
      setLoading(false);
    }
  };
  
  return { messages, loading, sendMessage, sessionId };
}
```

### 2.2. Listar Sessões (NOVO)

```typescript
// GET /api/v1/chat/sessions
interface ChatSession {
  id: string;
  title: string;
  message_count: number;
  first_message_preview: string;
  last_message_at: string;
  created_at: string;
  token_usage_total: number;
}

interface ChatSessionsResponse {
  sessions: ChatSession[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

async function listChatSessions(
  limit = 20,
  offset = 0
): Promise<ChatSessionsResponse> {
  const response = await api.get<ChatSessionsResponse>(
    `/api/v1/chat/sessions?limit=${limit}&offset=${offset}`
  );
  return response.data;
}

// Hook para listar sessões
function useChatSessions() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);
  
  const loadSessions = async (offset = 0) => {
    const response = await listChatSessions(20, offset);
    setSessions(offset === 0 ? response.sessions : [...sessions, ...response.sessions]);
    setHasMore(response.has_more);
    setLoading(false);
  };
  
  useEffect(() => {
    loadSessions();
  }, []);
  
  return { sessions, loading, hasMore, loadMore: () => loadSessions(sessions.length) };
}
```

### 2.3. Obter Histórico de Sessão (NOVO)

```typescript
// GET /api/v1/chat/sessions/{session_id}
interface SessionHistory {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
  message_count: number;
  total_token_usage: number;
  has_more: boolean;
}

async function getChatHistory(sessionId: string): Promise<SessionHistory> {
  const response = await api.get<SessionHistory>(`/api/v1/chat/sessions/${sessionId}`);
  return response.data;
}
```

### 2.4. Renomear Sessão (NOVO)

```typescript
// PATCH /api/v1/chat/sessions/{session_id}
async function renameSession(sessionId: string, title: string): Promise<void> {
  await api.patch(`/api/v1/chat/sessions/${sessionId}`, { title });
}
```

### 2.5. Deletar Sessão (NOVO)

```typescript
// DELETE /api/v1/chat/sessions/{session_id}
async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/api/v1/chat/sessions/${sessionId}`);
}
```

### 2.6. Exportar Conversa (NOVO)

```typescript
// GET /api/v1/chat/sessions/{session_id}/export?format=json|txt|pdf
async function exportSession(
  sessionId: string,
  format: 'json' | 'txt' | 'pdf'
): Promise<Blob> {
  const response = await api.get(
    `/api/v1/chat/sessions/${sessionId}/export?format=${format}`,
    { responseType: 'blob' }
  );
  return response.data;
}

// Componente de export
function ExportButton({ sessionId }: { sessionId: string }) {
  const [exporting, setExporting] = useState(false);
  
  const handleExport = async (format: 'json' | 'txt' | 'pdf') => {
    setExporting(true);
    try {
      const blob = await exportSession(sessionId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `conversa-${sessionId}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };
  
  return (
    <div>
      <button onClick={() => handleExport('json')} disabled={exporting}>
        Exportar JSON
      </button>
      <button onClick={() => handleExport('txt')} disabled={exporting}>
        Exportar TXT
      </button>
      <button onClick={() => handleExport('pdf')} disabled={exporting}>
        Exportar PDF
      </button>
    </div>
  );
}
```

### 2.7. Buscar em Conversas (NOVO)

```typescript
// GET /api/v1/chat/sessions/search?query=termo
interface SearchResult {
  session_id: string;
  session_title: string;
  message_id: string;
  message_role: 'user' | 'assistant';
  message_content: string;
  message_created_at: string;
  match_highlight: string;
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
  query_time: number;
}

async function searchConversations(query: string): Promise<SearchResponse> {
  const response = await api.get<SearchResponse>(
    `/api/v1/chat/sessions/search?query=${encodeURIComponent(query)}`
  );
  return response.data;
}
```

---

## 📄 3. GERENCIAMENTO DE DOCUMENTOS (`/api/v1/documents`)

### 3.1. Upload de Documento (3 Passos)

```typescript
function useDocumentUpload() {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const uploadDocument = async (
    file: File,
    metadata: { title?: string; description?: string; tags?: string[] }
  ) => {
    setUploading(true);
    setProgress(0);
    
    try {
      // Passo 1: Solicitar URL presigned
      const presignedResponse = await api.post('/api/v1/documents/upload/presigned', {
        filename: file.name,
        file_size: file.size,
        content_type: file.type,
        ...metadata,
      });
      
      setProgress(10);
      
      // Passo 2: Upload para S3
      await axios.put(presignedResponse.data.upload_url, file, {
        headers: { 'Content-Type': file.type },
        onUploadProgress: (e) => {
          const percent = Math.round(10 + (e.loaded * 80) / (e.total || file.size));
          setProgress(percent);
        },
      });
      
      setProgress(90);
      
      // Passo 3: Solicitar processamento
      const processResponse = await api.post(
        `/api/v1/documents/${presignedResponse.data.document_id}/process`,
        { upload_id: presignedResponse.data.upload_id }
      );
      
      setProgress(100);
      
      return {
        document_id: presignedResponse.data.document_id,
        job_id: processResponse.data.job_id,
      };
    } finally {
      setUploading(false);
    }
  };
  
  return { uploadDocument, uploading, progress };
}
```

### 3.2. Listar Documentos (NOVO)

```typescript
// GET /api/v1/documents
interface Document {
  id: string;
  title: string;
  description: string | null;
  source: string;
  content_type: string;
  file_size: number;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  tags: string[];
  chunks_count: number;
  embeddings_count: number;
  uploaded_by: {
    id: string;
    full_name: string;
  };
  municipality_id: string;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
}

interface DocumentListResponse {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

async function listDocuments(params: {
  search?: string;
  tags?: string[];
  status?: string;
  limit?: number;
  offset?: number;
  sort_by?: 'created_at' | 'title' | 'file_size';
  sort_order?: 'asc' | 'desc';
}): Promise<DocumentListResponse> {
  const queryParams = new URLSearchParams();
  if (params.search) queryParams.append('search', params.search);
  if (params.tags) params.tags.forEach(tag => queryParams.append('tags', tag));
  if (params.status) queryParams.append('status', params.status);
  if (params.limit) queryParams.append('limit', params.limit.toString());
  if (params.offset) queryParams.append('offset', params.offset.toString());
  if (params.sort_by) queryParams.append('sort_by', params.sort_by);
  if (params.sort_order) queryParams.append('sort_order', params.sort_order);
  
  const response = await api.get<DocumentListResponse>(
    `/api/v1/documents?${queryParams.toString()}`
  );
  return response.data;
}

// Hook para listar documentos
function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    search: '',
    status: 'completed',
    tags: [] as string[],
  });
  
  const loadDocuments = async () => {
    setLoading(true);
    try {
      const response = await listDocuments(filters);
      setDocuments(response.documents);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    loadDocuments();
  }, [filters]);
  
  return { documents, loading, filters, setFilters, refresh: loadDocuments };
}
```

### 3.3. Obter Documento Específico (NOVO)

```typescript
// GET /api/v1/documents/{document_id}
interface DocumentDetails extends Document {
  chunks: Array<{
    id: string;
    chunk_index: number;
    content: string;
    metadata: Record<string, any>;
  }>;
  municipality: {
    id: string;
    name: string;
  };
  processing_info: {
    job_id: string;
    processing_time: number;
    completed_at: string;
  };
  usage_stats: {
    times_referenced: number;
    last_referenced: string | null;
  };
}

async function getDocumentDetails(documentId: string): Promise<DocumentDetails> {
  const response = await api.get<DocumentDetails>(`/api/v1/documents/${documentId}`);
  return response.data;
}
```

### 3.4. Atualizar Documento (NOVO)

```typescript
// PATCH /api/v1/documents/{document_id}
async function updateDocument(
  documentId: string,
  updates: { title?: string; description?: string; tags?: string[] }
): Promise<Document> {
  const response = await api.patch<Document>(`/api/v1/documents/${documentId}`, updates);
  return response.data;
}
```

### 3.5. Deletar Documento (NOVO)

```typescript
// DELETE /api/v1/documents/{document_id}
async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/api/v1/documents/${documentId}`);
}

// Componente com confirmação
function DeleteDocumentButton({ documentId, onDelete }: { 
  documentId: string; 
  onDelete: () => void;
}) {
  const [deleting, setDeleting] = useState(false);
  
  const handleDelete = async () => {
    if (!confirm('Tem certeza que deseja deletar este documento?')) return;
    
    setDeleting(true);
    try {
      await deleteDocument(documentId);
      alert('Documento deletado com sucesso');
      onDelete();
    } catch (err) {
      alert('Erro ao deletar documento');
    } finally {
      setDeleting(false);
    }
  };
  
  return (
    <button onClick={handleDelete} disabled={deleting}>
      {deleting ? 'Deletando...' : 'Deletar'}
    </button>
  );
}
```

### 3.6. Busca Semântica Manual (NOVO)

```typescript
// POST /api/v1/documents/search
interface SearchRequest {
  query: string;
  limit?: number;
  min_similarity?: number;
  filters?: {
    document_ids?: string[];
    tags?: string[];
    municipality_id?: string;
  };
}

interface SearchResult {
  document_id: string;
  chunk_id: string;
  document_title: string;
  source: string;
  page: number | null;
  similarity_score: number;
  content: string;
  metadata: Record<string, any>;
}

interface SearchResponse {
  results: SearchResult[];
  query: string;
  total_results: number;
  showing: number;
  query_time: number;
  total_chunks_searched: number;
}

async function searchDocuments(request: SearchRequest): Promise<SearchResponse> {
  const response = await api.post<SearchResponse>('/api/v1/documents/search', request);
  return response.data;
}

// Componente de busca
function DocumentSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    try {
      const response = await searchDocuments({
        query,
        limit: 10,
        min_similarity: 0.7,
      });
      setResults(response.results);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <form onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar nos documentos..."
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </form>
      
      <div className="results">
        {results.map((result) => (
          <div key={result.chunk_id} className="result">
            <h3>{result.document_title}</h3>
            <p>{result.content}</p>
            <span>Relevância: {(result.similarity_score * 100).toFixed(0)}%</span>
            {result.page && <span>Página: {result.page}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 3.7. Estatísticas de Documentos (NOVO)

```typescript
// GET /api/v1/documents/stats
interface DocumentStats {
  total_documents: number;
  by_status: Record<string, number>;
  total_chunks: number;
  total_embeddings: number;
  storage_used_mb: number;
  by_type: Record<string, number>;
  by_content_type: Record<string, number>;
  processing_stats: {
    average_processing_time_seconds: number;
    success_rate: number;
    total_processed_today: number;
    total_processed_this_month: number;
  };
  top_documents: Array<{
    document_id: string;
    title: string;
    times_referenced: number;
    last_referenced: string;
  }>;
  recent_uploads: Array<{
    document_id: string;
    title: string;
    uploaded_at: string;
    uploaded_by: string;
  }>;
}

async function getDocumentStats(): Promise<DocumentStats> {
  const response = await api.get<DocumentStats>('/api/v1/documents/stats');
  return response.data;
}
```

### 3.8. Verificar Status do Documento

```typescript
// GET /api/v1/documents/{document_id}/status
interface DocumentStatus {
  document_id: string;
  job_id: string;
  status: 'uploaded' | 'extracting' | 'checking_duplicates' | 'chunking' | 'embedding' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  chunks_processed: number;
  total_chunks: number;
  processing_time: number;
  s3_file_deleted: boolean;
  duplicate_of: string | null;
  error: string | null;
  estimated_time_remaining: string | null;
}

function useDocumentStatus(documentId: string | null) {
  const [status, setStatus] = useState<DocumentStatus | null>(null);
  const [polling, setPolling] = useState(false);
  
  useEffect(() => {
    if (!documentId) return;
    
    setPolling(true);
    let interval: NodeJS.Timeout;
    
    const checkStatus = async () => {
      try {
        const response = await api.get<DocumentStatus>(
          `/api/v1/documents/${documentId}/status`
        );
        setStatus(response.data);
        
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          setPolling(false);
          if (interval) clearInterval(interval);
        }
      } catch (err) {
        setPolling(false);
        if (interval) clearInterval(interval);
      }
    };
    
    checkStatus();
    interval = setInterval(checkStatus, 2000);
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [documentId]);
  
  return { status, polling };
}
```

---

## 👥 4. GERENCIAMENTO DE USUÁRIOS (`/api/v1/users`)

### 4.1. Criar Usuário com Convite

```typescript
// POST /api/v1/users/create
interface CreateUserRequest {
  email: string;
  full_name: string;
  role: 'user' | 'admin' | 'superuser';
  primary_municipality_id: string;
  municipality_ids?: string[];
  auth_provider?: 'email_password' | 'google_oauth2';
}

async function createUser(request: CreateUserRequest): Promise<UserListDTO> {
  const response = await api.post<UserListDTO>('/api/v1/users/create', request);
  return response.data;
}
```

### 4.2. Listar Usuários

```typescript
// GET /api/v1/users/list?municipality_id={id}
async function listUsers(municipalityId: string, limit = 50): Promise<UserListDTO[]> {
  const response = await api.get<UserListDTO[]>(
    `/api/v1/users/list?municipality_id=${municipalityId}&limit=${limit}`
  );
  return response.data;
}
```

### 4.3. Desativar Usuário

```typescript
// POST /api/v1/users/{user_id}/deactivate
async function deactivateUser(userId: string): Promise<void> {
  await api.post(`/api/v1/users/${userId}/deactivate`);
}
```

### 4.4. Reenviar Convite

```typescript
// POST /api/v1/users/{user_id}/resend-invitation
async function resendInvitation(userId: string): Promise<void> {
  await api.post(`/api/v1/users/${userId}/resend-invitation`);
}
```

---

## 🎯 5. CONTROLE DE TOKENS (`/api/v1/tokens`)

### 5.1. Obter Status de Tokens

```typescript
// GET /api/v1/tokens/{municipality_id}/status
interface TokenStatus {
  municipality_id: string;
  municipality_active: boolean;
  status: 'available' | 'warning' | 'exceeded' | 'inactive';
  base_limit: number;
  extra_credits: number;
  total_limit: number;
  consumed: number;
  remaining: number;
  usage_percentage: number;
  period_start: string;
  period_end: string;
  days_remaining: number;
  next_due_date: string;
  message?: string;
}

function useTokenStatus(municipalityId: string | null) {
  const [status, setStatus] = useState<TokenStatus | null>(null);
  const [loading, setLoading] = useState(true);
  
  const loadStatus = async () => {
    if (!municipalityId) return;
    
    try {
      const response = await api.get<TokenStatus>(
        `/api/v1/tokens/${municipalityId}/status`
      );
      setStatus(response.data);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    loadStatus();
  }, [municipalityId]);
  
  return { status, loading, refresh: loadStatus };
}
```

### 5.2. Adicionar Créditos

```typescript
// POST /api/v1/tokens/{municipality_id}/credits
async function addCredits(
  municipalityId: string,
  tokens: number,
  reason: string
): Promise<TokenStatus> {
  const response = await api.post<TokenStatus>(
    `/api/v1/tokens/${municipalityId}/credits`,
    { tokens, reason }
  );
  return response.data;
}
```

### 5.3. Atualizar Limite Mensal

```typescript
// PUT /api/v1/tokens/{municipality_id}/limit
async function updateMonthlyLimit(
  municipalityId: string,
  newLimit: number,
  changedBy: string
): Promise<TokenStatus> {
  const response = await api.put<TokenStatus>(
    `/api/v1/tokens/${municipalityId}/limit`,
    { new_limit: newLimit, changed_by: changedBy }
  );
  return response.data;
}
```

---

## 🏛️ 6. ADMINISTRAÇÃO (`/api/v1/admin`)

### 6.1. Criar Prefeitura

```typescript
// POST /api/v1/admin/municipalities
async function createMunicipality(
  name: string,
  tokenQuota: number
): Promise<Municipality> {
  const response = await api.post<Municipality>('/api/v1/admin/municipalities', {
    name,
    token_quota: tokenQuota,
  });
  return response.data;
}
```

### 6.2. Listar Prefeituras

```typescript
// GET /api/v1/admin/municipalities
async function listMunicipalities(): Promise<Municipality[]> {
  const response = await api.get<Municipality[]>('/api/v1/admin/municipalities');
  return response.data;
}
```

### 6.3. Atualizar Prefeitura (NOVO)

```typescript
// PATCH /api/v1/admin/municipalities/{municipality_id}
async function updateMunicipality(
  municipalityId: string,
  updates: {
    name?: string;
    token_quota?: number;
    monthly_token_limit?: number;
    active?: boolean;
  }
): Promise<Municipality> {
  const response = await api.patch<Municipality>(
    `/api/v1/admin/municipalities/${municipalityId}`,
    updates
  );
  return response.data;
}
```

### 6.4. Ativar/Desativar Prefeitura (NOVO)

```typescript
// PATCH /api/v1/admin/municipalities/{municipality_id}/status
async function toggleMunicipalityStatus(
  municipalityId: string,
  active: boolean,
  reason?: string
): Promise<Municipality> {
  const response = await api.patch<Municipality>(
    `/api/v1/admin/municipalities/${municipalityId}/status`,
    { active, reason }
  );
  return response.data;
}
```

### 6.5. Histórico de Consumo (NOVO)

```typescript
// GET /api/v1/admin/municipalities/{municipality_id}/consumption
interface ConsumptionHistory {
  municipality_id: string;
  municipality_name: string;
  period: {
    start: string;
    end: string;
  };
  consumption_by_period: Array<{
    date: string;
    tokens_consumed: number;
    messages_sent: number;
    documents_referenced: number;
  }>;
  consumption_by_user: Array<{
    user_id: string;
    user_name: string;
    tokens_consumed: number;
    messages_sent: number;
  }>;
  top_documents: Array<{
    document_id: string;
    document_title: string;
    times_referenced: number;
  }>;
  totals: {
    total_tokens: number;
    total_messages: number;
    average_tokens_per_message: number;
  };
}

async function getMunicipalityConsumption(
  municipalityId: string,
  startDate?: string,
  endDate?: string
): Promise<ConsumptionHistory> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await api.get<ConsumptionHistory>(
    `/api/v1/admin/municipalities/${municipalityId}/consumption?${params.toString()}`
  );
  return response.data;
}
```

### 6.6. Relatório Mensal (NOVO)

```typescript
// GET /api/v1/admin/municipalities/{municipality_id}/reports/monthly
interface MonthlyReport {
  municipality_id: string;
  municipality_name: string;
  report_period: string;
  generated_at: string;
  summary: {
    total_tokens_consumed: number;
    total_messages: number;
    total_documents: number;
    active_users: number;
    new_users: number;
  };
  usage_by_day: any[];
  usage_by_user: any[];
  top_documents: any[];
  billing: {
    base_limit: number;
    extra_credits_purchased: number;
    total_available: number;
    consumed: number;
    remaining: number;
    overage: number;
    estimated_cost_usd: number;
  };
}

async function getMonthlyReport(
  municipalityId: string,
  year: number,
  month: number,
  format: 'json' | 'pdf' = 'json'
): Promise<MonthlyReport | Blob> {
  const response = await api.get(
    `/api/v1/admin/municipalities/${municipalityId}/reports/monthly?year=${year}&month=${month}&format=${format}`,
    { responseType: format === 'pdf' ? 'blob' : 'json' }
  );
  return response.data;
}
```

### 6.7. Estatísticas Administrativas

```typescript
// GET /api/v1/admin/stats
interface AdminStats {
  municipalities: {
    total: number;
    active: number;
    critical_quota: number;
    exhausted_quota: number;
  };
  users: {
    total: number;
    active: number;
    anonymous: number;
    linked: number;
  };
}

async function getAdminStats(): Promise<AdminStats> {
  const response = await api.get<AdminStats>('/api/v1/admin/stats');
  return response.data;
}
```

---

## 📊 7. ANALYTICS E MÉTRICAS (NOVO - `/api/v1/analytics`)

### 7.1. Métricas de Uso

```typescript
// GET /api/v1/analytics/usage
interface UsageMetrics {
  period: {
    start: string;
    end: string;
    group_by: 'hour' | 'day' | 'week' | 'month';
  };
  metrics: Array<{
    date: string;
    messages_sent: number;
    tokens_consumed: number;
    documents_uploaded: number;
    unique_users: number;
    average_response_time_seconds: number;
    success_rate: number;
  }>;
  totals: {
    total_messages: number;
    total_tokens: number;
    total_documents: number;
    total_unique_users: number;
  };
}

async function getUsageMetrics(
  startDate: string,
  endDate: string,
  groupBy: 'hour' | 'day' | 'week' | 'month' = 'day',
  municipalityId?: string
): Promise<UsageMetrics> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
    group_by: groupBy,
  });
  if (municipalityId) params.append('municipality_id', municipalityId);
  
  const response = await api.get<UsageMetrics>(
    `/api/v1/analytics/usage?${params.toString()}`
  );
  return response.data;
}

// Hook para métricas
function useUsageMetrics(days = 30) {
  const [metrics, setMetrics] = useState<UsageMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const endDate = new Date().toISOString().split('T')[0];
    const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000)
      .toISOString()
      .split('T')[0];
    
    getUsageMetrics(startDate, endDate, 'day')
      .then(setMetrics)
      .finally(() => setLoading(false));
  }, [days]);
  
  return { metrics, loading };
}
```

### 7.2. Documentos Mais Consultados (NOVO)

```typescript
// GET /api/v1/analytics/top-documents
interface TopDocument {
  rank: number;
  document_id: string;
  title: string;
  source: string;
  times_referenced: number;
  unique_users: number;
  average_similarity_score: number;
  last_referenced: string;
}

interface TopDocumentsResponse {
  period: {
    start: string;
    end: string;
  };
  top_documents: TopDocument[];
}

async function getTopDocuments(
  startDate: string,
  endDate: string,
  limit = 10
): Promise<TopDocumentsResponse> {
  const response = await api.get<TopDocumentsResponse>(
    `/api/v1/analytics/top-documents?start_date=${startDate}&end_date=${endDate}&limit=${limit}`
  );
  return response.data;
}
```

### 7.3. Usuários Mais Ativos (NOVO)

```typescript
// GET /api/v1/analytics/top-users
interface TopUser {
  rank: number;
  user_id: string;
  full_name: string;
  email: string;
  messages_sent: number;
  tokens_consumed: number;
  sessions_created: number;
  last_activity: string;
}

interface TopUsersResponse {
  period: {
    start: string;
    end: string;
  };
  top_users: TopUser[];
}

async function getTopUsers(
  startDate: string,
  endDate: string,
  limit = 10
): Promise<TopUsersResponse> {
  const response = await api.get<TopUsersResponse>(
    `/api/v1/analytics/top-users?start_date=${startDate}&end_date=${endDate}&limit=${limit}`
  );
  return response.data;
}
```

### 7.4. Performance da IA (NOVO)

```typescript
// GET /api/v1/analytics/ai-performance
interface AIPerformance {
  period: {
    start: string;
    end: string;
  };
  performance: {
    average_response_time_seconds: number;
    median_response_time_seconds: number;
    p95_response_time_seconds: number;
    p99_response_time_seconds: number;
    success_rate: number;
    error_rate: number;
    timeout_rate: number;
  };
  token_usage: {
    average_tokens_per_message: number;
    average_prompt_tokens: number;
    average_completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
  };
  quality_metrics: {
    average_similarity_score: number;
    sources_used_average: number;
    messages_with_sources: number;
  };
}

async function getAIPerformance(
  startDate: string,
  endDate: string
): Promise<AIPerformance> {
  const response = await api.get<AIPerformance>(
    `/api/v1/analytics/ai-performance?start_date=${startDate}&end_date=${endDate}`
  );
  return response.data;
}
```

### 7.5. Gerar Relatórios (NOVO)

```typescript
// POST /api/v1/analytics/reports/generate
interface GenerateReportRequest {
  report_type: 'usage_summary' | 'detailed_usage' | 'cost_analysis' | 'user_activity';
  format: 'json' | 'csv' | 'pdf' | 'xlsx';
  filters: {
    start_date: string;
    end_date: string;
    municipality_id?: string;
  };
}

interface ReportJob {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  estimated_time?: string;
  download_url?: string;
  expires_at?: string;
  file_size?: number;
  error?: string;
}

async function generateReport(request: GenerateReportRequest): Promise<ReportJob> {
  const response = await api.post<ReportJob>(
    '/api/v1/analytics/reports/generate',
    request
  );
  return response.data;
}

// GET /api/v1/analytics/reports/{job_id}
async function getReportStatus(jobId: string): Promise<ReportJob> {
  const response = await api.get<ReportJob>(`/api/v1/analytics/reports/${jobId}`);
  return response.data;
}

// Hook para gerar relatório com polling
function useReportGeneration() {
  const [job, setJob] = useState<ReportJob | null>(null);
  const [polling, setPolling] = useState(false);
  
  const generateAndPoll = async (request: GenerateReportRequest) => {
    const initialJob = await generateReport(request);
    setJob(initialJob);
    setPolling(true);
    
    const interval = setInterval(async () => {
      const updatedJob = await getReportStatus(initialJob.job_id);
      setJob(updatedJob);
      
      if (updatedJob.status === 'completed' || updatedJob.status === 'failed') {
        setPolling(false);
        clearInterval(interval);
      }
    }, 2000);
  };
  
  return { job, polling, generateReport: generateAndPoll };
}
```

---

## 🔔 8. NOTIFICAÇÕES (NOVO - `/api/v1/notifications`)

### 8.1. Listar Notificações

```typescript
// GET /api/v1/notifications
interface Notification {
  id: string;
  type: 'token_warning' | 'token_exceeded' | 'document_completed' | 'document_failed' | 'user_invited' | 'user_activated';
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  data: Record<string, any>;
  action_url: string | null;
  is_read: boolean;
  created_at: string;
  expires_at: string | null;
}

interface NotificationsResponse {
  notifications: Notification[];
  unread_count: number;
  total: number;
  has_more: boolean;
}

async function getNotifications(
  unreadOnly = false,
  limit = 20,
  offset = 0
): Promise<NotificationsResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  if (unreadOnly) params.append('unread_only', 'true');
  
  const response = await api.get<NotificationsResponse>(
    `/api/v1/notifications?${params.toString()}`
  );
  return response.data;
}

// Hook para notificações
function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  
  const loadNotifications = async () => {
    const response = await getNotifications(false, 20, 0);
    setNotifications(response.notifications);
    setUnreadCount(response.unread_count);
    setLoading(false);
  };
  
  useEffect(() => {
    loadNotifications();
  }, []);
  
  return { notifications, unreadCount, loading, refresh: loadNotifications };
}
```

### 8.2. Marcar como Lida (NOVO)

```typescript
// PATCH /api/v1/notifications/{notification_id}/read
async function markAsRead(notificationId: string): Promise<void> {
  await api.patch(`/api/v1/notifications/${notificationId}/read`);
}

// POST /api/v1/notifications/mark-all-read
async function markAllAsRead(): Promise<number> {
  const response = await api.post<{ marked_count: number }>(
    '/api/v1/notifications/mark-all-read'
  );
  return response.data.marked_count;
}
```

### 8.3. Deletar Notificação (NOVO)

```typescript
// DELETE /api/v1/notifications/{notification_id}
async function deleteNotification(notificationId: string): Promise<void> {
  await api.delete(`/api/v1/notifications/${notificationId}`);
}
```

### 8.4. Preferências de Notificação (NOVO)

```typescript
// GET /api/v1/notifications/preferences
interface NotificationPreferences {
  email_notifications: boolean;
  push_notifications: boolean;
  notification_types: {
    token_warning: boolean;
    token_exceeded: boolean;
    document_completed: boolean;
    document_failed: boolean;
    user_invited: boolean;
    user_activated: boolean;
  };
}

async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const response = await api.get<NotificationPreferences>(
    '/api/v1/notifications/preferences'
  );
  return response.data;
}

// PATCH /api/v1/notifications/preferences
async function updateNotificationPreferences(
  preferences: Partial<NotificationPreferences>
): Promise<NotificationPreferences> {
  const response = await api.patch<NotificationPreferences>(
    '/api/v1/notifications/preferences',
    preferences
  );
  return response.data;
}
```

### 8.5. WebSocket para Notificações em Tempo Real (NOVO)

```typescript
// WS /api/v1/notifications/ws
class NotificationWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  
  connect(token: string, onNotification: (notification: Notification) => void) {
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
    this.ws = new WebSocket(`${wsUrl}/api/v1/notifications/ws?token=${token}`);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      
      // Heartbeat
      setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'notification') {
        onNotification(message.data);
      } else if (message.type === 'pong') {
        console.log('Heartbeat response received');
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      
      // Tentar reconectar
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        setTimeout(() => {
          console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
          this.connect(token, onNotification);
        }, 5000);
      }
    };
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Hook para WebSocket
function useNotificationWebSocket() {
  const { user } = useAuth();
  const { refresh: refreshNotifications } = useNotifications();
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<NotificationWebSocket | null>(null);
  
  useEffect(() => {
    if (!user) return;
    
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    wsRef.current = new NotificationWebSocket();
    wsRef.current.connect(token, (notification) => {
      console.log('Nova notificação:', notification);
      
      // Mostrar toast/notification
      showToast(notification.title, notification.message, notification.severity);
      
      // Atualizar lista
      refreshNotifications();
    });
    
    setConnected(true);
    
    return () => {
      wsRef.current?.disconnect();
      setConnected(false);
    };
  }, [user]);
  
  return { connected };
}

// Componente de notificação toast
function NotificationToast() {
  useNotificationWebSocket();
  return null;
}
```

---

## 🚦 9. PROTEÇÃO DE ROTAS

```typescript
// src/components/ProtectedRoute.tsx
interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  
  if (loading) return <LoadingSpinner />;
  
  if (!user) return <Navigate to="/login" replace />;
  
  if (allowedRoles && !allowedRoles.includes(user.role as UserRole)) {
    return <Navigate to="/unauthorized" replace />;
  }
  
  return <>{children}</>;
}

// src/App.tsx
function App() {
  return (
    <BrowserRouter>
      <NotificationToast />
      <Routes>
        {/* Públicas */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/activate" element={<ActivateAccountPage />} />
        
        {/* Usuário comum */}
        <Route
          path="/chat"
          element={
            <ProtectedRoute allowedRoles={['user', 'admin', 'superuser']}>
              <ChatPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/chat/history"
          element={
            <ProtectedRoute allowedRoles={['user', 'admin', 'superuser']}>
              <ChatHistoryPage />
            </ProtectedRoute>
          }
        />
        
        {/* Admin */}
        <Route
          path="/admin/*"
          element={
            <ProtectedRoute allowedRoles={['admin', 'superuser']}>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route path="dashboard" element={<AdminDashboard />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="documents/upload" element={<DocumentUploadPage />} />
          <Route path="documents/:id" element={<DocumentDetailsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="tokens" element={<TokensPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>
        
        {/* Superuser */}
        <Route
          path="/superadmin/*"
          element={
            <ProtectedRoute allowedRoles={['superuser']}>
              <SuperAdminLayout />
            </ProtectedRoute>
          }
        >
          <Route path="dashboard" element={<SuperAdminDashboard />} />
          <Route path="municipalities" element={<MunicipalitiesPage />} />
          <Route path="municipalities/:id" element={<MunicipalityDetailsPage />} />
          <Route path="municipalities/:id/consumption" element={<ConsumptionHistoryPage />} />
          <Route path="all-users" element={<AllUsersPage />} />
          <Route path="analytics" element={<GlobalAnalyticsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

---

## 🎨 10. ESTRUTURA DE PASTAS COMPLETA

```
src/
├── components/
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   ├── GoogleLoginButton.tsx
│   │   └── ActivateAccount.tsx
│   ├── chat/
│   │   ├── ChatInterface.tsx
│   │   ├── MessageList.tsx
│   │   ├── MessageInput.tsx
│   │   ├── SourcesList.tsx
│   │   ├── SessionsList.tsx           # NOVO
│   │   ├── SessionItem.tsx            # NOVO
│   │   └── ExportButton.tsx           # NOVO
│   ├── documents/
│   │   ├── DocumentUpload.tsx
│   │   ├── DocumentStatus.tsx
│   │   ├── DocumentsList.tsx          # NOVO
│   │   ├── DocumentCard.tsx           # NOVO
│   │   ├── DocumentDetails.tsx        # NOVO
│   │   ├── DocumentSearch.tsx         # NOVO
│   │   └── DocumentFilters.tsx        # NOVO
│   ├── users/
│   │   ├── CreateUserForm.tsx
│   │   ├── UsersList.tsx
│   │   └── UserCard.tsx
│   ├── tokens/
│   │   ├── TokenDashboard.tsx
│   │   ├── AddCreditsForm.tsx
│   │   └── TokenChart.tsx             # NOVO
│   ├── admin/
│   │   ├── AdminDashboard.tsx
│   │   ├── MunicipalitiesList.tsx
│   │   ├── MunicipalityCard.tsx       # NOVO
│   │   ├── ConsumptionChart.tsx       # NOVO
│   │   └── StatisticsCards.tsx
│   ├── analytics/                     # NOVO
│   │   ├── UsageMetricsChart.tsx
│   │   ├── TopDocumentsTable.tsx
│   │   ├── TopUsersTable.tsx
│   │   ├── AIPerformanceCard.tsx
│   │   └── ReportGenerator.tsx
│   ├── notifications/                 # NOVO
│   │   ├── NotificationsList.tsx
│   │   ├── NotificationItem.tsx
│   │   ├── NotificationBell.tsx
│   │   ├── NotificationToast.tsx
│   │   └── NotificationPreferences.tsx
│   └── common/
│       ├── ProtectedRoute.tsx
│       ├── Navbar.tsx
│       ├── Sidebar.tsx                # NOVO
│       ├── LoadingSpinner.tsx
│       ├── ErrorBoundary.tsx          # NOVO
│       └── ConfirmDialog.tsx          # NOVO
│
├── hooks/
│   ├── useAuth.ts
│   ├── useChat.ts
│   ├── useChatSessions.ts             # NOVO
│   ├── useDocumentUpload.ts
│   ├── useDocumentStatus.ts
│   ├── useDocuments.ts                # NOVO
│   ├── useTokenStatus.ts
│   ├── useUsers.ts
│   ├── useNotifications.ts            # NOVO
│   ├── useNotificationWebSocket.ts    # NOVO
│   ├── useUsageMetrics.ts             # NOVO
│   └── useReportGeneration.ts         # NOVO
│
├── services/
│   ├── api.ts
│   ├── authService.ts
│   ├── chatService.ts
│   ├── documentService.ts
│   ├── userService.ts
│   ├── tokenService.ts
│   ├── adminService.ts
│   ├── analyticsService.ts            # NOVO
│   ├── notificationService.ts         # NOVO
│   └── websocketService.ts            # NOVO
│
├── pages/
│   ├── LoginPage.tsx
│   ├── ActivateAccountPage.tsx
│   ├── ChatPage.tsx
│   ├── ChatHistoryPage.tsx            # NOVO
│   ├── admin/
│   │   ├── AdminDashboardPage.tsx
│   │   ├── DocumentsPage.tsx          # NOVO
│   │   ├── DocumentUploadPage.tsx     # NOVO
│   │   ├── DocumentDetailsPage.tsx    # NOVO
│   │   ├── UsersPage.tsx
│   │   ├── TokensPage.tsx
│   │   ├── AnalyticsPage.tsx          # NOVO
│   │   └── ReportsPage.tsx            # NOVO
│   └── superadmin/
│       ├── SuperAdminDashboard.tsx
│       ├── MunicipalitiesPage.tsx
│       ├── MunicipalityDetailsPage.tsx    # NOVO
│       ├── ConsumptionHistoryPage.tsx     # NOVO
│       ├── AllUsersPage.tsx
│       └── GlobalAnalyticsPage.tsx        # NOVO
│
├── types/
│   ├── auth.ts
│   ├── chat.ts
│   ├── document.ts
│   ├── user.ts
│   ├── token.ts
│   ├── admin.ts
│   ├── analytics.ts                   # NOVO
│   └── notification.ts                # NOVO
│
├── contexts/
│   ├── AuthContext.tsx
│   └── NotificationContext.tsx        # NOVO
│
├── utils/
│   ├── formatters.ts
│   ├── validators.ts
│   ├── constants.ts
│   └── chartHelpers.ts                # NOVO
│
└── App.tsx
```

---

## 🎯 11. TIPOS TYPESCRIPT COMPLETOS

```typescript
// types/auth.ts
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'user' | 'admin' | 'superuser';
  primary_municipality_id: string | null;
  municipality_ids: string[];
  is_active: boolean;
  email_verified: boolean;
  last_login: string | null;
  created_at: string;
}

// types/chat.ts
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: DocumentSource[];
  token_usage?: TokenUsage;
}

export interface ChatSession {
  id: string;
  title: string;
  message_count: number;
  first_message_preview: string;
  last_message_at: string;
  created_at: string;
  token_usage_total: number;
}

// types/document.ts
export interface Document {
  id: string;
  title: string;
  description: string | null;
  source: string;
  content_type: string;
  file_size: number;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  tags: string[];
  chunks_count: number;
  embeddings_count: number;
  uploaded_by: {
    id: string;
    full_name: string;
  };
  municipality_id: string;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
}

// types/analytics.ts
export interface UsageMetrics {
  period: {
    start: string;
    end: string;
    group_by: 'hour' | 'day' | 'week' | 'month';
  };
  metrics: Array<{
    date: string;
    messages_sent: number;
    tokens_consumed: number;
    documents_uploaded: number;
    unique_users: number;
    average_response_time_seconds: number;
    success_rate: number;
  }>;
  totals: {
    total_messages: number;
    total_tokens: number;
    total_documents: number;
    total_unique_users: number;
  };
}

// types/notification.ts
export interface Notification {
  id: string;
  type: 'token_warning' | 'token_exceeded' | 'document_completed' | 'document_failed' | 'user_invited' | 'user_activated';
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error' | 'success';
  data: Record<string, any>;
  action_url: string | null;
  is_read: boolean;
  created_at: string;
  expires_at: string | null;
}
```

---

## 📝 12. CHECKLIST DE IMPLEMENTAÇÃO

### **Fase 1 - MVP (2 semanas)**
- [ ] Setup do projeto React + TypeScript
- [ ] Configuração do Axios com interceptors
- [ ] Sistema de autenticação (login, JWT, guards)
- [ ] Interface de chat básica
- [ ] Upload de documentos com progresso

### **Fase 2 - Histórico e Organização (1 semana)**
- [ ] Listagem de sessões de chat
- [ ] Visualização de histórico
- [ ] Renomear/deletar sessões
- [ ] Exportar conversas

### **Fase 3 - Biblioteca de Documentos (1 semana)**
- [ ] Listagem de documentos
- [ ] Filtros e busca
- [ ] Detalhes do documento
- [ ] Editar/deletar documentos
- [ ] Busca semântica manual

### **Fase 4 - Admin Dashboard (1 semana)**
- [ ] Dashboard de tokens
- [ ] Gerenciamento de usuários
- [ ] Estatísticas básicas
- [ ] Histórico de consumo

### **Fase 5 - Analytics (1 semana)**
- [ ] Métricas de uso com gráficos
- [ ] Top documentos/usuários
- [ ] Performance da IA
- [ ] Geração de relatórios

### **Fase 6 - Notificações (1 semana)**
- [ ] Lista de notificações
- [ ] WebSocket em tempo real
- [ ] Toast notifications
- [ ] Preferências de notificação

### **Fase 7 - Superadmin (1 semana)**
- [ ] Dashboard global
- [ ] Gerenciamento de prefeituras
- [ ] Analytics globais
- [ ] Relatórios consolidados

**Total: ~8 semanas de desenvolvimento frontend**

---

## 🚀 EXEMPLO DE DASHBOARD COMPLETO

```typescript
// AdminDashboard.tsx
function AdminDashboard() {
  const { user } = useAuth();
  const { status: tokenStatus } = useTokenStatus(user?.primary_municipality_id);
  const { metrics } = useUsageMetrics(30);
  const { stats } = useDocumentStats();
  const { notifications, unreadCount } = useNotifications();
  
  return (
    <div className="dashboard">
      <header>
        <h1>Dashboard Administrativo</h1>
        <NotificationBell count={unreadCount} />
      </header>
      
      <div className="metrics-grid">
        {/* Card de Tokens */}
        <TokenStatusCard status={tokenStatus} />
        
        {/* Métricas de Uso */}
        <UsageMetricsChart metrics={metrics} />
        
        {/* Estatísticas de Documentos */}
        <DocumentStatsCard stats={stats} />
        
        {/* Top Documentos */}
        <TopDocumentsTable />
        
        {/* Usuários Ativos */}
        <ActiveUsersTable />
        
        {/* Notificações Recentes */}
        <RecentNotifications notifications={notifications} />
      </div>
    </div>
  );
}
```

---

Este documento está completo e pronto para ser usado com qualquer ferramenta de geração de código (Lovable, v0, Bolt, etc). Todos os endpoints estão documentados como se já existissem! 🚀

