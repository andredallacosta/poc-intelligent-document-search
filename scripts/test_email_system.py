#!/usr/bin/env python3
"""
Script para testar o sistema de envio de emails

Usage:
    python scripts/test_email_system.py --email test@example.com --type invitation
    python scripts/test_email_system.py --email test@example.com --type welcome
    python scripts/test_email_system.py --email test@example.com --type reset
    python scripts/test_email_system.py --email test@example.com --type activated
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.config.settings import settings
from infrastructure.external.smtp_email_service import SMTPEmailService
from domain.exceptions.auth_exceptions import EmailDeliveryError


async def test_invitation_email(email_service: SMTPEmailService, email: str):
    """Testa email de convite"""
    print(f"🔄 Enviando email de convite para {email}...")
    
    try:
        result = await email_service.send_invitation_email(
            email=email,
            full_name="Usuário de Teste",
            invitation_token="test-token-123456",
            invited_by_name="Administrador do Sistema",
            municipality_name="Prefeitura de Teste",
        )
        
        if result:
            print("✅ Email de convite enviado com sucesso!")
        else:
            print("❌ Falha no envio do email de convite")
            
    except EmailDeliveryError as e:
        print(f"❌ Erro no envio: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


async def test_welcome_email(email_service: SMTPEmailService, email: str):
    """Testa email de boas-vindas"""
    print(f"🔄 Enviando email de boas-vindas para {email}...")
    
    try:
        result = await email_service.send_welcome_email(
            email=email,
            full_name="Usuário de Teste",
            municipality_name="Prefeitura de Teste",
        )
        
        if result:
            print("✅ Email de boas-vindas enviado com sucesso!")
        else:
            print("❌ Falha no envio do email de boas-vindas")
            
    except EmailDeliveryError as e:
        print(f"❌ Erro no envio: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


async def test_password_reset_email(email_service: SMTPEmailService, email: str):
    """Testa email de redefinição de senha"""
    print(f"🔄 Enviando email de redefinição de senha para {email}...")
    
    try:
        result = await email_service.send_password_reset_email(
            email=email,
            full_name="Usuário de Teste",
            reset_token="reset-token-123456",
        )
        
        if result:
            print("✅ Email de redefinição de senha enviado com sucesso!")
        else:
            print("❌ Falha no envio do email de redefinição de senha")
            
    except EmailDeliveryError as e:
        print(f"❌ Erro no envio: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


async def test_account_activated_email(email_service: SMTPEmailService, email: str):
    """Testa email de confirmação de ativação"""
    print(f"🔄 Enviando email de confirmação de ativação para {email}...")
    
    try:
        result = await email_service.send_account_activated_email(
            email=email,
            full_name="Usuário de Teste",
        )
        
        if result:
            print("✅ Email de confirmação de ativação enviado com sucesso!")
        else:
            print("❌ Falha no envio do email de confirmação de ativação")
            
    except EmailDeliveryError as e:
        print(f"❌ Erro no envio: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


async def test_all_emails(email_service: SMTPEmailService, email: str):
    """Testa todos os tipos de email"""
    print(f"🧪 Testando todos os tipos de email para {email}...\n")
    
    await test_invitation_email(email_service, email)
    print()
    
    await test_welcome_email(email_service, email)
    print()
    
    await test_password_reset_email(email_service, email)
    print()
    
    await test_account_activated_email(email_service, email)
    print()
    
    print("🎉 Teste completo finalizado!")


def validate_smtp_configuration():
    """Valida configuração SMTP"""
    print("🔍 Validando configuração SMTP...")
    
    required_settings = [
        ("SMTP_HOST", settings.smtp_host),
        ("SMTP_PORT", settings.smtp_port),
        ("SMTP_USERNAME", settings.smtp_username),
        ("SMTP_PASSWORD", settings.smtp_password),
    ]
    
    missing_settings = []
    
    for setting_name, setting_value in required_settings:
        if not setting_value:
            missing_settings.append(setting_name)
        else:
            print(f"✅ {setting_name}: {setting_value if setting_name != 'SMTP_PASSWORD' else '***'}")
    
    if missing_settings:
        print(f"\n❌ Configurações SMTP faltando: {', '.join(missing_settings)}")
        print("\nAdicione as seguintes variáveis ao seu .env:")
        for setting in missing_settings:
            if setting == "SMTP_HOST":
                print("SMTP_HOST=smtp.gmail.com  # Para Gmail")
            elif setting == "SMTP_PORT":
                print("SMTP_PORT=587  # Para TLS")
            elif setting == "SMTP_USERNAME":
                print("SMTP_USERNAME=seu_email@gmail.com")
            elif setting == "SMTP_PASSWORD":
                print("SMTP_PASSWORD=sua_senha_de_app  # Use App Password para Gmail")
        
        print("\nPara Gmail:")
        print("1. Ative a verificação em duas etapas")
        print("2. Gere uma senha de app em: https://myaccount.google.com/apppasswords")
        print("3. Use a senha de app no SMTP_PASSWORD")
        
        return False
    
    print(f"✅ SMTP_USE_TLS: {settings.smtp_use_tls}")
    print(f"✅ SMTP_FROM_EMAIL: {settings.smtp_from_email or settings.smtp_username}")
    print(f"✅ SMTP_FROM_NAME: {settings.smtp_from_name}")
    print(f"✅ BASE_URL: {settings.base_url}")
    
    return True


async def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Testa sistema de envio de emails")
    parser.add_argument("--email", required=True, help="Email de destino para teste")
    parser.add_argument(
        "--type",
        choices=["invitation", "welcome", "reset", "activated", "all"],
        default="all",
        help="Tipo de email para testar",
    )
    
    args = parser.parse_args()
    
    print("📧 Sistema de Teste de Emails")
    print("=" * 50)
    
    # Valida configuração
    if not validate_smtp_configuration():
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # Cria serviço de email
    email_service = SMTPEmailService(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password,
        smtp_use_tls=settings.smtp_use_tls,
        from_email=settings.smtp_from_email,
        from_name=settings.smtp_from_name,
        base_url=settings.base_url,
    )
    
    # Executa testes
    if args.type == "invitation":
        await test_invitation_email(email_service, args.email)
    elif args.type == "welcome":
        await test_welcome_email(email_service, args.email)
    elif args.type == "reset":
        await test_password_reset_email(email_service, args.email)
    elif args.type == "activated":
        await test_account_activated_email(email_service, args.email)
    elif args.type == "all":
        await test_all_emails(email_service, args.email)


if __name__ == "__main__":
    asyncio.run(main())
