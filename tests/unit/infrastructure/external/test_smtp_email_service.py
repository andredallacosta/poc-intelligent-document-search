from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

import pytest

from domain.exceptions.auth_exceptions import EmailDeliveryError
from infrastructure.external.smtp_email_service import SMTPEmailService


class TestSMTPEmailService:
    """Testes para SMTPEmailService"""

    @pytest.fixture
    def email_service(self):
        """Fixture para SMTPEmailService"""
        return SMTPEmailService(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_username="test@example.com",
            smtp_password="password123",
            smtp_use_tls=True,
            from_email="noreply@example.com",
            from_name="Test System",
            base_url="http://localhost:8000",
        )

    @pytest.mark.asyncio
    @patch("infrastructure.external.smtp_email_service.smtplib.SMTP")
    async def test_send_invitation_email_success(self, mock_smtp, email_service):
        """Testa envio bem-sucedido de email de convite"""
        # Arrange
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        # Act
        result = await email_service.send_invitation_email(
            email="user@example.com",
            full_name="João Silva",
            invitation_token="abc12345",
            invited_by_name="Admin User",
            municipality_name="Prefeitura de São Paulo",
        )
        # Assert
        assert result is True
        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "password123")
        mock_server.send_message.assert_called_once()
        # Verifica se a mensagem foi criada corretamente
        call_args = mock_server.send_message.call_args[0][0]
        assert isinstance(call_args, MIMEMultipart)
        assert "João Silva" in call_args["To"]
        assert "user@example.com" in call_args["To"]
        assert "Convite para acessar o Sistema" in call_args["Subject"]

    @pytest.mark.asyncio
    @patch("infrastructure.external.smtp_email_service.smtplib.SMTP")
    async def test_send_invitation_email_without_municipality(
        self, mock_smtp, email_service
    ):
        """Testa envio de email de convite sem prefeitura"""
        # Arrange
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        # Act
        result = await email_service.send_invitation_email(
            email="user@example.com",
            full_name="João Silva",
            invitation_token="abc12345",
            invited_by_name="Admin User",
        )
        # Assert
        assert result is True
        call_args = mock_server.send_message.call_args[0][0]
        assert "da Prefeitura" not in call_args["Subject"]

    @pytest.mark.asyncio
    @patch("infrastructure.external.smtp_email_service.smtplib.SMTP")
    async def test_send_password_reset_email_success(self, mock_smtp, email_service):
        """Testa envio bem-sucedido de email de redefinição de senha"""
        # Arrange
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        # Act
        result = await email_service.send_password_reset_email(
            email="user@example.com",
            full_name="João Silva",
            reset_token="reset123",
        )
        # Assert
        assert result is True
        call_args = mock_server.send_message.call_args[0][0]
        assert "Redefinição de senha" in call_args["Subject"]

    @pytest.mark.asyncio
    @patch("infrastructure.external.smtp_email_service.smtplib.SMTP")
    async def test_send_account_activated_email_success(self, mock_smtp, email_service):
        """Testa envio bem-sucedido de email de confirmação de ativação"""
        # Arrange
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        # Act
        result = await email_service.send_account_activated_email(
            email="user@example.com",
            full_name="João Silva",
        )
        # Assert
        assert result is True
        call_args = mock_server.send_message.call_args[0][0]
        assert "Conta ativada com sucesso" in call_args["Subject"]

    @pytest.mark.asyncio
    @patch("infrastructure.external.smtp_email_service.smtplib.SMTP")
    async def test_send_welcome_email_success(self, mock_smtp, email_service):
        """Testa envio bem-sucedido de email de boas-vindas"""
        # Arrange
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        # Act
        result = await email_service.send_welcome_email(
            email="user@example.com",
            full_name="João Silva",
            municipality_name="Prefeitura de São Paulo",
        )
        # Assert
        assert result is True
        call_args = mock_server.send_message.call_args[0][0]
        assert "Bem-vindo ao Sistema" in call_args["Subject"]
        assert "da Prefeitura de São Paulo" in call_args["Subject"]

    @pytest.mark.asyncio
    @patch("infrastructure.external.smtp_email_service.smtplib.SMTP")
    async def test_send_email_smtp_connection_error(self, mock_smtp, email_service):
        """Testa falha na conexão SMTP"""
        # Arrange
        mock_smtp.side_effect = Exception("Connection failed")
        # Act & Assert
        with pytest.raises(EmailDeliveryError) as exc_info:
            await email_service.send_invitation_email(
                email="user@example.com",
                full_name="João Silva",
                invitation_token="abc12345",
                invited_by_name="Admin User",
            )
        assert "Falha ao enviar email" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("infrastructure.external.smtp_email_service.smtplib.SMTP")
    async def test_send_email_authentication_error(self, mock_smtp, email_service):
        """Testa falha na autenticação SMTP"""
        # Arrange
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        mock_server.login.side_effect = Exception("Authentication failed")
        # Act & Assert
        with pytest.raises(EmailDeliveryError) as exc_info:
            await email_service.send_invitation_email(
                email="user@example.com",
                full_name="João Silva",
                invitation_token="abc12345",
                invited_by_name="Admin User",
            )
        assert "Falha ao enviar email" in str(exc_info.value)
        assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("infrastructure.external.smtp_email_service.smtplib.SMTP")
    async def test_send_email_without_tls(self, mock_smtp):
        """Testa envio de email sem TLS"""
        # Arrange
        email_service = SMTPEmailService(
            smtp_host="smtp.example.com",
            smtp_port=25,
            smtp_username="test@example.com",
            smtp_password="password123",
            smtp_use_tls=False,  # Sem TLS
            from_email="noreply@example.com",
            from_name="Test System",
            base_url="http://localhost:8000",
        )
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        # Act
        result = await email_service.send_invitation_email(
            email="user@example.com",
            full_name="João Silva",
            invitation_token="abc12345",
            invited_by_name="Admin User",
        )
        # Assert
        assert result is True
        mock_server.starttls.assert_not_called()  # TLS não deve ser chamado
        mock_server.login.assert_called_once()

    def test_create_invitation_html_content(self, email_service):
        """Testa criação de conteúdo HTML do email de convite"""
        # Act
        html_content = email_service._create_invitation_html(
            full_name="João Silva",
            invited_by_name="Admin User",
            activation_url="http://localhost:8000/auth/activate?token=abc123",
            municipality_name="Prefeitura de São Paulo",
        )
        # Assert
        assert "João Silva" in html_content
        assert "Admin User" in html_content
        assert "http://localhost:8000/auth/activate?token=abc123" in html_content
        assert "da Prefeitura de São Paulo" in html_content
        assert "<!DOCTYPE html>" in html_content
        assert "Ativar Minha Conta" in html_content

    def test_create_invitation_text_content(self, email_service):
        """Testa criação de conteúdo texto do email de convite"""
        # Act
        text_content = email_service._create_invitation_text(
            full_name="João Silva",
            invited_by_name="Admin User",
            activation_url="http://localhost:8000/auth/activate?token=abc123",
            municipality_name="Prefeitura de São Paulo",
        )
        # Assert
        assert "João Silva" in text_content
        assert "Admin User" in text_content
        assert "http://localhost:8000/auth/activate?token=abc123" in text_content
        assert "da Prefeitura de São Paulo" in text_content
        assert "Sistema de Documentos Inteligentes" in text_content

    def test_create_password_reset_html_content(self, email_service):
        """Testa criação de conteúdo HTML do email de redefinição de senha"""
        # Act
        html_content = email_service._create_password_reset_html(
            full_name="João Silva",
            reset_url="http://localhost:8000/auth/reset?token=reset123",
        )
        # Assert
        assert "João Silva" in html_content
        assert "http://localhost:8000/auth/reset?token=reset123" in html_content
        assert "Redefinir Senha" in html_content
        assert "<!DOCTYPE html>" in html_content

    def test_create_welcome_html_content(self, email_service):
        """Testa criação de conteúdo HTML do email de boas-vindas"""
        # Act
        html_content = email_service._create_welcome_html(
            full_name="João Silva",
            municipality_name="Prefeitura de São Paulo",
        )
        # Assert
        assert "João Silva" in html_content
        assert "da Prefeitura de São Paulo" in html_content
        assert "Bem-vindo ao Sistema" in html_content
        assert "<!DOCTYPE html>" in html_content

    def test_email_service_configuration(self):
        """Testa configuração do serviço de email"""
        # Act
        service = SMTPEmailService(
            smtp_host="custom.smtp.com",
            smtp_port=465,
            smtp_username="custom@example.com",
            smtp_password="custom_password",
            smtp_use_tls=False,
            from_email="custom_from@example.com",
            from_name="Custom System",
            base_url="https://custom.example.com",
        )
        # Assert
        assert service._smtp_host == "custom.smtp.com"
        assert service._smtp_port == 465
        assert service._smtp_username == "custom@example.com"
        assert service._smtp_password == "custom_password"
        assert service._smtp_use_tls is False
        assert service._from_email == "custom_from@example.com"
        assert service._from_name == "Custom System"
        assert service._base_url == "https://custom.example.com"

    def test_email_service_default_from_email(self):
        """Testa configuração padrão do from_email"""
        # Act
        service = SMTPEmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="test@example.com",
            smtp_password="password123",
        )
        # Assert
        assert (
            service._from_email == "test@example.com"
        )  # Deve usar smtp_username como padrão
