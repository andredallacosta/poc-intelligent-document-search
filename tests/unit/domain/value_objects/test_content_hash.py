import pytest

from domain.exceptions.business_exceptions import BusinessRuleViolationError
from domain.value_objects.content_hash import ContentHash


class TestContentHash:
    def test_create_valid_sha256_hash(self):
        hash_value = "a" * 64
        content_hash = ContentHash(algorithm="sha256", value=hash_value)
        assert content_hash.algorithm == "sha256"
        assert content_hash.value == hash_value

    def test_create_valid_md5_hash(self):
        hash_value = "b" * 32
        content_hash = ContentHash(algorithm="md5", value=hash_value)
        assert content_hash.algorithm == "md5"
        assert content_hash.value == hash_value

    def test_invalid_algorithm(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Algoritmo deve ser 'sha256' ou 'md5'"
        ):
            ContentHash(algorithm="invalid", value="a" * 64)

    def test_empty_algorithm(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Algoritmo deve ser 'sha256' ou 'md5'"
        ):
            ContentHash(algorithm="", value="a" * 64)

    def test_none_algorithm(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Algoritmo deve ser 'sha256' ou 'md5'"
        ):
            ContentHash(algorithm=None, value="a" * 64)

    def test_empty_hash_value(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Hash value é obrigatório"
        ):
            ContentHash(algorithm="sha256", value="")

    def test_whitespace_only_hash_value(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Hash value é obrigatório"
        ):
            ContentHash(algorithm="sha256", value="   ")

    def test_none_hash_value(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Hash value é obrigatório"
        ):
            ContentHash(algorithm="sha256", value=None)

    def test_sha256_wrong_length_short(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Hash SHA256 deve ter 64 caracteres"
        ):
            ContentHash(algorithm="sha256", value="a" * 63)

    def test_sha256_wrong_length_long(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Hash SHA256 deve ter 64 caracteres"
        ):
            ContentHash(algorithm="sha256", value="a" * 65)

    def test_md5_wrong_length_short(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Hash MD5 deve ter 32 caracteres"
        ):
            ContentHash(algorithm="md5", value="b" * 31)

    def test_md5_wrong_length_long(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Hash MD5 deve ter 32 caracteres"
        ):
            ContentHash(algorithm="md5", value="b" * 33)

    def test_non_hexadecimal_characters(self):
        invalid_hash = "g" * 64
        with pytest.raises(
            BusinessRuleViolationError,
            match="Hash deve conter apenas caracteres hexadecimais",
        ):
            ContentHash(algorithm="sha256", value=invalid_hash)

    def test_mixed_case_hexadecimal_valid(self):
        hash_value = "AbCdEf" + "0" * 58
        content_hash = ContentHash(algorithm="sha256", value=hash_value)
        assert content_hash.value == hash_value

    def test_from_text_sha256_default(self):
        text = "Hello World"
        content_hash = ContentHash.from_text(text)
        assert content_hash.algorithm == "sha256"
        assert len(content_hash.value) == 64
        assert content_hash.value.isalnum()

    def test_from_text_md5(self):
        text = "Hello World"
        content_hash = ContentHash.from_text(text, algorithm="md5")
        assert content_hash.algorithm == "md5"
        assert len(content_hash.value) == 32
        assert content_hash.value.isalnum()

    def test_from_text_unsupported_algorithm(self):
        with pytest.raises(
            BusinessRuleViolationError, match="Algoritmo não suportado: sha1"
        ):
            ContentHash.from_text("Hello World", algorithm="sha1")

    def test_from_text_consistent_hash(self):
        text = "Hello World"
        hash1 = ContentHash.from_text(text)
        hash2 = ContentHash.from_text(text)
        assert hash1.value == hash2.value

    def test_normalize_text_whitespace(self):
        text1 = "Hello    World"
        text2 = "Hello World"
        hash1 = ContentHash.from_text(text1)
        hash2 = ContentHash.from_text(text2)
        assert hash1.value == hash2.value

    def test_normalize_text_case_insensitive(self):
        text1 = "Hello World"
        text2 = "hello world"
        hash1 = ContentHash.from_text(text1)
        hash2 = ContentHash.from_text(text2)
        assert hash1.value == hash2.value

    def test_normalize_text_punctuation_removed(self):
        text1 = "Hello, World!"
        text2 = "Hello World"
        hash1 = ContentHash.from_text(text1)
        hash2 = ContentHash.from_text(text2)
        assert hash1.value == hash2.value

    def test_normalize_text_leading_trailing_spaces(self):
        text1 = "  Hello World  "
        text2 = "Hello World"
        hash1 = ContentHash.from_text(text1)
        hash2 = ContentHash.from_text(text2)
        assert hash1.value == hash2.value

    def test_str_representation(self):
        content_hash = ContentHash(algorithm="sha256", value="a" * 64)
        expected = f"sha256:{'a' * 64}"
        assert str(content_hash) == expected

    def test_equality_same_values(self):
        hash1 = ContentHash(algorithm="sha256", value="a" * 64)
        hash2 = ContentHash(algorithm="sha256", value="a" * 64)
        assert hash1 == hash2

    def test_equality_different_algorithms(self):
        hash1 = ContentHash(algorithm="sha256", value="a" * 64)
        hash2 = ContentHash(algorithm="md5", value="a" * 32)
        assert hash1 != hash2

    def test_equality_different_values(self):
        hash1 = ContentHash(algorithm="sha256", value="a" * 64)
        hash2 = ContentHash(algorithm="sha256", value="b" * 64)
        assert hash1 != hash2

    def test_equality_with_non_content_hash(self):
        content_hash = ContentHash(algorithm="sha256", value="a" * 64)
        assert content_hash != "not a content hash"
        assert content_hash is not None
        assert content_hash != 123

    def test_frozen_dataclass(self):
        content_hash = ContentHash(algorithm="sha256", value="a" * 64)
        with pytest.raises(AttributeError):
            content_hash.algorithm = "md5"
        with pytest.raises(AttributeError):
            content_hash.value = "b" * 64
