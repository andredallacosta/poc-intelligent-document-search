import logging
from datetime import timedelta
from typing import Optional

from redis import Redis

logger = logging.getLogger(__name__)


class EmailRateLimiter:
    """Serviço de rate limiting para envio de emails"""

    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    def check_user_limit(
        self, user_id: str, max_emails: int = 10, window_minutes: int = 1
    ) -> bool:
        """
        Verifica se usuário atingiu limite de emails por minuto

        Args:
            user_id: ID do usuário
            max_emails: Máximo de emails permitidos
            window_minutes: Janela de tempo em minutos

        Returns:
            bool: True se dentro do limite, False se excedeu
        """
        try:
            key = f"email_limit:user:{user_id}:minute"
            count = self._redis.incr(key)

            if count == 1:
                self._redis.expire(key, timedelta(minutes=window_minutes))

            is_within_limit = count <= max_emails

            if not is_within_limit:
                logger.warning(
                    "user_email_rate_limit_exceeded",
                    extra={
                        "user_id": user_id,
                        "count": count,
                        "limit": max_emails,
                        "window_minutes": window_minutes,
                    },
                )

            return is_within_limit

        except Exception as e:
            logger.error(
                "rate_limiter_check_user_error",
                extra={"user_id": user_id, "error": str(e)},
            )
            return True

    def check_global_limit(
        self, max_emails: int = 100, window_minutes: int = 1
    ) -> bool:
        """
        Verifica se sistema atingiu limite global de emails por minuto

        Args:
            max_emails: Máximo de emails permitidos globalmente
            window_minutes: Janela de tempo em minutos

        Returns:
            bool: True se dentro do limite, False se excedeu
        """
        try:
            key = "email_limit:global:minute"
            count = self._redis.incr(key)

            if count == 1:
                self._redis.expire(key, timedelta(minutes=window_minutes))

            is_within_limit = count <= max_emails

            if not is_within_limit:
                logger.warning(
                    "global_email_rate_limit_exceeded",
                    extra={
                        "count": count,
                        "limit": max_emails,
                        "window_minutes": window_minutes,
                    },
                )

            return is_within_limit

        except Exception as e:
            logger.error("rate_limiter_check_global_error", extra={"error": str(e)})
            return True

    def get_user_remaining_emails(
        self, user_id: str, max_emails: int = 10, window_minutes: int = 1
    ) -> Optional[int]:
        """
        Retorna quantos emails o usuário ainda pode enviar

        Args:
            user_id: ID do usuário
            max_emails: Máximo de emails permitidos
            window_minutes: Janela de tempo em minutos

        Returns:
            int: Número de emails restantes ou None se erro
        """
        try:
            key = f"email_limit:user:{user_id}:minute"
            count = self._redis.get(key)

            if count is None:
                return max_emails

            current_count = int(count)
            remaining = max(0, max_emails - current_count)

            return remaining

        except Exception as e:
            logger.error(
                "rate_limiter_get_remaining_error",
                extra={"user_id": user_id, "error": str(e)},
            )
            return None

    def reset_user_limit(self, user_id: str) -> bool:
        """
        Reseta o limite de um usuário específico

        Args:
            user_id: ID do usuário

        Returns:
            bool: True se resetado com sucesso
        """
        try:
            key = f"email_limit:user:{user_id}:minute"
            self._redis.delete(key)
            logger.info("user_rate_limit_reset", extra={"user_id": user_id})
            return True

        except Exception as e:
            logger.error(
                "rate_limiter_reset_error",
                extra={"user_id": user_id, "error": str(e)},
            )
            return False

