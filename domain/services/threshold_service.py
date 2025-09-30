import re
from enum import Enum
from typing import Dict

from infrastructure.config.settings import Settings


class QueryType(Enum):
    SPECIFIC = "specific"
    GENERAL = "general"
    TECHNICAL = "technical"
    DEFAULT = "default"


class ThresholdService:

    def __init__(self, settings: Settings):
        self._settings = settings
        self._threshold_map = {
            QueryType.SPECIFIC: settings.similarity_threshold_specific,
            QueryType.GENERAL: settings.similarity_threshold_general,
            QueryType.TECHNICAL: settings.similarity_threshold_technical,
            QueryType.DEFAULT: settings.similarity_threshold_default,
        }

        self._specific_patterns = [
            r"como\s+(escrever|fazer|criar|elaborar)",
            r"modelo\s+de",
            r"exemplo\s+de",
            r"estrutura\s+de",
            r"formato\s+de",
        ]

        self._general_patterns = [
            r"o\s+que\s+(é|são)",
            r"quais\s+(são|os)",
            r"tipos\s+de",
            r"conceito\s+de",
            r"definição\s+de",
        ]

        self._technical_patterns = [
            r"artigo\s+\d+",
            r"lei\s+n[ºo°]?\s*\d+",
            r"decreto\s+n[ºo°]?\s*\d+",
            r"resolução\s+n[ºo°]?\s*\d+",
            r"portaria\s+n[ºo°]?\s*\d+",
            r"inciso\s+[IVX]+",
            r"parágrafo\s+[§\d]+",
        ]

    def determine_query_type(self, query: str) -> QueryType:
        query_lower = query.lower()

        for pattern in self._technical_patterns:
            if re.search(pattern, query_lower):
                return QueryType.TECHNICAL

        for pattern in self._specific_patterns:
            if re.search(pattern, query_lower):
                return QueryType.SPECIFIC

        for pattern in self._general_patterns:
            if re.search(pattern, query_lower):
                return QueryType.GENERAL

        return QueryType.DEFAULT

    def get_threshold_for_query(self, query: str) -> float:
        query_type = self.determine_query_type(query)
        return self._threshold_map[query_type]

    def get_threshold_by_type(self, query_type: QueryType) -> float:
        return self._threshold_map[query_type]

    def get_all_thresholds(self) -> Dict[str, float]:
        return {
            query_type.value: threshold
            for query_type, threshold in self._threshold_map.items()
        }
