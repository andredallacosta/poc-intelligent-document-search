#!/bin/bash
# Build script para Docker images

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
IMAGE_NAME="intelligent-document-search"
REGISTRY="${DOCKER_REGISTRY:-localhost}"
TAG="${TAG:-latest}"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${TAG}"

echo -e "${BLUE}🐳 Building Docker image...${NC}"
echo -e "${YELLOW}Image: ${FULL_IMAGE}${NC}"

# Build da imagem
docker build \
    --tag "${IMAGE_NAME}:${TAG}" \
    --tag "${IMAGE_NAME}:latest" \
    --tag "${FULL_IMAGE}" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --build-arg VCS_REF="$(git rev-parse --short HEAD)" \
    .

echo -e "${GREEN}✅ Build concluído!${NC}"

# Mostrar tamanho da imagem
echo -e "${BLUE}📊 Tamanho da imagem:${NC}"
docker images "${IMAGE_NAME}:${TAG}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Testar a imagem
echo -e "${BLUE}🧪 Testando imagem...${NC}"
if docker run --rm "${IMAGE_NAME}:${TAG}" python -c "import interface.main; print('✅ Import OK')"; then
    echo -e "${GREEN}✅ Teste da imagem passou!${NC}"
else
    echo -e "${RED}❌ Teste da imagem falhou!${NC}"
    exit 1
fi

# Push para registry (se especificado)
if [[ "${REGISTRY}" != "localhost" && "${PUSH:-false}" == "true" ]]; then
    echo -e "${BLUE}📤 Pushing para registry...${NC}"
    docker push "${FULL_IMAGE}"
    echo -e "${GREEN}✅ Push concluído!${NC}"
fi

echo -e "${GREEN}🎉 Build process completo!${NC}"
