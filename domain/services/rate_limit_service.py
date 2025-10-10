import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

from domain.exceptions.auth_exceptions import RateLimitExceededError
from infrastructure.external.redis_client import RedisClient

logger = logging.getLogger(__name__)


class RateLimitService:
    """
    Serviço de rate limiting usando Redis com algoritmo Fixed Window.

    ZERO CUSTO - Usa infraestrutura Redis existente.
    Algoritmo simples e eficiente para proteger endpoints críticos.
    """

    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client

        # Configurações de rate limit por endpoint (CONSERVADORAS para budget apertado)
        self._limits = {
            # Autenticação - CRÍTICO para segurança
            "/api/v1/auth/login": {
                "per_ip": {"count": 5, "window": 60},  # 5 tentativas por IP por minuto
                "per_email": {
                    "count": 3,
                    "window": 60,
                },  # 3 tentativas por email por minuto
            },
            # Google OAuth2 - Menos restritivo (Google já protege)
            "/api/v1/auth/google": {
                "per_ip": {
                    "count": 10,
                    "window": 60,
                },  # 10 tentativas por IP por minuto
            },
            # Chat - Moderado (protege custos OpenAI)
            "/api/v1/chat/ask": {
                "per_user": {
                    "count": 20,
                    "window": 60,
                },  # 20 mensagens por usuário por minuto
                "per_ip": {"count": 30, "window": 60},  # 30 mensagens por IP por minuto
            },
            # Default para outros endpoints
            "default": {
                "per_ip": {"count": 60, "window": 60},  # 60 requests por IP por minuto
            },
        }

    async def check_rate_limit(
        self, endpoint: str, identifier: str, limit_type: str
    ) -> Tuple[bool, Optional[int]]:
        """
        Verifica se request está dentro do rate limit.

        Args:
            endpoint: Caminho do endpoint (ex: /api/v1/auth/login)
            identifier: IP, user_id, email, etc.
            limit_type: "per_ip", "per_user", "per_email"

        Returns:
            (is_allowed, retry_after_seconds)
        """
        try:
            # Obtém configuração do endpoint
            limit_config = self._get_limit_config(endpoint, limit_type)
            if not limit_config:
                return True, None

            # Chave Redis: rate_limit:endpoint:type:identifier:window
            window_start = int(datetime.utcnow().timestamp()) // limit_config["window"]
            key = f"rate_limit:{endpoint}:{limit_type}:{identifier}:{window_start}"

            # Obtém contador atual
            current_count = await self._get_counter(key)

            # Verifica se excedeu limite
            if current_count >= limit_config["count"]:
                retry_after = limit_config["window"] - (
                    int(datetime.utcnow().timestamp()) % limit_config["window"]
                )

                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "endpoint": endpoint,
                        "limit_type": limit_type,
                        "identifier": identifier,
                        "current_count": current_count,
                        "limit": limit_config["count"],
                        "retry_after": retry_after,
                    },
                )

                return False, retry_after

            # Incrementa contador
            await self._increment_counter(key, limit_config["window"])

            return True, None

        except Exception as e:
            logger.error(f"Erro no rate limiting: {e}")
            # Em caso de erro, permite request (fail-open para não quebrar sistema)
            return True, None

    async def check_multiple_limits(
        self, endpoint: str, checks: Dict[str, str]
    ) -> None:
        """
        Verifica múltiplos rate limits e levanta exceção se algum for excedido.

        Args:
            endpoint: Caminho do endpoint
            checks: Dict com limit_type -> identifier
                   Ex: {"per_ip": "192.168.1.1", "per_email": "user@test.com"}

        Raises:
            RateLimitExceededError: Se algum limite for excedido
        """
        for limit_type, identifier in checks.items():
            is_allowed, retry_after = await self.check_rate_limit(
                endpoint, identifier, limit_type
            )

            if not is_allowed:
                limit_config = self._get_limit_config(endpoint, limit_type)
                raise RateLimitExceededError(
                    f"Rate limit exceeded for {limit_type}. "
                    f"Limit: {limit_config['count']} requests per {limit_config['window']} seconds. "
                    f"Try again in {retry_after} seconds."
                )

    def _get_limit_config(self, endpoint: str, limit_type: str) -> Optional[Dict]:
        """Obtém configuração de limite para endpoint e tipo"""
        endpoint_config = self._limits.get(endpoint, self._limits.get("default", {}))
        return endpoint_config.get(limit_type)

    async def _get_counter(self, key: str) -> int:
        """Obtém contador atual do Redis"""
        try:
            # Usa comando Redis nativo para performance
            count = await self._redis.redis.get(key)
            return int(count) if count else 0
        except Exception:
            return 0

    async def _increment_counter(self, key: str, window_seconds: int) -> None:
        """Incrementa contador com TTL automático"""
        try:
            # Pipeline Redis para atomicidade e performance
            async with self._redis.redis.pipeline() as pipe:
                pipe.incr(key)
                pipe.expire(key, window_seconds)
                await pipe.execute()
        except Exception as e:
            logger.error(f"Erro ao incrementar contador: {e}")

    async def reset_rate_limit(
        self, endpoint: str, identifier: str, limit_type: str
    ) -> bool:
        """
        Reset manual de rate limit (para casos especiais).

        Útil para:
        - Testes
        - Usuários bloqueados incorretamente
        - Situações de emergência
        """
        try:
            window_start = (
                int(datetime.utcnow().timestamp()) // 60
            )  # Assume janela de 60s
            key = f"rate_limit:{endpoint}:{limit_type}:{identifier}:{window_start}"

            result = await self._redis.delete(key)

            if result:
                logger.info(
                    "Rate limit reset",
                    extra={
                        "endpoint": endpoint,
                        "limit_type": limit_type,
                        "identifier": identifier,
                    },
                )

            return result

        except Exception as e:
            logger.error(f"Erro ao resetar rate limit: {e}")
            return False

    async def get_rate_limit_status(
        self, endpoint: str, identifier: str, limit_type: str
    ) -> Dict:
        """
        Obtém status atual do rate limit para debugging/monitoramento.

        Returns:
            {
                "current_count": int,
                "limit": int,
                "window_seconds": int,
                "reset_time": datetime,
                "is_blocked": bool
            }
        """
        try:
            limit_config = self._get_limit_config(endpoint, limit_type)
            if not limit_config:
                return {"error": "No rate limit configured"}

            window_start = int(datetime.utcnow().timestamp()) // limit_config["window"]
            key = f"rate_limit:{endpoint}:{limit_type}:{identifier}:{window_start}"

            current_count = await self._get_counter(key)
            reset_time = datetime.fromtimestamp(
                (window_start + 1) * limit_config["window"]
            )

            return {
                "current_count": current_count,
                "limit": limit_config["count"],
                "window_seconds": limit_config["window"],
                "reset_time": reset_time.isoformat(),
                "is_blocked": current_count >= limit_config["count"],
                "requests_remaining": max(0, limit_config["count"] - current_count),
            }

        except Exception as e:
            logger.error(f"Erro ao obter status do rate limit: {e}")
            return {"error": str(e)}
