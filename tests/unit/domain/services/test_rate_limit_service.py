import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from domain.services.rate_limit_service import RateLimitService
from domain.exceptions.auth_exceptions import RateLimitExceededError


class TestRateLimitService:
    
    @pytest.fixture
    def mock_redis_client(self):
        """Mock Redis client"""
        mock_redis = AsyncMock()
        mock_redis.redis = AsyncMock()
        return mock_redis
    
    @pytest.fixture
    def rate_limit_service(self, mock_redis_client):
        """Rate limit service with mocked Redis"""
        return RateLimitService(mock_redis_client)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self, rate_limit_service, mock_redis_client):
        """Test rate limit check when within limit"""
        # Mock Redis responses
        mock_redis_client.redis.get.return_value = "2"  # Current count
        mock_redis_client.redis.pipeline.return_value.__aenter__.return_value.execute = AsyncMock()
        
        # Check rate limit
        is_allowed, retry_after = await rate_limit_service.check_rate_limit(
            endpoint="/api/v1/auth/login",
            identifier="192.168.1.1",
            limit_type="per_ip"
        )
        
        assert is_allowed is True
        assert retry_after is None
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, rate_limit_service, mock_redis_client):
        """Test rate limit check when limit exceeded"""
        # Mock Redis responses - limit is 5 for login per IP
        mock_redis_client.redis.get.return_value = "5"  # At limit
        
        # Check rate limit
        is_allowed, retry_after = await rate_limit_service.check_rate_limit(
            endpoint="/api/v1/auth/login",
            identifier="192.168.1.1",
            limit_type="per_ip"
        )
        
        assert is_allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    @pytest.mark.asyncio
    async def test_check_multiple_limits_success(self, rate_limit_service, mock_redis_client):
        """Test checking multiple limits when all are within bounds"""
        # Mock Redis responses
        mock_redis_client.redis.get.return_value = "1"  # Low count
        mock_redis_client.redis.pipeline.return_value.__aenter__.return_value.execute = AsyncMock()
        
        # Should not raise exception
        await rate_limit_service.check_multiple_limits(
            endpoint="/api/v1/auth/login",
            checks={
                "per_ip": "192.168.1.1",
                "per_email": "test@example.com"
            }
        )
    
    @pytest.mark.asyncio
    async def test_check_multiple_limits_exceeded(self, rate_limit_service, mock_redis_client):
        """Test checking multiple limits when one is exceeded"""
        # Mock Redis responses - first call returns limit exceeded
        mock_redis_client.redis.get.side_effect = ["5", "2"]  # IP limit exceeded, email OK
        
        # Should raise exception
        with pytest.raises(RateLimitExceededError) as exc_info:
            await rate_limit_service.check_multiple_limits(
                endpoint="/api/v1/auth/login",
                checks={
                    "per_ip": "192.168.1.1",
                    "per_email": "test@example.com"
                }
            )
        
        assert "Rate limit exceeded for per_ip" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, rate_limit_service, mock_redis_client):
        """Test resetting rate limit"""
        # Mock Redis delete response
        mock_redis_client.delete.return_value = True
        
        result = await rate_limit_service.reset_rate_limit(
            endpoint="/api/v1/auth/login",
            identifier="192.168.1.1",
            limit_type="per_ip"
        )
        
        assert result is True
        mock_redis_client.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self, rate_limit_service, mock_redis_client):
        """Test getting rate limit status"""
        # Mock Redis response
        mock_redis_client.redis.get.return_value = "3"
        
        status = await rate_limit_service.get_rate_limit_status(
            endpoint="/api/v1/auth/login",
            identifier="192.168.1.1",
            limit_type="per_ip"
        )
        
        assert status["current_count"] == 3
        assert status["limit"] == 5  # Default limit for login per IP
        assert status["window_seconds"] == 60
        assert status["is_blocked"] is False
        assert status["requests_remaining"] == 2
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, rate_limit_service, mock_redis_client):
        """Test graceful handling of Redis errors"""
        # Mock Redis error
        mock_redis_client.redis.get.side_effect = Exception("Redis connection failed")
        
        # Should not raise exception (fail-open)
        is_allowed, retry_after = await rate_limit_service.check_rate_limit(
            endpoint="/api/v1/auth/login",
            identifier="192.168.1.1",
            limit_type="per_ip"
        )
        
        assert is_allowed is True  # Fail-open behavior
        assert retry_after is None
    
    def test_get_limit_config(self, rate_limit_service):
        """Test getting limit configuration"""
        # Test existing endpoint
        config = rate_limit_service._get_limit_config("/api/v1/auth/login", "per_ip")
        assert config is not None
        assert config["count"] == 5
        assert config["window"] == 60
        
        # Test non-existing endpoint (should use default)
        config = rate_limit_service._get_limit_config("/api/v1/unknown", "per_ip")
        assert config is not None
        assert config["count"] == 60  # Default limit
        
        # Test non-existing limit type
        config = rate_limit_service._get_limit_config("/api/v1/auth/login", "per_unknown")
        assert config is None
    
    @pytest.mark.asyncio
    async def test_increment_counter_error_handling(self, rate_limit_service, mock_redis_client):
        """Test increment counter handles Redis errors gracefully"""
        # Mock Redis pipeline to raise exception
        mock_redis_client.redis.pipeline.side_effect = Exception("Redis connection failed")
        
        # Should not raise exception (graceful error handling)
        await rate_limit_service._increment_counter("test_key", 60)
        
        # Verify pipeline was attempted
        mock_redis_client.redis.pipeline.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_limits(self, rate_limit_service, mock_redis_client):
        """Test rate limits for chat endpoint"""
        # Mock Redis responses
        mock_redis_client.redis.get.return_value = "10"  # Within limit
        mock_redis_client.redis.pipeline.return_value.__aenter__.return_value.execute = AsyncMock()
        
        # Check chat rate limit
        is_allowed, retry_after = await rate_limit_service.check_rate_limit(
            endpoint="/api/v1/chat/ask",
            identifier="user123",
            limit_type="per_user"
        )
        
        assert is_allowed is True
        assert retry_after is None
    
    @pytest.mark.asyncio
    async def test_google_oauth_limits(self, rate_limit_service, mock_redis_client):
        """Test rate limits for Google OAuth endpoint"""
        # Mock Redis responses
        mock_redis_client.redis.get.return_value = "5"  # Within limit
        mock_redis_client.redis.pipeline.return_value.__aenter__.return_value.execute = AsyncMock()
        
        # Check Google OAuth rate limit
        is_allowed, retry_after = await rate_limit_service.check_rate_limit(
            endpoint="/api/v1/auth/google",
            identifier="192.168.1.1",
            limit_type="per_ip"
        )
        
        assert is_allowed is True
        assert retry_after is None
