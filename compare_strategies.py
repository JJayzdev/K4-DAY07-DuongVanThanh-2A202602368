from __future__ import annotations

import sys

from bench import BENCHMARKS, build_documents, evaluate_results, select_embedder
from src import EmbeddingStore, FixedSizeChunker, HeadingChunker, RecursiveChunker, SentenceChunker


STRATEGIES = {
    "fixed": FixedSizeChunker(chunk_size=700, overlap=70),
    "sentence": SentenceChunker(max_sentences_per_chunk=3),
    "recursive": RecursiveChunker(chunk_size=700),
    "heading": HeadingChunker(chunk_size=700),
}


def result_ids(results: list[dict]) -> str:
    return ", ".join(
        f"{result['metadata']['doc_id']}#{result['metadata']['chunk_index']}({result['score']:.4f})"
        for result in results
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    embedder = select_embedder()
    print(f"Backend: {embedder._backend_name}")

    for name, selected_chunker in STRATEGIES.items():
        store = EmbeddingStore(f"benchmark_{name}", embedding_fn=embedder)
        documents = build_documents(selected_chunker)
        store.add_documents(documents)
        total_points = 0
        print(f"\n=== {name} | chunks={len(documents)} ===")
        for number, benchmark in enumerate(BENCHMARKS, start=1):
            results = store.search_with_filter(
                benchmark["query"], top_k=3, metadata_filter=benchmark["metadata_filter"]
            )
            evaluation = evaluate_results(
                results, benchmark["gold_doc_ids"], benchmark["answer_marker"]
            )
            total_points += evaluation["points"]
            print(
                f"Q{number}: doc_rank={evaluation['doc_rank']} "
                f"answer_rank={evaluation['answer_rank']} points={evaluation['points']}/2 | "
                f"{result_ids(results)}"
            )

        filter_case = BENCHMARKS[0]
        unfiltered = store.search(filter_case["query"], top_k=3)
        filtered = store.search_with_filter(
            filter_case["query"], top_k=3, metadata_filter=filter_case["metadata_filter"]
        )
        unfiltered_eval = evaluate_results(
            unfiltered, filter_case["gold_doc_ids"], filter_case["answer_marker"]
        )
        filtered_eval = evaluate_results(
            filtered, filter_case["gold_doc_ids"], filter_case["answer_marker"]
        )
        print(f"Q1 A unfiltered: {result_ids(unfiltered)} | answer_rank={unfiltered_eval['answer_rank']}")
        print(f"Q1 B buyer:      {result_ids(filtered)} | answer_rank={filtered_eval['answer_rank']}")
        print(f"CONTENT SCORE: {total_points}/10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
