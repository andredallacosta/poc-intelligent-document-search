#!/bin/bash
# Deploy script para produção

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
BACKUP_DIR="./backups"
HEALTH_TIMEOUT=60

echo -e "${BLUE}🚀 Iniciando deploy para produção...${NC}"

# Verificar se arquivos necessários existem
if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo -e "${RED}❌ Arquivo $COMPOSE_FILE não encontrado!${NC}"
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}❌ Arquivo $ENV_FILE não encontrado!${NC}"
    exit 1
fi

# Criar diretório de backup se não existir
mkdir -p "$BACKUP_DIR"

# Backup antes do deploy
echo -e "${YELLOW}💾 Fazendo backup...${NC}"
if ./scripts/backup.sh; then
    echo -e "${GREEN}✅ Backup concluído!${NC}"
else
    echo -e "${RED}❌ Backup falhou!${NC}"
    exit 1
fi

# Pull das novas imagens
echo -e "${BLUE}📥 Baixando novas imagens...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull

# Deploy com zero downtime
echo -e "${BLUE}🔄 Fazendo deploy...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --remove-orphans

# Aguardar serviços ficarem prontos
echo -e "${YELLOW}⏳ Aguardando serviços ficarem prontos...${NC}"
sleep 10

# Health check
echo -e "${BLUE}🏥 Verificando saúde dos serviços...${NC}"
if timeout "$HEALTH_TIMEOUT" ./scripts/health-check.sh; then
    echo -e "${GREEN}✅ Deploy concluído com sucesso!${NC}"
else
    echo -e "${RED}❌ Health check falhou!${NC}"
    echo -e "${YELLOW}🔄 Fazendo rollback...${NC}"
    
    # Rollback (restart com imagens anteriores)
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
    
    echo -e "${RED}❌ Deploy falhou e rollback foi executado!${NC}"
    exit 1
fi

# Limpeza de imagens antigas
echo -e "${BLUE}🧹 Limpando imagens antigas...${NC}"
docker image prune -f

# Mostrar status final
echo -e "${BLUE}📊 Status dos serviços:${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

echo -e "${GREEN}🎉 Deploy concluído com sucesso!${NC}"
echo -e "${BLUE}📝 Logs disponíveis em: ./logs/${NC}"
echo -e "${BLUE}🔍 Monitoramento: curl http://localhost/api/v1/queue/info${NC}"
