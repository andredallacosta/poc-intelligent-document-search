from unittest.mock import Mock

import pytest

from domain.services.email_rate_limiter import EmailRateLimiter


class TestEmailRateLimiter:
    """Testes unitários para EmailRateLimiter"""

    @pytest.fixture
    def mock_redis(self):
        """Mock do Redis client"""
        return Mock()

    def test_check_user_limit_under_limit(self, mock_redis):
        """Deve permitir quando usuário está abaixo do limite"""
        mock_redis.incr.return_value = 5
        rate_limiter = EmailRateLimiter(mock_redis)

        result = rate_limiter.check_user_limit("user-123")

        assert result is True
        mock_redis.incr.assert_called_once_with("email_limit:user:user-123:minute")

    def test_check_user_limit_at_limit(self, mock_redis):
        """Deve permitir quando usuário está no limite exato"""
        mock_redis.incr.return_value = 10
        rate_limiter = EmailRateLimiter(mock_redis)

        result = rate_limiter.check_user_limit("user-123")

        assert result is True

    def test_check_user_limit_exceeded(self, mock_redis):
        """Deve bloquear quando usuário excedeu o limite"""
        mock_redis.incr.return_value = 11
        rate_limiter = EmailRateLimiter(mock_redis)

        result = rate_limiter.check_user_limit("user-123")

        assert result is False

    def test_check_user_limit_sets_expiry_on_first_use(self, mock_redis):
        """Deve definir TTL na primeira vez que usuário envia email"""
        mock_redis.incr.return_value = 1
        rate_limiter = EmailRateLimiter(mock_redis)

        rate_limiter.check_user_limit("user-123")

        mock_redis.expire.assert_called_once()

    def test_check_global_limit_under_limit(self, mock_redis):
        """Deve permitir quando sistema está abaixo do limite global"""
        mock_redis.incr.return_value = 50
        rate_limiter = EmailRateLimiter(mock_redis)

        result = rate_limiter.check_global_limit()

        assert result is True
        mock_redis.incr.assert_called_once_with("email_limit:global:minute")

    def test_check_global_limit_exceeded(self, mock_redis):
        """Deve bloquear quando sistema excedeu limite global"""
        mock_redis.incr.return_value = 101
        rate_limiter = EmailRateLimiter(mock_redis)

        result = rate_limiter.check_global_limit()

        assert result is False

    def test_get_user_remaining_emails(self, mock_redis):
        """Deve retornar quantos emails o usuário ainda pode enviar"""
        mock_redis.get.return_value = b"3"
        rate_limiter = EmailRateLimiter(mock_redis)

        remaining = rate_limiter.get_user_remaining_emails("user-123")

        assert remaining == 7

    def test_get_user_remaining_emails_no_usage(self, mock_redis):
        """Deve retornar limite máximo quando usuário não enviou emails"""
        mock_redis.get.return_value = None
        rate_limiter = EmailRateLimiter(mock_redis)

        remaining = rate_limiter.get_user_remaining_emails("user-123")

        assert remaining == 10

    def test_reset_user_limit(self, mock_redis):
        """Deve resetar o limite de um usuário específico"""
        rate_limiter = EmailRateLimiter(mock_redis)

        result = rate_limiter.reset_user_limit("user-123")

        assert result is True
        mock_redis.delete.assert_called_once_with("email_limit:user:user-123:minute")

