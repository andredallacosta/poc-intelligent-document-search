#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError


def setup_localstack_s3():
    """Configura LocalStack S3 usando boto3 diretamente"""

    print("🚀 Configurando LocalStack S3 com boto3...")

    # Configurações
    endpoint_url = "http://localhost:4566"
    bucket_name = "documents-dev"
    region = "us-east-1"

    # Cliente S3
    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name=region,
    )

    try:
        # 1. Criar bucket
        print(f"📦 Criando bucket S3: {bucket_name}")

        try:
            s3_client.create_bucket(Bucket=bucket_name)
            print("✅ Bucket criado com sucesso!")
        except ClientError as e:
            if e.response["Error"]["Code"] == "BucketAlreadyOwnedByYou":
                print("✅ Bucket já existe!")
            else:
                raise

        # 2. Configurar CORS
        print("🔧 Configurando CORS...")

        cors_config = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
                    "AllowedOrigins": ["*"],
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3600,
                }
            ]
        }

        s3_client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)
        print("✅ CORS configurado!")

        # 3. Configurar lifecycle
        print("🗑️ Configurando lifecycle para limpeza...")

        lifecycle_config = {
            "Rules": [
                {
                    "ID": "TempFilesCleanup",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "temp/"},
                    "Expiration": {"Days": 7},
                }
            ]
        }

        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name, LifecycleConfiguration=lifecycle_config
        )
        print("✅ Lifecycle configurado!")

        # 4. Verificar configuração
        print("✅ Verificando configuração...")

        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]

        if bucket_name in buckets:
            print(f"✅ Bucket {bucket_name} encontrado!")

        print("\n🎉 LocalStack S3 configurado com sucesso!")
        print("")
        print("📋 Configurações:")
        print(f"   Endpoint: {endpoint_url}")
        print(f"   Bucket: {bucket_name}")
        print(f"   Region: {region}")
        print("")
        print("🔧 Para usar no projeto, configure no .env:")
        print("   S3_ENDPOINT_URL=http://localhost:4566")
        print("   AWS_ACCESS_KEY=test")
        print("   AWS_SECRET_KEY=test")
        print("   S3_BUCKET=documents-dev")

        return True

    except Exception as e:
        print(f"❌ Erro ao configurar LocalStack: {e}")
        return False


if __name__ == "__main__":
    success = setup_localstack_s3()
    exit(0 if success else 1)
