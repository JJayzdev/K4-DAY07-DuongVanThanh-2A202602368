from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from src import (
    Document,
    EmbeddingStore,
    GeminiEmbedder,
    HeadingChunker,
    LocalEmbedder,
    OpenAIEmbedder,
)


CORPUS_DIR = Path("data/ebay-policy")
CACHE_DIR = Path(".cache")

# This is the only line each member should change for a fair chunking comparison.
chunker = HeadingChunker(chunk_size=700)

BENCHMARKS = [
    {
        "query": "Sau khi yêu cầu hủy được gửi, bên còn lại có bao lâu để phản hồi?",
        "gold_answer": "Người bán có 3 ngày theo lịch để chấp nhận hoặc từ chối yêu cầu hủy.",
        "gold_doc_ids": ["ebay-buyer-cancel-order"],
        "answer_marker": "within 3 calendar days",
        "metadata_filter": {"audience": "buyer"},
    },
    {
        "query": "Người mua phải báo chưa nhận được hàng trong thời hạn bao lâu để đủ điều kiện bảo vệ?",
        "gold_answer": "Trong vòng 30 ngày theo lịch kể từ ngày giao hàng dự kiến.",
        "gold_doc_ids": ["ebay-buyer-item-not-received"],
        "answer_marker": "within 30 calendar days after the delivery date",
        "metadata_filter": None,
    },
    {
        "query": "Điều kiện nào để Top Rated Seller được hưởng bảo vệ của eBay?",
        "gold_answer": "Phải là Top Rated Seller, ở Mỹ hoặc Canada, không có service metric mức Very High, đăng trên eBay.com và niêm yết cho phép trả hàng từ 30 ngày trở lên.",
        "gold_doc_ids": ["ebay-seller-protections"],
        "answer_marker": "The listing offered 30-day or longer returns",
        "metadata_filter": {"audience": "seller"},
    },
    {
        "query": "Người mua thực hiện các bước nào để báo một món hàng chưa đến?",
        "gold_answer": "Mở Purchases, tìm món hàng, chọn More actions, chọn I didn't receive it, chọn cách xử lý mong muốn, thêm lời nhắn nếu cần rồi gửi yêu cầu.",
        "gold_doc_ids": ["ebay-buyer-item-not-received"],
        "answer_marker": "I didn't receive it",
        "metadata_filter": {"audience": "buyer"},
    },
    {
        "query": "Người bán có thể chọn những thời hạn và hình thức trả hàng nào?",
        "gold_answer": "Không nhận trả hàng; trả hàng 30 ngày do người mua trả phí; miễn phí 30 ngày; người mua trả phí 60 ngày; hoặc miễn phí 60 ngày. Một số danh mục cho phép 14 ngày.",
        "gold_doc_ids": ["ebay-seller-return-policy"],
        "answer_marker": "30-day buyer-paid returns",
        "metadata_filter": {"audience": "seller"},
    },
]


class CachedEmbedder:
    """Persist embeddings by backend and content hash to avoid repeated API cost."""

    def __init__(self, embedder: Callable[[str], list[float]], backend_name: str) -> None:
        CACHE_DIR.mkdir(exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", backend_name)
        self.path = CACHE_DIR / f"bench-embeddings-{safe_name}.json"
        self.embedder = embedder
        self.cache = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self._backend_name = f"{backend_name} (cached)"

    def __call__(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if key not in self.cache:
            self.cache[key] = self.embedder(text)
            self.path.write_text(json.dumps(self.cache), encoding="utf-8")
        return [float(value) for value in self.cache[key]]


def parse_markdown(path: Path) -> tuple[dict[str, str], str]:
    raw = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", raw, re.S)
    if not match:
        raise ValueError(f"Missing YAML frontmatter: {path}")
    metadata = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')
    return metadata, match.group(2).strip()


def build_documents(selected_chunker=chunker) -> list[Document]:
    documents = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        frontmatter, content = parse_markdown(path)
        for index, chunk in enumerate(selected_chunker.chunk(content)):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata={**frontmatter, "doc_id": path.stem, "chunk_index": index},
                )
            )
    return documents


