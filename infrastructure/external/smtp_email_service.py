import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from domain.exceptions.auth_exceptions import EmailDeliveryError
from domain.services.email_service import EmailService

logger = logging.getLogger(__name__)


class SMTPEmailService(EmailService):
    """Implementação do EmailService usando SMTP"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        smtp_use_tls: bool = True,
        from_email: str = None,
        from_name: str = "Sistema de Documentos Inteligentes",
        base_url: str = "http://localhost:8000",
    ):
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_username = smtp_username
        self._smtp_password = smtp_password
        self._smtp_use_tls = smtp_use_tls
        self._from_email = from_email or smtp_username
        self._from_name = from_name
        self._base_url = base_url

    async def send_invitation_email(
        self,
        email: str,
        full_name: str,
        invitation_token: str,
        invited_by_name: str,
        municipality_name: Optional[str] = None,
    ) -> bool:
        """Envia email de convite para ativação de conta"""

        activation_url = f"{self._base_url}/auth/activate?token={invitation_token}"
        municipality_text = f" da {municipality_name}" if municipality_name else ""

        subject = f"Convite para acessar o Sistema de Documentos Inteligentes{municipality_text}"

        html_content = self._create_invitation_html(
            full_name=full_name,
            invited_by_name=invited_by_name,
            activation_url=activation_url,
            municipality_name=municipality_name,
        )

        text_content = self._create_invitation_text(
            full_name=full_name,
            invited_by_name=invited_by_name,
            activation_url=activation_url,
            municipality_name=municipality_name,
        )

        return await self._send_email(
            to_email=email,
            to_name=full_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_password_reset_email(
        self,
        email: str,
        full_name: str,
        reset_token: str,
    ) -> bool:
        """Envia email de redefinição de senha"""

        reset_url = f"{self._base_url}/auth/reset-password?token={reset_token}"

        subject = "Redefinição de senha - Sistema de Documentos Inteligentes"

        html_content = self._create_password_reset_html(
            full_name=full_name,
            reset_url=reset_url,
        )

        text_content = self._create_password_reset_text(
            full_name=full_name,
            reset_url=reset_url,
        )

        return await self._send_email(
            to_email=email,
            to_name=full_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_account_activated_email(
        self,
        email: str,
        full_name: str,
    ) -> bool:
        """Envia email de confirmação de ativação de conta"""

        subject = "Conta ativada com sucesso!"

        html_content = self._create_account_activated_html(full_name)
        text_content = self._create_account_activated_text(full_name)

        return await self._send_email(
            to_email=email,
            to_name=full_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_welcome_email(
        self,
        email: str,
        full_name: str,
        municipality_name: Optional[str] = None,
    ) -> bool:
        """Envia email de boas-vindas após ativação"""

        municipality_text = f" da {municipality_name}" if municipality_name else ""
        subject = f"Bem-vindo ao Sistema de Documentos Inteligentes{municipality_text}!"

        html_content = self._create_welcome_html(
            full_name=full_name,
            municipality_name=municipality_name,
        )

        text_content = self._create_welcome_text(
            full_name=full_name,
            municipality_name=municipality_name,
        )

        return await self._send_email(
            to_email=email,
            to_name=full_name,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def _send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        """Envia email via SMTP"""

        try:
            # Cria mensagem
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self._from_name} <{self._from_email}>"
            msg["To"] = f"{to_name} <{to_email}>"

            # Adiciona conteúdo texto e HTML
            text_part = MIMEText(text_content, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")

            msg.attach(text_part)
            msg.attach(html_part)

            # Conecta ao servidor SMTP
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                if self._smtp_use_tls:
                    server.starttls()

                server.login(self._smtp_username, self._smtp_password)
                server.send_message(msg)

            logger.info(
                "email_sent_successfully",
                extra={
                    "to_email": to_email,
                    "subject": subject,
                    "smtp_host": self._smtp_host,
                },
            )

            return True

        except Exception as e:
            logger.error(
                "email_send_failed",
                extra={
                    "to_email": to_email,
                    "subject": subject,
                    "error": str(e),
                    "smtp_host": self._smtp_host,
                },
            )
            raise EmailDeliveryError(f"Falha ao enviar email: {str(e)}")

    def _create_invitation_html(
        self,
        full_name: str,
        invited_by_name: str,
        activation_url: str,
        municipality_name: Optional[str] = None,
    ) -> str:
        """Cria conteúdo HTML do email de convite"""

        municipality_text = f" da {municipality_name}" if municipality_name else ""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Convite para o Sistema</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f8f9fa; }}
                .button {{
                    display: inline-block;
                    background: #3498db;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Sistema de Documentos Inteligentes{municipality_text}</h1>
                </div>

                <div class="content">
                    <h2>Olá, {full_name}!</h2>

                    <p>Você foi convidado por <strong>{invited_by_name}</strong> para acessar o \\
Sistema de Documentos Inteligentes{municipality_text}.</p>
                    <p>Este sistema permite que você:</p>
                    <ul>
                        <li>Faça perguntas sobre documentos oficiais</li>
                        <li>Obtenha respostas inteligentes baseadas em IA</li>
                        <li>Acesse informações de forma rápida e eficiente</li>
                    </ul>

                    <p>Para ativar sua conta, clique no botão abaixo:</p>

                    <div style="text-align: center;">
                        <a href="{activation_url}" class="button">Ativar Minha Conta</a>
                    </div>

                    <p><small>Se o botão não funcionar, copie e cole este link no seu navegador:<br>
                    <a href="{activation_url}">{activation_url}</a></small></p>

                    <p><strong>Importante:</strong> Este convite expira em 7 dias.</p>
                </div>

                <div class="footer">
                    <p>Este é um email automático. Não responda a esta mensagem.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_invitation_text(
        self,
        full_name: str,
        invited_by_name: str,
        activation_url: str,
        municipality_name: Optional[str] = None,
    ) -> str:
        """Cria conteúdo texto do email de convite"""

        municipality_text = f" da {municipality_name}" if municipality_name else ""

        return f"""
