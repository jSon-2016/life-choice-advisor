#!/usr/bin/env python
"""RAG 迷你评测：读取 golden_gaokao.jsonl，统计召回与拒答准确率。

用法:
  python eval/run_eval.py
  python eval/run_eval.py --file eval/golden_gaokao.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.service.knowledge_base_loader import KnowledgeBaseLoader
from app.service.rag_service import RAGService


def load_golden(path: Path) -> list[dict]:
    items: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def eval_rag(rag: RAGService, golden: list[dict]) -> dict:
    passed = 0
    details: list[str] = []

    for item in golden:
        profile = item["profile"]
        result = rag.build_context_for_gaokao(profile)
        context_blob = result.context + " ".join(h.content for h in result.hits)

        must_hit = item.get("rag_must_hit", [])
        hit_ok = all(kw in context_blob for kw in must_hit) if must_hit else True

        expect_low = item.get("expect_low_confidence", False)
        confidence_ok = result.low_confidence if expect_low else not result.low_confidence or bool(must_hit)

        ok = hit_ok and confidence_ok
        passed += int(ok)
        status = "PASS" if ok else "FAIL"
        details.append(
            f"[{status}] id={item.get('id')} hits={len(result.hits)} "
            f"score={result.top_score:.2f} low_conf={result.low_confidence} "
            f"hit_ok={hit_ok} conf_ok={confidence_ok}"
        )

    total = len(golden) or 1
    return {
        "passed": passed,
        "total": len(golden),
        "pass_rate": passed / total,
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Life Choice Advisor RAG eval")
    parser.add_argument(
        "--file",
        default=str(ROOT / "eval" / "golden_gaokao.jsonl"),
        help="黄金样本 JSONL 路径",
    )
    args = parser.parse_args()
    path = Path(args.file)
    if not path.exists():
        print(f"文件不存在: {path}")
        return 1

    rag = RAGService(KnowledgeBaseLoader())
    golden = load_golden(path)
    report = eval_rag(rag, golden)

    print(f"RAG Eval: {report['passed']}/{report['total']} passed ({report['pass_rate']:.0%})")
    for line in report["details"]:
        print(line)
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