def select_embedder() -> CachedEmbedder:
    load_dotenv(override=False)
    provider = os.getenv("EMBEDDING_PROVIDER", "gemini").strip().lower()
    if provider == "local":
        # Keep live demos deterministic once the model has been downloaded.
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        logging.getLogger("tensorflow").setLevel(logging.ERROR)
        warnings.filterwarnings("ignore", message=".*flash attention.*")
        embedder = LocalEmbedder()
    elif provider == "openai":
        embedder = OpenAIEmbedder()
    elif provider == "gemini":
        embedder = GeminiEmbedder()
    else:
        raise ValueError("EMBEDDING_PROVIDER must be local, openai, or gemini; mock is not valid for benchmarks")
    return CachedEmbedder(embedder, getattr(embedder, "_backend_name", provider))


def evaluate_results(results: list[dict], gold_doc_ids: list[str], answer_marker: str) -> dict:
    doc_ranks = [
        rank
        for rank, result in enumerate(results, start=1)
        if result["metadata"].get("doc_id") in gold_doc_ids
    ]
    answer_ranks = [
        rank
        for rank, result in enumerate(results, start=1)
        if result["metadata"].get("doc_id") in gold_doc_ids
        and answer_marker.casefold() in result["content"].casefold()
    ]
    answer_rank = min(answer_ranks, default=None)
    points = 2 if answer_rank == 1 else 1 if answer_rank in {2, 3} else 0
    return {
        "doc_rank": min(doc_ranks, default=None),
        "answer_rank": answer_rank,
        "points": points,
    }


def print_results(
    label: str,
    results: list[dict],
    gold_doc_ids: list[str],
    answer_marker: str,
) -> dict:
    print(f"  {label}")
    for rank, result in enumerate(results, start=1):
        doc_id = result["metadata"].get("doc_id", "unknown")
        chunk_index = result["metadata"].get("chunk_index", "?")
        is_gold_doc = doc_id in gold_doc_ids
        has_answer = answer_marker.casefold() in result["content"].casefold()
        marker = "ANSWER" if is_gold_doc and has_answer else "GOLD-DOC" if is_gold_doc else ""
        print(
            f"    {rank}. score={result['score']:.4f} "
            f"doc_id={doc_id} chunk={chunk_index} {marker}".rstrip()
        )
    evaluation = evaluate_results(results, gold_doc_ids, answer_marker)
    print(
        f"    doc_rank={evaluation['doc_rank']} answer_rank={evaluation['answer_rank']} "
        f"points={evaluation['points']}/2"
    )
    return evaluation


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    documents = build_documents()
    embedder = select_embedder()
    store = EmbeddingStore(collection_name="ebay_policy_benchmark", embedding_fn=embedder)
    store.add_documents(documents)
    print(f"Backend: {embedder._backend_name}")
    print(f"Files: {len(list(CORPUS_DIR.glob('*.md')))} | Chunks: {store.get_collection_size()}")

    doc_hits = 0
    total_points = 0
    for number, benchmark in enumerate(BENCHMARKS, start=1):
        print(f"\nQ{number}: {benchmark['query']}")
        print(f"  Gold: {benchmark['gold_answer']}")
        metadata_filter = benchmark["metadata_filter"]
        if metadata_filter:
            print_results(
                "Unfiltered top-3:",
                store.search(benchmark["query"], top_k=3),
                benchmark["gold_doc_ids"],
                benchmark["answer_marker"],
            )
        results = store.search_with_filter(benchmark["query"], top_k=3, metadata_filter=metadata_filter)
        evaluation = print_results(
            f"Filtered top-3 {metadata_filter}:" if metadata_filter else "Top-3:",
            results,
            benchmark["gold_doc_ids"],
            benchmark["answer_marker"],
        )
        doc_hits += int(evaluation["doc_rank"] is not None)
        total_points += evaluation["points"]
    print(f"\nDocument-level top-3 hit rate: {doc_hits}/{len(BENCHMARKS)}")
    print(f"Answer-bearing chunk score: {total_points}/{len(BENCHMARKS) * 2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