Sistema de Documentos Inteligentes{municipality_text}

Olá, {full_name}!

Você foi convidado por {invited_by_name} para acessar o Sistema de Documentos Inteligentes{municipality_text}.

Este sistema permite que você:
- Faça perguntas sobre documentos oficiais
- Obtenha respostas inteligentes baseadas em IA
- Acesse informações de forma rápida e eficiente

Para ativar sua conta, acesse o link abaixo:
{activation_url}

IMPORTANTE: Este convite expira em 7 dias.

---
Este é um email automático. Não responda a esta mensagem.
        """

    def _create_password_reset_html(self, full_name: str, reset_url: str) -> str:
        """Cria conteúdo HTML do email de redefinição de senha"""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Redefinição de Senha</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #e74c3c; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f8f9fa; }}
                .button {{
                    display: inline-block;
                    background: #e74c3c;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Redefinição de Senha</h1>
                </div>

                <div class="content">
                    <h2>Olá, {full_name}!</h2>

                    <p>Recebemos uma solicitação para redefinir a senha da sua conta.</p>

                    <p>Se você fez esta solicitação, clique no botão abaixo para criar uma nova senha:</p>

                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">Redefinir Senha</a>
                    </div>

                    <p><small>Se o botão não funcionar, copie e cole este link no seu navegador:<br>
                    <a href="{reset_url}">{reset_url}</a></small></p>

                    <p><strong>Se você não solicitou esta redefinição, ignore este email.</strong> Sua senha permanecerá inalterada.</p>

                    <p><small>Este link expira em 1 hora por segurança.</small></p>
                </div>

                <div class="footer">
                    <p>Este é um email automático. Não responda a esta mensagem.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_password_reset_text(self, full_name: str, reset_url: str) -> str:
        """Cria conteúdo texto do email de redefinição de senha"""

        return f"""
Redefinição de Senha

Olá, {full_name}!

Recebemos uma solicitação para redefinir a senha da sua conta.

Se você fez esta solicitação, acesse o link abaixo para criar uma nova senha:
{reset_url}

