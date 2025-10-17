from unittest.mock import AsyncMock, Mock, patch

import pytest

from infrastructure.queue.jobs import send_email_job


class TestSendEmailJob:
    """Testes unitários para send_email_job"""

    @patch("infrastructure.queue.jobs.get_current_job")
    @patch("infrastructure.queue.jobs.asyncio.run")
    def test_send_invitation_email_success(self, mock_asyncio_run, mock_get_job):
        """Deve enviar email de convite com sucesso"""
        mock_job = Mock()
        mock_job.id = "job-123"
        mock_get_job.return_value = mock_job

        mock_asyncio_run.return_value = True

        result = send_email_job(
            email_type="invitation",
            recipient_email="test@example.com",
            recipient_name="Test User",
            template_data={
                "invitation_token": "token123",
                "invited_by_name": "Admin",
            },
        )

        assert result["status"] == "sent"
        assert result["recipient"] == "test@example.com"
        assert result["email_type"] == "invitation"
        mock_asyncio_run.assert_called_once()

    @patch("infrastructure.queue.jobs.get_current_job")
    @patch("infrastructure.queue.jobs.asyncio.run")
    def test_send_welcome_email_success(self, mock_asyncio_run, mock_get_job):
        """Deve enviar email de boas-vindas com sucesso"""
        mock_job = Mock()
        mock_job.id = "job-456"
        mock_get_job.return_value = mock_job

        mock_asyncio_run.return_value = True

        result = send_email_job(
            email_type="welcome",
            recipient_email="test@example.com",
            recipient_name="Test User",
            template_data={},
        )

        assert result["status"] == "sent"
        assert result["email_type"] == "welcome"
        mock_asyncio_run.assert_called_once()

    @patch("infrastructure.queue.jobs.get_current_job")
    @patch("infrastructure.queue.jobs.asyncio.run")
    def test_send_email_unknown_type_raises_error(
        self, mock_asyncio_run, mock_get_job
    ):
        """Deve lançar exceção para tipo de email desconhecido"""
        mock_job = Mock()
        mock_get_job.return_value = mock_job

        mock_asyncio_run.side_effect = ValueError("Tipo de email desconhecido: unknown_type")

        with pytest.raises(ValueError) as exc_info:
            send_email_job(
                email_type="unknown_type",
                recipient_email="test@example.com",
                recipient_name="Test User",
                template_data={},
            )

        assert "Tipo de email desconhecido" in str(exc_info.value)

    @patch("infrastructure.queue.jobs.get_current_job")
    @patch("infrastructure.queue.jobs.asyncio.run")
    def test_send_email_smtp_failure_raises_exception(
        self, mock_asyncio_run, mock_get_job
    ):
        """Deve propagar exceção quando SMTP falhar"""
        mock_job = Mock()
        mock_job.id = "job-789"
        mock_get_job.return_value = mock_job

        mock_asyncio_run.side_effect = Exception("SMTP connection failed")

        with pytest.raises(Exception) as exc_info:
            send_email_job(
                email_type="invitation",
                recipient_email="test@example.com",
                recipient_name="Test User",
                template_data={
                    "invitation_token": "token",
                    "invited_by_name": "Admin",
                },
            )

        assert "SMTP connection failed" in str(exc_info.value)

