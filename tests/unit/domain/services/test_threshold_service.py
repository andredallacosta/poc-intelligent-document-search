from unittest.mock import Mock

import pytest

from domain.services.threshold_service import QueryType, ThresholdService


class TestThresholdService:
    @pytest.fixture
    def mock_settings(self):
        settings = Mock()
        settings.similarity_threshold_specific = 0.85
        settings.similarity_threshold_general = 0.70
        settings.similarity_threshold_technical = 0.90
        settings.similarity_threshold_default = 0.75
        return settings

    @pytest.fixture
    def threshold_service(self, mock_settings):
        return ThresholdService(mock_settings)

    def test_init_threshold_map(self, threshold_service, mock_settings):
        assert (
            threshold_service._threshold_map[QueryType.SPECIFIC]
            == mock_settings.similarity_threshold_specific
        )
        assert (
            threshold_service._threshold_map[QueryType.GENERAL]
            == mock_settings.similarity_threshold_general
        )
        assert (
            threshold_service._threshold_map[QueryType.TECHNICAL]
            == mock_settings.similarity_threshold_technical
        )
        assert (
            threshold_service._threshold_map[QueryType.DEFAULT]
            == mock_settings.similarity_threshold_default
        )

    def test_determine_query_type_specific_patterns(self, threshold_service):
        specific_queries = [
            "Como escrever um ofício?",
            "Como fazer uma ata?",
            "Como criar um relatório?",
            "Como elaborar um documento?",
            "Modelo de contrato",
            "Exemplo de memorando",
            "Estrutura de relatório",
            "Formato de ofício",
        ]
        for query in specific_queries:
            assert threshold_service.determine_query_type(query) == QueryType.SPECIFIC

    def test_determine_query_type_general_patterns(self, threshold_service):
        general_queries = [
            "O que é um ofício?",
            "O que são documentos oficiais?",
            "Quais são os tipos de documento?",
            "Quais os requisitos?",
            "Tipos de contrato",
            "Conceito de licitação",
            "Definição de processo",
        ]
        for query in general_queries:
            assert threshold_service.determine_query_type(query) == QueryType.GENERAL

    def test_determine_query_type_technical_patterns(self, threshold_service):
        technical_queries = [
            "Artigo 37 da Constituição",
            "Lei nº 8666",
            "Lei n° 14133",
            "Lei no 12527",
            "Decreto nº 10024",
            "Decreto n° 9203",
            "Resolução nº 123",
            "Portaria nº 456",
            "Parágrafo § 1º",
            "Parágrafo 2",
        ]
        for query in technical_queries:
            assert threshold_service.determine_query_type(query) == QueryType.TECHNICAL

    def test_determine_query_type_default(self, threshold_service):
        default_queries = [
            "Preciso de ajuda",
            "Informações sobre processo",
            "Documentação necessária",
            "Prazo para entrega",
            "Status do pedido",
        ]
        for query in default_queries:
            assert threshold_service.determine_query_type(query) == QueryType.DEFAULT

    def test_determine_query_type_case_insensitive(self, threshold_service):
        queries = [
            ("COMO ESCREVER UM OFÍCIO?", QueryType.SPECIFIC),
            ("O QUE É UM PROCESSO?", QueryType.GENERAL),
            ("ARTIGO 37", QueryType.TECHNICAL),
            ("INFORMAÇÕES GERAIS", QueryType.DEFAULT),
        ]
        for query, expected_type in queries:
            assert threshold_service.determine_query_type(query) == expected_type

    def test_determine_query_type_priority_technical_over_specific(
        self, threshold_service
    ):
        query = "Como aplicar o artigo 37?"
        assert threshold_service.determine_query_type(query) == QueryType.TECHNICAL

    def test_determine_query_type_priority_technical_over_general(
        self, threshold_service
    ):
        query = "O que é o decreto nº 123?"
        assert threshold_service.determine_query_type(query) == QueryType.TECHNICAL

    def test_determine_query_type_priority_specific_over_general(
        self, threshold_service
    ):
        query = "Como fazer o que é necessário?"
        assert threshold_service.determine_query_type(query) == QueryType.SPECIFIC

    def test_get_threshold_for_query_specific(self, threshold_service, mock_settings):
        query = "Como escrever um ofício?"
        threshold = threshold_service.get_threshold_for_query(query)
        assert threshold == mock_settings.similarity_threshold_specific

    def test_get_threshold_for_query_general(self, threshold_service, mock_settings):
        query = "O que é um processo?"
        threshold = threshold_service.get_threshold_for_query(query)
        assert threshold == mock_settings.similarity_threshold_general

    def test_get_threshold_for_query_technical(self, threshold_service, mock_settings):
        query = "Artigo 37 da Constituição"
        threshold = threshold_service.get_threshold_for_query(query)
        assert threshold == mock_settings.similarity_threshold_technical

    def test_get_threshold_for_query_default(self, threshold_service, mock_settings):
        query = "Informações gerais"
        threshold = threshold_service.get_threshold_for_query(query)
        assert threshold == mock_settings.similarity_threshold_default

    def test_get_threshold_by_type_specific(self, threshold_service, mock_settings):
        threshold = threshold_service.get_threshold_by_type(QueryType.SPECIFIC)
        assert threshold == mock_settings.similarity_threshold_specific

    def test_get_threshold_by_type_general(self, threshold_service, mock_settings):
        threshold = threshold_service.get_threshold_by_type(QueryType.GENERAL)
        assert threshold == mock_settings.similarity_threshold_general

    def test_get_threshold_by_type_technical(self, threshold_service, mock_settings):
        threshold = threshold_service.get_threshold_by_type(QueryType.TECHNICAL)
        assert threshold == mock_settings.similarity_threshold_technical

    def test_get_threshold_by_type_default(self, threshold_service, mock_settings):
        threshold = threshold_service.get_threshold_by_type(QueryType.DEFAULT)
        assert threshold == mock_settings.similarity_threshold_default

    def test_get_all_thresholds(self, threshold_service, mock_settings):
        all_thresholds = threshold_service.get_all_thresholds()
        expected = {
            "specific": mock_settings.similarity_threshold_specific,
            "general": mock_settings.similarity_threshold_general,
            "technical": mock_settings.similarity_threshold_technical,
            "default": mock_settings.similarity_threshold_default,
        }
        assert all_thresholds == expected

    def test_technical_patterns_variations(self, threshold_service):
        technical_variations = [
            "artigo 123",
            "Artigo 456",
            "lei nº 8666",
            "lei n° 12527",
            "lei no 14133",
            "decreto nº 10024",
            "decreto n° 9203",
            "decreto no 7724",
            "resolução nº 456",
            "resolução n° 789",
            "portaria nº 123",
            "portaria n° 456",
            "parágrafo § 1º",
            "parágrafo § 2",
            "parágrafo 3",
        ]
        for query in technical_variations:
            assert threshold_service.determine_query_type(query) == QueryType.TECHNICAL

    def test_empty_query(self, threshold_service):
        assert threshold_service.determine_query_type("") == QueryType.DEFAULT

    def test_whitespace_only_query(self, threshold_service):
        assert threshold_service.determine_query_type("   ") == QueryType.DEFAULT


class TestQueryType:
    def test_query_type_enum_values(self):
        assert QueryType.SPECIFIC.value == "specific"
        assert QueryType.GENERAL.value == "general"
        assert QueryType.TECHNICAL.value == "technical"
        assert QueryType.DEFAULT.value == "default"

    def test_query_type_enum_members(self):
        assert len(QueryType) == 4
        assert QueryType.SPECIFIC in QueryType
        assert QueryType.GENERAL in QueryType
        assert QueryType.TECHNICAL in QueryType
        assert QueryType.DEFAULT in QueryType
