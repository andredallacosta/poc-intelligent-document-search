from abc import ABC, abstractmethod
from typing import Optional


class EmailService(ABC):
    """Interface para serviço de envio de emails"""

    @abstractmethod
    async def send_invitation_email(
        self,
        email: str,
        full_name: str,
        invitation_token: str,
        invited_by_name: str,
        municipality_name: Optional[str] = None,
    ) -> bool:
        """
        Envia email de convite para ativação de conta

        Args:
            email: Email do destinatário
            full_name: Nome completo do usuário convidado
            invitation_token: Token para ativação da conta
            invited_by_name: Nome de quem enviou o convite
            municipality_name: Nome da prefeitura (opcional)

        Returns:
            bool: True se enviado com sucesso

        Raises:
            EmailDeliveryError: Se falhar ao enviar
        """
        pass

    @abstractmethod
    async def send_password_reset_email(
        self,
        email: str,
        full_name: str,
        reset_token: str,
    ) -> bool:
        """
        Envia email de redefinição de senha

        Args:
            email: Email do destinatário
            full_name: Nome completo do usuário
            reset_token: Token para redefinir senha

        Returns:
            bool: True se enviado com sucesso

        Raises:
            EmailDeliveryError: Se falhar ao enviar
        """
        pass

    @abstractmethod
    async def send_account_activated_email(
        self,
        email: str,
        full_name: str,
    ) -> bool:
        """
        Envia email de confirmação de ativação de conta

        Args:
            email: Email do destinatário
            full_name: Nome completo do usuário

        Returns:
            bool: True se enviado com sucesso

        Raises:
            EmailDeliveryError: Se falhar ao enviar
        """
        pass

    @abstractmethod
    async def send_welcome_email(
        self,
        email: str,
        full_name: str,
        municipality_name: Optional[str] = None,
    ) -> bool:
        """
        Envia email de boas-vindas após ativação

        Args:
            email: Email do destinatário
            full_name: Nome completo do usuário
            municipality_name: Nome da prefeitura (opcional)

        Returns:
            bool: True se enviado com sucesso

        Raises:
            EmailDeliveryError: Se falhar ao enviar
        """
        pass
