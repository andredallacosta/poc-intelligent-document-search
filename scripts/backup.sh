#!/bin/bash
# Backup script para dados críticos

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
REDIS_CONTAINER="${REDIS_CONTAINER:-redis}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

echo -e "${BLUE}💾 Iniciando backup...${NC}"

# Criar diretório de backup
mkdir -p "$BACKUP_DIR"

# Backup Redis (dados das filas)
echo -e "${YELLOW}📦 Fazendo backup do Redis...${NC}"
if docker ps --format "table {{.Names}}" | grep -q "$REDIS_CONTAINER"; then
    # Forçar save do Redis
    docker exec "$REDIS_CONTAINER" redis-cli BGSAVE
    
    # Aguardar save completar
    sleep 5
    
    # Copiar dump do Redis
    if docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$BACKUP_DIR/redis_$DATE.rdb" 2>/dev/null; then
        echo -e "${GREEN}✅ Backup Redis: redis_$DATE.rdb${NC}"
    else
        echo -e "${YELLOW}⚠️ Backup Redis falhou (container pode não ter dados)${NC}"
    fi
    
    # Backup do AOF se existir
    if docker exec "$REDIS_CONTAINER" test -f /data/appendonly.aof 2>/dev/null; then
        docker cp "$REDIS_CONTAINER:/data/appendonly.aof" "$BACKUP_DIR/redis_aof_$DATE.aof"
        echo -e "${GREEN}✅ Backup Redis AOF: redis_aof_$DATE.aof${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Container Redis não encontrado, pulando backup Redis${NC}"
fi

# Backup dos logs importantes
echo -e "${YELLOW}📋 Fazendo backup dos logs...${NC}"
if [[ -d "./logs" ]]; then
    tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" ./logs/ 2>/dev/null
    echo -e "${GREEN}✅ Backup logs: logs_$DATE.tar.gz${NC}"
else
    echo -e "${YELLOW}⚠️ Diretório de logs não encontrado${NC}"
fi

# Backup das configurações
echo -e "${YELLOW}⚙️ Fazendo backup das configurações...${NC}"
CONFIG_FILES=(
    "docker-compose.prod.yml"
    ".env.prod"
    "redis.conf"
    "nginx/nginx.conf"
)

for file in "${CONFIG_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        cp "$file" "$BACKUP_DIR/$(basename "$file")_$DATE"
        echo -e "${GREEN}✅ Backup config: $(basename "$file")_$DATE${NC}"
    fi
done

# Backup do estado dos containers
echo -e "${YELLOW}🐳 Fazendo backup do estado dos containers...${NC}"
docker-compose -f docker-compose.prod.yml ps > "$BACKUP_DIR/containers_state_$DATE.txt" 2>/dev/null || true
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" > "$BACKUP_DIR/images_$DATE.txt" 2>/dev/null || true

# Backup das variáveis de ambiente (sem valores sensíveis)
echo -e "${YELLOW}🔐 Fazendo backup das variáveis de ambiente...${NC}"
if [[ -f ".env.prod" ]]; then
    grep -E "^[A-Z_]+=.*" .env.prod | sed 's/=.*/=***REDACTED***/' > "$BACKUP_DIR/env_template_$DATE.txt"
    echo -e "${GREEN}✅ Template de variáveis salvo (valores redacted)${NC}"
fi

# Limpeza de backups antigos
echo -e "${YELLOW}🧹 Limpando backups antigos (>${RETENTION_DAYS} dias)...${NC}"
DELETED_COUNT=0

# Limpar arquivos antigos
for pattern in "redis_*.rdb" "redis_aof_*.aof" "logs_*.tar.gz" "*_$DATE.*"; do
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            rm "$file"
            DELETED_COUNT=$((DELETED_COUNT + 1))
        fi
    done < <(find "$BACKUP_DIR" -name "$pattern" -mtime +$RETENTION_DAYS -print0 2>/dev/null)
done

if [[ $DELETED_COUNT -gt 0 ]]; then
    echo -e "${GREEN}✅ $DELETED_COUNT arquivo(s) antigo(s) removido(s)${NC}"
else
    echo -e "${BLUE}ℹ️ Nenhum arquivo antigo para remover${NC}"
fi

# Mostrar resumo do backup
echo -e "${BLUE}📊 Resumo do backup:${NC}"
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "*$DATE*" | wc -l)

echo -e "${GREEN}✅ Backup concluído!${NC}"
echo -e "${BLUE}📁 Diretório: $BACKUP_DIR${NC}"
echo -e "${BLUE}📦 Arquivos criados: $BACKUP_COUNT${NC}"
echo -e "${BLUE}💾 Tamanho total: $BACKUP_SIZE${NC}"
echo -e "${BLUE}📅 Data: $DATE${NC}"

# Listar arquivos criados
echo -e "${BLUE}📋 Arquivos de backup criados:${NC}"
find "$BACKUP_DIR" -name "*$DATE*" -exec basename {} \; | sort

exit 0
