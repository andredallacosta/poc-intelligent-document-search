#!/bin/bash
# Health check script para verificar todos os serviços

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
API_URL="${API_URL:-http://localhost:8000}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
MAX_RETRIES=5
RETRY_DELAY=5

echo -e "${BLUE}🏥 Verificando saúde dos serviços...${NC}"

# Função para retry
retry_command() {
    local cmd="$1"
    local description="$2"
    local retries=0
    
    while [[ $retries -lt $MAX_RETRIES ]]; do
        if eval "$cmd" &>/dev/null; then
            echo -e "${GREEN}✅ $description: OK${NC}"
            return 0
        else
            retries=$((retries + 1))
            if [[ $retries -lt $MAX_RETRIES ]]; then
                echo -e "${YELLOW}⏳ $description: Tentativa $retries/$MAX_RETRIES falhou, tentando novamente em ${RETRY_DELAY}s...${NC}"
                sleep $RETRY_DELAY
            fi
        fi
    done
    
    echo -e "${RED}❌ $description: FALHOU após $MAX_RETRIES tentativas${NC}"
    return 1
}

# Verificar API Health
echo -e "${BLUE}🔍 Verificando API...${NC}"
if ! retry_command "curl -f -s '$API_URL/health'" "API Health"; then
    echo -e "${RED}❌ API não está respondendo em $API_URL/health${NC}"
    exit 1
fi

# Verificar Redis
echo -e "${BLUE}🔍 Verificando Redis...${NC}"
if command -v redis-cli &> /dev/null; then
    if ! retry_command "redis-cli -h '$REDIS_HOST' -p '$REDIS_PORT' ping | grep -q PONG" "Redis Connection"; then
        echo -e "${RED}❌ Redis não está respondendo em $REDIS_HOST:$REDIS_PORT${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️ redis-cli não encontrado, pulando verificação direta do Redis${NC}"
fi

# Verificar Queue Health
echo -e "${BLUE}🔍 Verificando Redis Queue...${NC}"
if ! retry_command "curl -f -s '$API_URL/api/v1/queue/health' | grep -q '\"status\":\"healthy\"'" "Redis Queue"; then
    echo -e "${RED}❌ Redis Queue não está saudável${NC}"
    exit 1
fi

# Verificar informações das filas
echo -e "${BLUE}🔍 Verificando filas...${NC}"
QUEUE_INFO=$(curl -s "$API_URL/api/v1/queue/info" 2>/dev/null || echo "{}")
if echo "$QUEUE_INFO" | grep -q "document_processing"; then
    echo -e "${GREEN}✅ Fila de processamento: OK${NC}"
else
    echo -e "${YELLOW}⚠️ Fila de processamento não encontrada${NC}"
fi

if echo "$QUEUE_INFO" | grep -q "cleanup_tasks"; then
    echo -e "${GREEN}✅ Fila de limpeza: OK${NC}"
else
    echo -e "${YELLOW}⚠️ Fila de limpeza não encontrada${NC}"
fi

# Verificar se há workers ativos
echo -e "${BLUE}🔍 Verificando workers...${NC}"
WORKERS_COUNT=$(echo "$QUEUE_INFO" | grep -o '"workers":[0-9]*' | grep -o '[0-9]*' | head -1 || echo "0")
if [[ "$WORKERS_COUNT" -gt 0 ]]; then
    echo -e "${GREEN}✅ Workers ativos: $WORKERS_COUNT${NC}"
else
    echo -e "${YELLOW}⚠️ Nenhum worker ativo detectado${NC}"
fi

# Verificar logs de erro recentes
echo -e "${BLUE}🔍 Verificando logs de erro...${NC}"
if [[ -d "./logs" ]]; then
    ERROR_COUNT=$(find ./logs -name "*.log" -mtime -1 -exec grep -l "ERROR\|CRITICAL" {} \; 2>/dev/null | wc -l || echo "0")
    if [[ "$ERROR_COUNT" -eq 0 ]]; then
        echo -e "${GREEN}✅ Sem erros críticos nas últimas 24h${NC}"
    else
        echo -e "${YELLOW}⚠️ $ERROR_COUNT arquivo(s) com erros encontrados nas últimas 24h${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Diretório de logs não encontrado${NC}"
fi

# Verificar espaço em disco
echo -e "${BLUE}🔍 Verificando espaço em disco...${NC}"
DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
if [[ "$DISK_USAGE" -lt 80 ]]; then
    echo -e "${GREEN}✅ Espaço em disco: ${DISK_USAGE}% usado${NC}"
elif [[ "$DISK_USAGE" -lt 90 ]]; then
    echo -e "${YELLOW}⚠️ Espaço em disco: ${DISK_USAGE}% usado (atenção)${NC}"
else
    echo -e "${RED}❌ Espaço em disco: ${DISK_USAGE}% usado (crítico)${NC}"
fi

# Verificar memória Redis (se possível)
if command -v redis-cli &> /dev/null; then
    echo -e "${BLUE}🔍 Verificando memória Redis...${NC}"
    REDIS_MEMORY=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" info memory 2>/dev/null | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r' || echo "N/A")
    if [[ "$REDIS_MEMORY" != "N/A" ]]; then
        echo -e "${GREEN}✅ Memória Redis: $REDIS_MEMORY${NC}"
    fi
fi

# Resumo final
echo -e "${BLUE}📊 Resumo do Health Check:${NC}"
echo -e "${GREEN}✅ Todos os serviços essenciais estão funcionando!${NC}"
echo -e "${BLUE}🔗 API: $API_URL${NC}"
echo -e "${BLUE}🔗 Queue Info: $API_URL/api/v1/queue/info${NC}"
echo -e "${BLUE}🔗 API Docs: $API_URL/docs${NC}"

exit 0
