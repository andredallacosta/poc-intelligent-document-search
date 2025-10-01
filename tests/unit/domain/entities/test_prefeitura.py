import pytest
from datetime import datetime
from domain.entities.prefeitura import Prefeitura
from domain.value_objects.prefeitura_id import PrefeituraId
from domain.exceptions.business_exceptions import BusinessRuleViolationError

class TestPrefeitura:
    
    def test_create_valid_prefeitura(self):
        prefeitura_id = PrefeituraId.generate()
        prefeitura = Prefeitura(
            id=prefeitura_id,
            nome="Prefeitura de São Paulo",
            quota_tokens=10000
        )
        
        assert prefeitura.id == prefeitura_id
        assert prefeitura.nome == "Prefeitura de São Paulo"
        assert prefeitura.quota_tokens == 10000
        assert prefeitura.tokens_consumidos == 0
        assert prefeitura.ativo is True
        assert isinstance(prefeitura.criado_em, datetime)
        assert isinstance(prefeitura.atualizado_em, datetime)
    
    def test_create_prefeitura_factory_method(self):
        prefeitura = Prefeitura.create("Prefeitura do Rio de Janeiro", quota_tokens=5000)
        
        assert prefeitura.nome == "Prefeitura do Rio de Janeiro"
        assert prefeitura.quota_tokens == 5000
        assert prefeitura.tokens_consumidos == 0
        assert prefeitura.ativo is True
        assert isinstance(prefeitura.id, PrefeituraId)
    
    def test_create_prefeitura_factory_method_defaults(self):
        prefeitura = Prefeitura.create("Prefeitura de Brasília")
        
        assert prefeitura.nome == "Prefeitura de Brasília"
        assert prefeitura.quota_tokens == 10000
        assert prefeitura.ativo is True
    
    def test_empty_nome_raises_error(self):
        prefeitura_id = PrefeituraId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="Nome da prefeitura é obrigatório"):
            Prefeitura(id=prefeitura_id, nome="", quota_tokens=10000)
    
    def test_whitespace_only_nome_raises_error(self):
        prefeitura_id = PrefeituraId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="Nome da prefeitura é obrigatório"):
            Prefeitura(id=prefeitura_id, nome="   ", quota_tokens=10000)
    
    def test_none_nome_raises_error(self):
        prefeitura_id = PrefeituraId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="Nome da prefeitura é obrigatório"):
            Prefeitura(id=prefeitura_id, nome=None, quota_tokens=10000)
    
    def test_nome_too_long_raises_error(self):
        prefeitura_id = PrefeituraId.generate()
        long_nome = "a" * 256
        
        with pytest.raises(BusinessRuleViolationError, match="Nome da prefeitura não pode ter mais de 255 caracteres"):
            Prefeitura(id=prefeitura_id, nome=long_nome, quota_tokens=10000)
    
    def test_nome_max_length_valid(self):
        prefeitura_id = PrefeituraId.generate()
        max_nome = "a" * 255
        
        prefeitura = Prefeitura(id=prefeitura_id, nome=max_nome, quota_tokens=10000)
        assert prefeitura.nome == max_nome
    
    def test_negative_quota_tokens_raises_error(self):
        prefeitura_id = PrefeituraId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="Quota de tokens não pode ser negativa"):
            Prefeitura(id=prefeitura_id, nome="Test", quota_tokens=-1)
    
    def test_negative_tokens_consumidos_raises_error(self):
        prefeitura_id = PrefeituraId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="Tokens consumidos não pode ser negativo"):
            Prefeitura(id=prefeitura_id, nome="Test", quota_tokens=10000, tokens_consumidos=-1)
    
    def test_tokens_consumidos_exceeds_quota_raises_error(self):
        prefeitura_id = PrefeituraId.generate()
        
        with pytest.raises(BusinessRuleViolationError, match="Tokens consumidos não pode exceder a quota"):
            Prefeitura(id=prefeitura_id, nome="Test", quota_tokens=1000, tokens_consumidos=1001)
    
    def test_tokens_consumidos_equals_quota_valid(self):
        prefeitura_id = PrefeituraId.generate()
        
        prefeitura = Prefeitura(id=prefeitura_id, nome="Test", quota_tokens=1000, tokens_consumidos=1000)
        assert prefeitura.tokens_consumidos == prefeitura.quota_tokens
    
    def test_consumir_tokens_success(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        initial_consumed = prefeitura.tokens_consumidos
        initial_updated = prefeitura.atualizado_em
        
        prefeitura.consumir_tokens(100)
        
        assert prefeitura.tokens_consumidos == initial_consumed + 100
        assert prefeitura.atualizado_em > initial_updated
    
    def test_consumir_tokens_exceeds_quota_raises_error(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 900
        
        with pytest.raises(BusinessRuleViolationError, match="Quota de tokens excedida"):
            prefeitura.consumir_tokens(200)
    
    def test_consumir_tokens_exact_remaining_success(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 900
        
        prefeitura.consumir_tokens(100)
        assert prefeitura.tokens_consumidos == 1000
    
    def test_consumir_tokens_negative_raises_error(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        
        with pytest.raises(BusinessRuleViolationError, match="Quantidade de tokens deve ser positiva"):
            prefeitura.consumir_tokens(-10)
    
    def test_consumir_tokens_zero_raises_error(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        
        with pytest.raises(BusinessRuleViolationError, match="Quantidade de tokens deve ser positiva"):
            prefeitura.consumir_tokens(0)
    
    def test_pode_consumir_true(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 500
        
        assert prefeitura.pode_consumir(100) is True
    
    def test_pode_consumir_false(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 900
        
        assert prefeitura.pode_consumir(200) is False
    
    def test_pode_consumir_exact_amount(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 900
        
        assert prefeitura.pode_consumir(100) is True
    
    def test_tokens_restantes_property(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 300
        
        assert prefeitura.tokens_restantes == 700
    
    def test_tokens_restantes_zero(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 1000
        
        assert prefeitura.tokens_restantes == 0
    
    def test_desativar_prefeitura(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        initial_updated = prefeitura.atualizado_em
        
        prefeitura.desativar()
        
        assert prefeitura.ativo is False
        assert prefeitura.atualizado_em > initial_updated
    
    def test_ativar_prefeitura(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000, ativo=False)
        initial_updated = prefeitura.atualizado_em
        
        prefeitura.ativar()
        
        assert prefeitura.ativo is True
        assert prefeitura.atualizado_em > initial_updated
    
    def test_aumentar_quota_success(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 500
        initial_updated = prefeitura.atualizado_em
        
        prefeitura.aumentar_quota(2000)
        
        assert prefeitura.quota_tokens == 2000
        assert prefeitura.atualizado_em > initial_updated
    
    def test_aumentar_quota_below_consumed_raises_error(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 800
        
        with pytest.raises(BusinessRuleViolationError, match="Nova quota .* não pode ser menor que tokens já consumidos"):
            prefeitura.aumentar_quota(700)
    
    def test_aumentar_quota_equals_consumed_success(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 800
        
        prefeitura.aumentar_quota(800)
        assert prefeitura.quota_tokens == 800
    
    def test_resetar_consumo(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 500
        initial_updated = prefeitura.atualizado_em
        
        prefeitura.resetar_consumo()
        
        assert prefeitura.tokens_consumidos == 0
        assert prefeitura.atualizado_em > initial_updated
    
    def test_percentual_consumo_property(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 250
        
        assert prefeitura.percentual_consumo == 25.0
    
    def test_percentual_consumo_zero_quota(self):
        prefeitura_id = PrefeituraId.generate()
        prefeitura = Prefeitura(id=prefeitura_id, nome="Test", quota_tokens=0)
        
        assert prefeitura.percentual_consumo == 0.0
    
    def test_quota_esgotada_property_true(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 1000
        
        assert prefeitura.quota_esgotada is True
    
    def test_quota_esgotada_property_false(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 500
        
        assert prefeitura.quota_esgotada is False
    
    def test_quota_critica_property_true(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 950
        
        assert prefeitura.quota_critica is True
    
    def test_quota_critica_property_false(self):
        prefeitura = Prefeitura.create("Test", quota_tokens=1000)
        prefeitura.tokens_consumidos = 800
        
        assert prefeitura.quota_critica is False
