# Dockerfile para API + Workers
FROM python:3.11-slim

# Metadados
LABEL maintainer="Intelligent Document Search Team"
LABEL description="FastAPI + Redis Workers para processamento de documentos"

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Criar usuário não-root para segurança
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copiar e instalar dependências Python
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copiar código da aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p logs temp && \
    chown -R appuser:appuser /app

# Mudar para usuário não-root
USER appuser

# Expor porta da API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando padrão (pode ser sobrescrito)
CMD ["uvicorn", "interface.main:app", "--host", "0.0.0.0", "--port", "8000"]