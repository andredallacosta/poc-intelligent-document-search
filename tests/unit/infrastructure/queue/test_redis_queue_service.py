from unittest.mock import Mock, patch

import pytest


class TestRedisQueueServiceEmailSending:
    """Testes unitários para enqueue_email_sending do RedisQueueService"""

    @patch("infrastructure.queue.redis_queue.Redis")
    @patch("infrastructure.queue.redis_queue.Queue")
    def test_enqueue_email_sending_success(self, mock_queue_class, mock_redis):
        """Deve enfileirar email com sucesso"""
        from infrastructure.queue.redis_queue import RedisQueueService

        mock_queue = Mock()
        mock_job = Mock()
        mock_job.id = "job-123"
        mock_queue.enqueue.return_value = mock_job
        mock_queue_class.return_value = mock_queue

        mock_redis_instance = Mock()
        mock_redis.from_url.return_value = mock_redis_instance

        service = RedisQueueService()

        job_id = service.enqueue_email_sending(
            email_type="invitation",
            recipient_email="test@example.com",
            recipient_name="Test User",
            template_data={"invitation_token": "token123"},
            priority="high",
        )

        assert job_id == "job-123"
        mock_queue.enqueue.assert_called_once()

        call_kwargs = mock_queue.enqueue.call_args.kwargs
        assert call_kwargs["job_timeout"] == "2m"
        assert call_kwargs["retry"].max == 3
        assert call_kwargs["meta"]["priority"] == "high"
        assert call_kwargs["meta"]["email_type"] == "invitation"

    @patch("infrastructure.queue.redis_queue.Redis")
    @patch("infrastructure.queue.redis_queue.Queue")
    def test_enqueue_email_sending_default_priority(self, mock_queue_class, mock_redis):
        """Deve usar prioridade 'normal' como padrão"""
        from infrastructure.queue.redis_queue import RedisQueueService

        mock_queue = Mock()
        mock_job = Mock()
        mock_job.id = "job-456"
        mock_queue.enqueue.return_value = mock_job
        mock_queue_class.return_value = mock_queue

        mock_redis_instance = Mock()
        mock_redis.from_url.return_value = mock_redis_instance

        service = RedisQueueService()

        job_id = service.enqueue_email_sending(
            email_type="welcome",
            recipient_email="test@example.com",
            recipient_name="Test User",
            template_data={},
        )

        call_kwargs = mock_queue.enqueue.call_args.kwargs
        assert call_kwargs["meta"]["priority"] == "normal"