Se você não solicitou esta redefinição, ignore este email. Sua senha permanecerá inalterada.

IMPORTANTE: Este link expira em 1 hora por segurança.

---
Este é um email automático. Não responda a esta mensagem.
        """

    def _create_account_activated_html(self, full_name: str) -> str:
        """Cria conteúdo HTML do email de confirmação de ativação"""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Conta Ativada</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #27ae60; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f8f9fa; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Conta Ativada com Sucesso!</h1>
                </div>

                <div class="content">
                    <h2>Parabéns, {full_name}!</h2>

                    <p>Sua conta foi ativada com sucesso no Sistema de Documentos Inteligentes.</p>

                    <p>Agora você pode:</p>
                    <ul>
                        <li>Fazer login no sistema</li>
                        <li>Fazer perguntas sobre documentos</li>
                        <li>Acessar todas as funcionalidades disponíveis</li>
                    </ul>

                    <p>Acesse o sistema em: <a href="{self._base_url}">{self._base_url}</a></p>
                </div>

                <div class="footer">
                    <p>Este é um email automático. Não responda a esta mensagem.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_account_activated_text(self, full_name: str) -> str:
        """Cria conteúdo texto do email de confirmação de ativação"""

        return f"""
Conta Ativada com Sucesso!

Parabéns, {full_name}!

Sua conta foi ativada com sucesso no Sistema de Documentos Inteligentes.

Agora você pode:
- Fazer login no sistema
- Fazer perguntas sobre documentos
- Acessar todas as funcionalidades disponíveis

Acesse o sistema em: {self._base_url}

---
Este é um email automático. Não responda a esta mensagem.
        """

    def _create_welcome_html(
        self, full_name: str, municipality_name: Optional[str] = None
    ) -> str:
        """Cria conteúdo HTML do email de boas-vindas"""

        municipality_text = f" da {municipality_name}" if municipality_name else ""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Bem-vindo</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #3498db; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f8f9fa; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Bem-vindo ao Sistema!</h1>
                </div>

                <div class="content">
                    <h2>Olá, {full_name}!</h2>

                    <p>Seja bem-vindo ao Sistema de Documentos Inteligentes{municipality_text}!</p>

                    <p>Você agora tem acesso a uma ferramenta poderosa que utiliza inteligência artificial \\
para ajudar você a encontrar informações em documentos oficiais de forma rápida e precisa.</p>
                    <h3>Como usar o sistema:</h3>
                    <ol>
                        <li>Faça login com seu email e senha</li>
                        <li>Digite sua pergunta na caixa de chat</li>
                        <li>Receba respostas baseadas nos documentos oficiais</li>
                        <li>Use as citações para verificar as fontes</li>
                    </ol>

                    <p>Se tiver dúvidas, entre em contato com o administrador do sistema.</p>

                    <p>Acesse o sistema: <a href="{self._base_url}">{self._base_url}</a></p>
                </div>

                <div class="footer">
                    <p>Este é um email automático. Não responda a esta mensagem.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _create_welcome_text(
        self, full_name: str, municipality_name: Optional[str] = None
    ) -> str:
        """Cria conteúdo texto do email de boas-vindas"""

        municipality_text = f" da {municipality_name}" if municipality_name else ""

        return f"""
Bem-vindo ao Sistema de Documentos Inteligentes{municipality_text}!

Olá, {full_name}!

Seja bem-vindo ao Sistema de Documentos Inteligentes{municipality_text}!

Você agora tem acesso a uma ferramenta poderosa que utiliza inteligência artificial \\
para ajudar você a encontrar informações em documentos oficiais de forma rápida e precisa.

Como usar o sistema:
1. Faça login com seu email e senha
2. Digite sua pergunta na caixa de chat
3. Receba respostas baseadas nos documentos oficiais
4. Use as citações para verificar as fontes

Se tiver dúvidas, entre em contato com o administrador do sistema.

Acesse o sistema: {self._base_url}

---
Este é um email automático. Não responda a esta mensagem.
        """
