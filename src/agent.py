from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            return "Không tìm thấy thông tin liên quan trong kho tri thức."

        context_blocks = []
        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            source = (
                metadata.get("source_url")
                or metadata.get("source")
                or metadata.get("file_path")
                or metadata.get("doc_id")
                or result.get("id", "unknown")
            )
            context_blocks.append(f"[{index}] Source: {source}\n{result['content']}")
        context = "\n\n".join(context_blocks)
        prompt = (
            "Answer the question using only the supplied context. "
            "Cite supporting chunks with bracketed numbers such as [1] or [2]. "
            "If the context does not contain the answer, explicitly say that the information was not found; "
            "do not guess or use outside knowledge.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\nAnswer:"
        )
        return self.llm_fn(prompt)
