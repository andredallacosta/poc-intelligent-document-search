# 🔍 Intelligent Document Search API v2.0

> **Clean Architecture** implementation for conversational AI with document search using RAG + GPT-4o-mini

A production-ready API that evolved from a simple document search POC to a complete **conversational AI system** with semantic search, session management, and intelligent responses based on your indexed documents.

## ✨ Features

### 💬 **Conversational AI**

- 🤖 **Chat with Documents**: Natural language conversations powered by GPT-4o-mini
- 🧠 **RAG Integration**: Responses based on your indexed documents with source citations
- 💾 **Session Management**: Persistent conversation context across messages
- ⚡ **Real-time Responses**: ~2-3 second response times
- 📚 **Automatic Citations**: Sources and similarity scores included

### 🏗️ **Clean Architecture**

- 🎯 **Domain-Driven Design**: Business logic isolated from infrastructure
- 🔧 **Dependency Injection**: Testable and flexible components
- 📦 **Layered Architecture**: Domain → Application → Infrastructure → Interface
- 🧪 **Test-Ready**: Unit, Integration, and E2E test structure
- 🚀 **Scalable**: Easy to extend and maintain

### 🔍 **Document Processing**

- 📄 **Multi-format Support**: PDF, DOCX, and web content
- 🧠 **Semantic Search**: Find content by meaning, not just keywords
- 🤖 **Contextual Retrieval**: Enhanced chunking with document context
- ⚡ **Vector Database**: ChromaDB for efficient similarity search
- 🔧 **Smart Chunking**: Intelligent text splitting with overlap

### 🛡️ **Production Ready**

- 🚀 **FastAPI**: Modern async API with automatic documentation
- 📊 **Redis Sessions**: Persistent conversation memory
- 🔒 **Rate Limiting**: Cost control and abuse prevention
- 📈 **Monitoring**: Token usage and performance metrics
- 🌐 **API Versioning**: `/api/v1/` for backward compatibility

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Redis (Docker recommended)
- OpenAI API key

### Installation

1. **Clone and setup**

```bash
git clone https://github.com/andredallacosta/poc-intelligent-document-search.git
cd poc-intelligent-document-search
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows
```

2. **Install dependencies**

```bash
pip install -e .
```

3. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

4. **Start Redis**

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### Usage

#### 🚀 **Start the API**

```bash
python -m interface.main
```

#### 📚 **Document Ingestion** (Optional - for new documents)

```bash
# Place documents in documents/ folder
python -m scripts.ingest_documents
```

#### 💬 **Chat with Documents**

```bash
# Start a conversation
curl -X POST http://localhost:8000/api/v1/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I write an official letter?"}'

# Continue conversation (use session_id from response)
curl -X POST http://localhost:8000/api/v1/chat/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "What about the header format?", "session_id": "your-session-id"}'
```

#### 📖 **Interactive Documentation**

- **API Docs**: <http://localhost:8000/docs>
- **Health Check**: <http://localhost:8000/health>
- **App Info**: <http://localhost:8000/info>

## 📁 Architecture

### Clean Architecture Layers

```
interface/                    # 🚀 Interface Layer (FastAPI)
├── api/v1/endpoints/        # REST endpoints
├── schemas/                 # Pydantic models
├── dependencies/            # Dependency injection
└── main.py                  # Application entry point

application/                  # 🎯 Application Layer (Use Cases)
├── use_cases/              # Business use cases
├── dto/                    # Data transfer objects
└── interfaces/             # Service contracts

domain/                      # 💎 Domain Layer (Business Logic)
├── entities/               # Business entities
├── value_objects/          # Domain value objects
├── services/               # Domain services
├── repositories/           # Repository interfaces
└── exceptions/             # Domain exceptions

infrastructure/              # 🔧 Infrastructure Layer
├── repositories/           # Repository implementations
├── external/               # External service clients
├── processors/             # Document processing
└── config/                 # Configuration management

shared/                      # 🛠️ Shared Utilities
tests/                       # 🧪 Test Organization
storage/                     # 📦 Data Storage
```

### Key Components

- **Entities**: `Document`, `ChatSession`, `Message`
- **Use Cases**: `ChatWithDocumentsUseCase`
- **Services**: `ChatService`, `SearchService`, `DocumentService`
- **Repositories**: `ChromaVectorRepository`, `RedisSessionRepository`
- **External**: `OpenAIClient`, `ChromaClient`, `RedisClient`

## 🛠 How It Works

1. **Document Processing**: Extracts text and creates contextual chunks
2. **Vector Embeddings**: Converts text to numerical representations
3. **Semantic Search**: Finds relevant content by meaning similarity
4. **RAG Pipeline**: Combines search results with conversation context
5. **AI Generation**: GPT-4o-mini generates contextual responses
6. **Session Management**: Maintains conversation history in Redis

## 🔧 Configuration

Key environment variables in `.env`:

```bash
# OpenAI
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Processing
CHUNK_SIZE=500
USE_CONTEXTUAL_RETRIEVAL=true

# Rate Limiting
MAX_MESSAGES_PER_SESSION=100
MAX_DAILY_MESSAGES=50
```

## 📊 Performance & Costs

### Performance Metrics

- **Response Time**: 2-3 seconds end-to-end
- **Throughput**: 50+ requests/minute
- **Memory Usage**: ~200MB base + document storage
- **Storage**: ~1MB per 1000 document chunks

### Cost Efficiency

- **Embeddings**: $0.02 per 1M tokens (text-embedding-3-small)
- **Chat**: ~$0.0003 per request (GPT-4o-mini)
- **Typical Document**: $0.001-0.01 to process
- **Monthly Cost**: ~$15-30 for 100 conversations/day

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/e2e/           # End-to-end tests

# With coverage
pytest --cov=app --cov=domain --cov=application --cov=infrastructure
```

## 🚀 Deployment

### Docker

```bash
docker build -t intelligent-doc-search .
docker run -p 8000:8000 intelligent-doc-search
```

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Configure Redis persistence
- [ ] Set up monitoring (health checks)
- [ ] Configure rate limiting
- [ ] Set up logging aggregation
- [ ] Configure CORS for your domain

## 📋 API Reference

### Chat Endpoints

- `POST /api/v1/chat/ask` - Send message and get AI response
- `GET /api/v1/chat/health` - Chat service health check

### System Endpoints

- `GET /` - API information
- `GET /health` - System health check
- `GET /info` - Detailed system information
- `GET /docs` - Interactive API documentation

## 🎯 Use Cases

- **Legal Document Research**: Query legal documents and precedents
- **Technical Documentation**: Search through technical manuals and guides  
- **Knowledge Management**: Corporate knowledge base with conversational interface
- **Research Assistant**: Academic paper analysis and summarization
- **Customer Support**: Automated responses based on documentation

## 🤝 Contributing

This project follows Clean Architecture principles:

1. **Domain Layer**: Pure business logic, no external dependencies
2. **Application Layer**: Use cases and application services
3. **Infrastructure Layer**: External integrations and data persistence
4. **Interface Layer**: API endpoints and user interfaces

## 📄 License

MIT License - feel free to use this for your own projects.

---

<p align="center">
  <strong>Built with ❤️ using Clean Architecture principles</strong><br>
  <em>From simple POC to production-ready conversational AI</em>
</p>
