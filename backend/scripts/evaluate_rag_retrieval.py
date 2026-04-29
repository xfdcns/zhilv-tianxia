from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agents.tools.rag_tool import build_destination_query
from app.rag.retriever import retrieve_travel_guide_chunks


DEFAULT_CASES_PATH = BACKEND_DIR / "eval" / "rag_eval_cases.json"


def _load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("RAG eval cases file must contain a JSON list.")
    return data


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    top_k = int(case.get("top_k", 5))
    destination = str(case["destination"])
    query = build_destination_query(
        destination=destination,
        preferences=list(case.get("preferences", [])),
        pace=case.get("pace"),
        special_notes=case.get("special_notes"),
    )
    chunks = retrieve_travel_guide_chunks(query=query, top_k=top_k, destination=destination)

    expected_title_keywords = list(case.get("expected_title_keywords", []))
    required_content_keywords = list(case.get("required_content_keywords", []))
    noise_title_keywords = list(case.get("noise_title_keywords", []))

    titles = [str(chunk.get("title", "")) for chunk in chunks]
    combined_text = "\n".join(
        f"{chunk.get('title', '')}\n{chunk.get('text', '')}" for chunk in chunks
    )

    top1_title = titles[0] if titles else ""
    top1_title_hit = _contains_any(top1_title, expected_title_keywords)
    topk_title_hit = any(_contains_any(title, expected_title_keywords) for title in titles)
    required_keyword_hits = _count_keyword_hits(combined_text, required_content_keywords)
    noise_count = sum(
        1 for title in titles if _contains_any(title, noise_title_keywords)
    )

    return {
        "id": case.get("id", "<unknown>"),
        "query": query,
        "top1_title": top1_title,
        "top1_title_hit": top1_title_hit,
        "topk_title_hit": topk_title_hit,
        "required_keyword_hits": required_keyword_hits,
        "required_keyword_total": len(required_content_keywords),
        "noise_count": noise_count,
        "titles": titles,
    }


def _print_case_result(result: dict[str, Any]) -> None:
    print(f"case: {result['id']}")
    print(f"query: {result['query']}")
    print(f"top1_title: {result['top1_title']}")
    print(f"top1_title_hit: {result['top1_title_hit']}")
    print(f"topk_title_hit: {result['topk_title_hit']}")
    print(
        "required_keyword_hits: "
        f"{result['required_keyword_hits']}/{result['required_keyword_total']}"
    )
    print(f"noise_count: {result['noise_count']}")
    print("titles:")
    for index, title in enumerate(result["titles"], start=1):
        print(f"  {index}. {title}")
    print("-" * 60)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate RAG retrieval quality with a small scenario case set."
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
        help="Path to the RAG eval cases JSON file.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    cases = _load_cases(args.cases)
    results = [_evaluate_case(case) for case in cases]

    for result in results:
        _print_case_result(result)

    total = len(results)
    top1_hits = sum(1 for result in results if result["top1_title_hit"])
    topk_hits = sum(1 for result in results if result["topk_title_hit"])
    total_noise = sum(int(result["noise_count"]) for result in results)
    total_required_hits = sum(int(result["required_keyword_hits"]) for result in results)
    total_required_keywords = sum(
        int(result["required_keyword_total"]) for result in results
    )

    print("=== Summary ===")
    print(f"cases: {total}")
    print(f"top1_title_hit_rate: {top1_hits}/{total}")
    print(f"topk_title_hit_rate: {topk_hits}/{total}")
    print(f"required_keyword_coverage: {total_required_hits}/{total_required_keywords}")
    print(f"noise_count_total: {total_noise}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
