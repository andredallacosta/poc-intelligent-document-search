import re
from typing import Any, Dict, Optional


class ContextGenerator:

    def __init__(self):
        self.content_patterns = {
            "legal": ["artigo", "lei", "decreto", "resolução", "parágrafo", "inciso"],
            "financial": [
                "receita",
                "despesa",
                "orçamento",
                "valor",
                "custo",
                "preço",
                "proposta",
            ],
            "administrative": [
                "ofício",
                "memorando",
                "circular",
                "portaria",
                "município",
                "presidente",
                "câmara",
                "vereador",
                "prefeito",
            ],
            "technical": ["função", "método", "algoritmo", "sistema", "processo"],
            "medical": ["paciente", "diagnóstico", "tratamento", "medicamento"],
            "academic": ["pesquisa", "estudo", "análise", "conclusão", "bibliografia"],
        }

        self.section_indicators = [
            r"^#{1,6}\s+(.+)$",
            r"^[A-Z][^.]*:$",
            r"^\d+\.\s+(.+)$",
            r"^[IVX]+\.\s+(.+)$",
            r"^[a-z]\)\s+(.+)$",
        ]

    def generate_context(
        self, chunk: str, metadata: Dict[str, Any], position_info: Dict[str, Any]
    ) -> str:
        context_parts = []

        doc_context = self._get_document_context(metadata)
        if doc_context:
            context_parts.append(doc_context)

        section_context = self._get_section_context(chunk, position_info)
        if section_context:
            context_parts.append(section_context)

        content_context = self._get_content_type_context(chunk)
        if content_context:
            context_parts.append(content_context)

        if context_parts:
            context = " | ".join(context_parts) + ": "
            return context + chunk

        return chunk

    def _get_document_context(self, metadata: Dict[str, Any]) -> Optional[str]:
        context_parts = []

        if metadata.get("title"):
            title = metadata["title"][:30]
            if len(metadata["title"]) > 30:
                title += "..."
            context_parts.append(f"Doc: {title}")
        elif metadata.get("source"):
            source = metadata["source"].split(".")[0][:25]
            context_parts.append(f"Doc: {source}")

        if metadata.get("file_type"):
            file_type = metadata["file_type"].upper()
            context_parts.append(f"Tipo: {file_type}")

        return " | ".join(context_parts) if context_parts else None

    def _get_section_context(
        self, chunk: str, position_info: Dict[str, Any]
    ) -> Optional[str]:
        for pattern in self.section_indicators:
            matches = re.findall(pattern, chunk, re.MULTILINE)
            if matches:
                header = matches[0][:20]
                if len(matches[0]) > 20:
                    header += "..."
                return f"Seção: {header}"

        chunk_index = position_info.get("chunk_index", 0)
        total_chunks = position_info.get("total_chunks", 1)

        if total_chunks > 1:
            relative_position = chunk_index / total_chunks

            if relative_position < 0.2:
                return "Início do documento"
            elif relative_position > 0.8:
                return "Final do documento"
            else:
                section_num = int((chunk_index / total_chunks) * 10) + 1
                return f"Seção {section_num}"

        return None

    def _get_content_type_context(self, chunk: str) -> Optional[str]:
        chunk_lower = chunk.lower()

        type_scores = {}
        for content_type, patterns in self.content_patterns.items():
            score = sum(chunk_lower.count(pattern) for pattern in patterns)
            if score > 0:
                type_scores[content_type] = score

        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            return f"Conteúdo: {best_type.title()}"

        if re.search(r"\$\d+|R\$\s*\d+|\€\d+", chunk):
            return "Conteúdo: Financeiro"
        elif re.search(r"\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}", chunk):
            return "Conteúdo: Datas"
        elif chunk.count("?") > 2:
            return "Conteúdo: Perguntas"
        elif re.search(r"^\d+\.", chunk, re.MULTILINE):
            return "Conteúdo: Lista numerada"

        return None

    def extract_document_metadata(
        self, full_text: str, file_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        enhanced_metadata = file_metadata.copy()

        if not enhanced_metadata.get("title"):
            title = self._extract_title_from_text(full_text)
            if title:
                enhanced_metadata["title"] = title

        language = self._detect_language(full_text)
        if language:
            enhanced_metadata["language"] = language

        enhanced_metadata["headers_count"] = self._count_headers(full_text)
        enhanced_metadata["has_tables"] = self._has_tables(full_text)
        enhanced_metadata["has_lists"] = self._has_lists(full_text)

        return enhanced_metadata

    def _extract_title_from_text(self, text: str) -> Optional[str]:
        lines = text.split("\n")[:10]

        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 100:
                if (
                    line.isupper()
                    or line.count(" ") < 8
                    or re.match(r"^[A-Z][^.]*$", line)
                ):
                    return line

        return None

    def _detect_language(self, text: str) -> str:
        sample = text[:1000].lower()

        portuguese_words = ["que", "para", "com", "uma", "dos", "são", "este", "pela"]
        english_words = ["the", "and", "that", "have", "for", "not", "with", "you"]

        pt_count = sum(sample.count(word) for word in portuguese_words)
        en_count = sum(sample.count(word) for word in english_words)

        return "portuguese" if pt_count > en_count else "english"

    def _count_headers(self, text: str) -> int:
        count = 0
        for pattern in self.section_indicators:
            count += len(re.findall(pattern, text, re.MULTILINE))
        return count

    def _has_tables(self, text: str) -> bool:
        return bool(re.search(r"\|.*\|.*\|", text) or text.count("\t") > 10)

    def _has_lists(self, text: str) -> bool:
        return bool(
            re.search(r"^\s*[-*•]\s+", text, re.MULTILINE)
            or re.search(r"^\s*\d+\.\s+", text, re.MULTILINE)
        )
