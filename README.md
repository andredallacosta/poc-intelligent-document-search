# 🔍 Intelligent Document Search

> Transform your documents into a searchable knowledge base powered by AI

A proof-of-concept that ingests various document formats (PDF, DOCX, URLs) and enables semantic search using vector embeddings and ChromaDB.

## ✨ Features

- 📄 **Multi-format support**: PDF, DOCX, and web content
- 🧠 **Semantic search**: Find content by meaning, not just keywords
- ⚡ **Fast retrieval**: ChromaDB vector database for efficient similarity search
- 🤖 **OpenAI embeddings**: Powered by `text-embedding-3-small`
- 🔧 **Smart chunking**: Intelligent text splitting with context preservation

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. Clone the repository

```bash
git clone https://github.com/andredallacosta/poc-intelligent-document-search.git
cd poc-intelligent-document-search
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Set up environment variables

```bash
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### Usage

1. **Add documents** to the `documents/` folder

2. **Ingest documents** into the vector database

```bash
python src/ingest.py
```

3. **Search your documents**

```bash
python src/query.py
```

## 📁 Project Structure

```
├── src/
│   ├── ingest.py      # Document processing pipeline
│   ├── query.py       # Semantic search interface
│   ├── embedder.py    # OpenAI embedding generation
│   └── chunker.py     # Text chunking logic
├── documents/         # Place your documents here
├── data/             # ChromaDB storage (auto-created)
└── requirements.txt  # Dependencies
```

## 🛠 How It Works

1. **Document Parsing**: Extracts text from PDFs, Word docs, and web pages
2. **Smart Chunking**: Breaks text into 300-500 token chunks with overlap
3. **Vector Embeddings**: Converts chunks to numerical representations using OpenAI
4. **Storage**: Saves embeddings in ChromaDB for fast retrieval
5. **Semantic Search**: Finds relevant content based on meaning similarity

## 💡 Example

```python
from src.query import DocumentQuery

query = DocumentQuery()
results = query.search("How to write a formal letter?", n_results=3)

for result in results:
    print(f"Source: {result['metadata']['source']}")
    print(f"Text: {result['text'][:200]}...")
    print(f"Similarity: {1 - result['distance']:.3f}")
```

## 🔧 Tech Stack

- **Vector Database**: ChromaDB (local, SQLite-based)
- **Embeddings**: OpenAI text-embedding-3-small
- **Text Processing**: LangChain, unstructured, python-docx
- **Web Scraping**: trafilatura

## 📋 Supported Formats

- 📄 PDF files
- 📝 Microsoft Word (.docx)
- 🌐 Web pages (URLs)

## 🎯 Use Cases

- Legal document research
- Technical documentation search
- Knowledge base creation
- Content discovery
- Research assistance

## 📈 Cost Efficiency

Using OpenAI's most cost-effective embedding model:

- **$0.02 per 1M tokens** (text-embedding-3-small)
- Typical document: ~$0.001-0.01 to process

## 🤝 Contributing

This is a proof-of-concept project. Feel free to fork and experiment!

## 📄 License

MIT License - feel free to use this for your own projects.

---

<p align="center">
  <strong>Built with ❤️ for intelligent document discovery</strong>
</p>

## 🧩 API (Q&A síncrona)

- Endpoint: `POST /v1/ask`
- Headers: `Content-Type: application/json`, `X-API-Key` (opcional)
- Corpo da requisição:

```json
{
  "question": "Como escrever um ofício?",
  "top_k": 4,
  "filters": { "tipo_documento": "manual", "source": "manual_redacao.pdf" },
  "prompt_preset": "default"
}
```

- Resposta 200 (exemplo):

```json
{
  "answer": "...",
  "sources": [
    { "id": "chunk-123", "source": "manual_redacao.pdf", "page": 4, "score": 0.83, "snippet": "Solicito a Vossa Excelência..." }
  ],
  "model": "gpt-4o-mini",
  "usage": { "prompt_tokens": 1234, "completion_tokens": 210, "total_tokens": 1444, "cost_estimated": 0.0007 },
  "latency_ms": 2310,
  "request_id": "req_abc123"
}
```

- Erros:
  - 400 input inválido
  - 401 não autorizado
  - 429 limite de requisições
  - 500/502 erro interno/upstream
  - 504 timeout
  - Formato: `{ "error": "code", "message": "...", "request_id": "..." }`

## 📝 Observações

- Sem OCR: PDFs escaneados podem não extrair texto

## 🔜 Próximos passos

- Implementar endpoint FastAPI `POST /v1/ask` reaproveitando `src/query.py`
- Extrair `retrieve(question, top_k, filters)` para reuso entre CLI e API
- Implementar prompting com presets (`default`, `conciso`, `citacoes_estritas`)
- Validação de entrada (tamanho de pergunta, filtros) e mapeamento de erros
- Timeouts e retries curtos para OpenAI
- Logs estruturados (com `request_id`) e métricas básicas (latência, tokens)
- Testes: unitários (schemas/prompt), integração (Chroma real, LLM mock), E2E pequeno

## 📝 Tarefas

- [ ] Estruturar `src/api/` (`main.py`, `schemas.py`, `service_retrieval.py`, `service_llm.py`, `prompting.py`, `auth.py` opcional)
- [ ] Implementar rota `POST /v1/ask`
- [ ] Validar variáveis de ambiente e limites (`DEFAULT_TOP_K`, `MAX_CONTEXT_CHARS`)
- [ ] Rate limit simples por chave (`X-API-Key`)
- [ ] Observabilidade: `request_id`, latência end-to-end, contagem de tokens
- [ ] Documentar comando de execução da API após implementação
