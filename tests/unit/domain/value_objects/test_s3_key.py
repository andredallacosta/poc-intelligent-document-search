import pytest

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.s3_key import S3Key


class TestS3Key:
    def test_create_valid_s3_key(self):
        s3_key = S3Key(bucket="test-bucket", key="test/file.pdf", region="us-east-1")
        assert s3_key.bucket == "test-bucket"
        assert s3_key.key == "test/file.pdf"
        assert s3_key.region == "us-east-1"

    def test_create_s3_key_without_region(self):
        s3_key = S3Key(bucket="test-bucket", key="test/file.pdf")
        assert s3_key.bucket == "test-bucket"
        assert s3_key.key == "test/file.pdf"
        assert s3_key.region is None

    def test_empty_bucket(self):
        with pytest.raises(BusinessRuleViolationError, match="Bucket S3 é obrigatório"):
            S3Key(bucket="", key="test/file.pdf")

    def test_whitespace_only_bucket(self):
        with pytest.raises(BusinessRuleViolationError, match="Bucket S3 é obrigatório"):
            S3Key(bucket="   ", key="test/file.pdf")

    def test_none_bucket(self):
        with pytest.raises(BusinessRuleViolationError, match="Bucket S3 é obrigatório"):
            S3Key(bucket=None, key="test/file.pdf")

    def test_empty_key(self):
        with pytest.raises(BusinessRuleViolationError, match="Key S3 é obrigatória"):
            S3Key(bucket="test-bucket", key="")

    def test_whitespace_only_key(self):
        with pytest.raises(BusinessRuleViolationError, match="Key S3 é obrigatória"):
            S3Key(bucket="test-bucket", key="   ")

    def test_none_key(self):
        with pytest.raises(BusinessRuleViolationError, match="Key S3 é obrigatória"):
            S3Key(bucket="test-bucket", key=None)

    def test_bucket_too_long(self):
        long_bucket = "a" * 64
        with pytest.raises(
            BusinessRuleViolationError,
            match="Bucket S3 não pode ter mais de 63 caracteres",
        ):
            S3Key(bucket=long_bucket, key="test/file.pdf")

    def test_bucket_max_length_valid(self):
        max_length_bucket = "a" * 63
        s3_key = S3Key(bucket=max_length_bucket, key="test/file.pdf")
        assert s3_key.bucket == max_length_bucket

    def test_key_too_long(self):
        long_key = "a" * 1025
        with pytest.raises(
            BusinessRuleViolationError,
            match="Key S3 não pode ter mais de 1024 caracteres",
        ):
            S3Key(bucket="test-bucket", key=long_key)

    def test_key_max_length_valid(self):
        max_length_key = "a" * 1024
        s3_key = S3Key(bucket="test-bucket", key=max_length_key)
        assert s3_key.key == max_length_key

    def test_create_temp_key(self):
        document_id = "doc-123"
        filename = "test document.pdf"
        bucket = "my-bucket"
        region = "us-west-2"
        s3_key = S3Key.create_temp_key(document_id, filename, bucket, region)
        assert s3_key.bucket == bucket
        assert s3_key.key == "temp/doc-123/test_document.pdf"
        assert s3_key.region == region

    def test_create_temp_key_default_region(self):
        document_id = "doc-456"
        filename = "report.pdf"
        bucket = "my-bucket"
        s3_key = S3Key.create_temp_key(document_id, filename, bucket)
        assert s3_key.bucket == bucket
        assert s3_key.key == "temp/doc-456/report.pdf"
        assert s3_key.region == "us-east-1"

    def test_create_temp_key_with_slashes_in_filename(self):
        document_id = "doc-789"
        filename = "folder/subfolder/file.pdf"
        bucket = "my-bucket"
        s3_key = S3Key.create_temp_key(document_id, filename, bucket)
        assert s3_key.key == "temp/doc-789/folder_subfolder_file.pdf"

    def test_create_temp_key_with_spaces_and_slashes(self):
        document_id = "doc-999"
        filename = "my folder/my file.pdf"
        bucket = "my-bucket"
        s3_key = S3Key.create_temp_key(document_id, filename, bucket)
        assert s3_key.key == "temp/doc-999/my_folder_my_file.pdf"

    def test_full_path_property(self):
        s3_key = S3Key(bucket="test-bucket", key="test/file.pdf")
        assert s3_key.full_path == "s3://test-bucket/test/file.pdf"

    def test_url_property_us_east_1(self):
        s3_key = S3Key(bucket="test-bucket", key="test/file.pdf", region="us-east-1")
        assert s3_key.url == "https://test-bucket.s3.amazonaws.com/test/file.pdf"

    def test_url_property_other_region(self):
        s3_key = S3Key(bucket="test-bucket", key="test/file.pdf", region="us-west-2")
        assert (
            s3_key.url == "https://test-bucket.s3.us-west-2.amazonaws.com/test/file.pdf"
        )

    def test_url_property_no_region(self):
        s3_key = S3Key(bucket="test-bucket", key="test/file.pdf")
        assert s3_key.url == "https://test-bucket.s3.amazonaws.com/test/file.pdf"

    def test_url_property_none_region(self):
        s3_key = S3Key(bucket="test-bucket", key="test/file.pdf", region=None)
        assert s3_key.url == "https://test-bucket.s3.amazonaws.com/test/file.pdf"

    def test_frozen_dataclass(self):
        s3_key = S3Key(bucket="test-bucket", key="test/file.pdf")
        with pytest.raises(AttributeError):
            s3_key.bucket = "new-bucket"
        with pytest.raises(AttributeError):
            s3_key.key = "new/key.pdf"
        with pytest.raises(AttributeError):
            s3_key.region = "new-region"
