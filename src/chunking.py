from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        # Split after sentence-ending punctuation so the punctuation remains
        # attached to the sentence instead of being consumed by the regex.
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])(?:[ \t]+|\n+)", text.strip())
            if sentence.strip()
        ]
        return [
            " ".join(sentences[start : start + self.max_sentences_per_chunk]).strip()
            for start in range(0, len(sentences), self.max_sentences_per_chunk)
        ]


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text.strip()] if current_text.strip() else []
        if not remaining_separators or remaining_separators[0] == "":
            return [
                current_text[start : start + self.chunk_size].strip()
                for start in range(0, len(current_text), self.chunk_size)
                if current_text[start : start + self.chunk_size].strip()
            ]

        separator = remaining_separators[0]
        if separator not in current_text:
            return self._split(current_text, remaining_separators[1:])

        raw_parts = current_text.split(separator)
        parts = [
            part + (separator if index < len(raw_parts) - 1 else "")
            for index, part in enumerate(raw_parts)
            if part or index < len(raw_parts) - 1
        ]

        split_parts: list[str] = []
        for part in parts:
            if len(part) > self.chunk_size:
                split_parts.extend(self._split(part, remaining_separators[1:]))
            elif part.strip():
                split_parts.append(part)

        # Merge adjacent small pieces back up to the size limit. Without this
        # pass, line- or word-level separators would create tiny fragments.
        merged: list[str] = []
        buffer = ""
        for part in split_parts:
            if not buffer:
                buffer = part
            elif len(buffer) + len(part) <= self.chunk_size:
                buffer += part
            else:
                if buffer.strip():
                    merged.append(buffer.strip())
                buffer = part
        if buffer.strip():
            merged.append(buffer.strip())
        return merged


class HeadingChunker:
    """Split Markdown by headings, recursively splitting oversized sections.

    When a section is split, its heading is prepended to every child chunk so
    each stored record keeps the section's semantic context.
    """

    def __init__(self, chunk_size: int = 700) -> None:
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        heading_matches = list(re.finditer(r"(?m)^#{1,6}\s+.+$", text))
        if not heading_matches:
            return RecursiveChunker(chunk_size=self.chunk_size).chunk(text)

        sections: list[tuple[str, str]] = []
        preamble = text[: heading_matches[0].start()].strip()
        if preamble:
            sections.append(("", preamble))
        for index, match in enumerate(heading_matches):
            end = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(text)
            heading = match.group(0).strip()
            body = text[match.end() : end].strip()
            sections.append((heading, body))

        chunks: list[str] = []
        for heading, body in sections:
            section = f"{heading}\n\n{body}".strip() if heading else body
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            if not heading:
                chunks.extend(RecursiveChunker(chunk_size=self.chunk_size).chunk(body))
                continue

            body_size = max(1, self.chunk_size - len(heading) - 2)
            body_chunks = RecursiveChunker(chunk_size=body_size).chunk(body)
            chunks.extend(f"{heading}\n\n{part}".strip() for part in body_chunks)
        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    magnitude_a = math.sqrt(_dot(vec_a, vec_a))
    magnitude_b = math.sqrt(_dot(vec_b, vec_b))
    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (magnitude_a * magnitude_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        overlap = min(50, max(0, chunk_size - 1))
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=overlap),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }
        comparison = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            comparison[name] = {
                "count": len(chunks),
                "avg_length": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0.0,
                "chunks": chunks,
            }
        return comparison
