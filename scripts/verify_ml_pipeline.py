"""Real, offline ONNX pipeline verification in disposable warehouses.

python -m scripts.verify_ml_pipeline --records 1000
Authored diagnostics measure implementation behavior, not production accuracy.
Never promotes semantic builds or calls a paid provider.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import tempfile
import time


def _category_diagnostic(pack, provider, profile):
    from src.ml_runtime.category_zeroshot import get_category_centroids, predict_category_zero_shot
    from src.frontline.shadow_pilot import _ADVERSARIAL_PARAPHRASE_TEMPLATES
    os.environ["FRONTLINE_CATEGORY_ZS_PROFILE"] = profile
    get_category_centroids(pack, provider)
    rows = []
    for gold, texts in _ADVERSARIAL_PARAPHRASE_TEMPLATES.items():
        for text in texts:
            prediction = predict_category_zero_shot(text, pack, embedder=provider)
            rows.append({"text": text, "gold": gold, "prediction": prediction.category,
                         "top1": prediction.top1_category, "score": prediction.top1_score,
                         "margin": prediction.margin, "latency_ms": prediction.latency_ms,
                         "unavailable": prediction.unavailable})
    accepted = [r for r in rows if r["prediction"]]
    return {"profile": profile, "label_source": "existing_builder_authored_adversarial_templates",
            "acceptance_eligible": False, "held_out": False, "n": len(rows),
            "accuracy": round(sum(r["prediction"] == r["gold"] for r in rows) / len(rows), 4),
            "accepted_precision": round(sum(r["prediction"] == r["gold"] for r in accepted) / len(accepted), 4) if accepted else None,
            "coverage": round(len(accepted) / len(rows), 4),
            "unavailable": sum(r["unavailable"] for r in rows),
            "per_category": {cat: {"n": sum(r["gold"] == cat for r in rows),
                                    "correct": sum(r["prediction"] == cat for r in rows if r["gold"] == cat)}
                             for cat in _ADVERSARIAL_PARAPHRASE_TEMPLATES}, "rows": rows}


def _verify(root: Path, records: int) -> dict:
    os.environ.update({"FRONTLINE_TEST_ISOLATION": "1", "FRONTLINE_DB_PATH": str(root / "ops.duckdb"),
                       "DOMAIN_DB_PATH": str(root / "domains"), "BUILDER_UPLOAD_DIR": str(root / "uploads"),
                       "DOMAIN_PACK": "automotive_nhtsa", "FRONTLINE_EMBEDDING_TOY": "0",
                       "FRONTLINE_EMBEDDING_MODE": "shadow", "FRONTLINE_ACTIVE_CLUSTER_BUILD_ID": "",
                       "FRONTLINE_EMBEDDING_SHADOW_KILL": "0", "FRONTLINE_SLM_MODE": "legacy",
                       "FRONTLINE_SLM_KILL": "0", "FRONTLINE_ENABLED": "1", "FRONTLINE_OPEN_MODE": "1",
                       "FRONTLINE_AUTH_REQUIRED": "0", "FRONTLINE_API_KEY": "", "META_API_KEY": "",
                       "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": "", "TOKENIZERS_PARALLELISM": "false",
                       "FRONTLINE_CATEGORY_ZS_FLOOR": "0.35", "FRONTLINE_CATEGORY_ZS_MARGIN": "0.05",
                       "FRONTLINE_CATEGORY_ZS_TIMEOUT_MS": "25", "FRONTLINE_SEMANTIC_MODEL_SHA256": ""})
    from src.agents.base import InteractionContext
    from src.agents.intake import extract_pack_category
    from src.data.warehouse import domain_con
    from src.domains.csv_load import load_csv_rows
    from src.domains.loader import load_pack
    from src.frontline.shadow_pilot import _ADVERSARIAL_PARAPHRASE_TEMPLATES
    from src.ml_runtime.cluster_builds import rebuild_cluster_build, activate_cluster_build, rollback_cluster_build
    from src.ml_runtime.embedding_backfill import run_backfill
    from src.ml_runtime.embedding_eval import evaluate_pairs
    from src.ml_runtime.embedding_match import rank_semantic
    from src.ml_runtime.embedding_runtime import active_embedder, reset_embedding_runtime, semantic_embedder
    from src.ml_runtime.embedding_space import HASH_EMBEDDING_VERSION
    from src.ml_runtime.embedding_store import coverage_for_version, get_embedding
    from src.ml_runtime.hash_embedder import HashEmbedder
    from src.jobs.queue import enqueue, run_next

    reset_embedding_runtime()
    provider = semantic_embedder()
    provider.embed("warmup")
    pack = load_pack("automotive_nhtsa")
    report = {"provider": "onnx", "version": provider.version,
              "model_sha256": provider.artifact_metadata().model_sha256,
              "paid_calls": 0, "warehouses": "disposable", "records_requested": records,
              "semantic_promotion": "blocked_pending_independent_human_evidence"}
    checks = report["checks"] = {}
    samples = [(cat, text) for cat, texts in _ADVERSARIAL_PARAPHRASE_TEMPLATES.items() for text in texts]
    uploads = root / "uploads"
    uploads.mkdir()
    source = uploads / "diagnostic.csv"
    fields = ("record_id", "text", "category", "entity_2", "entity_3", "received_at")
    with source.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for i in range(records):
            category, text = samples[i % len(samples)]
            writer.writerow(dict(zip(fields, (f"{i:06d}", text, category, "DIAGNOSTIC", "FIXTURE", "2026-10-28"))))
    t0 = time.perf_counter()
    ingest = load_csv_rows(pack.id, source, mapping={field: field for field in fields}, source="technical", provenance="fixture")
    assert ingest["written"] == records
    checks["csv_ingestion"] = {"passed": True, "written": records, "duration_s": round(time.perf_counter() - t0, 3)}
    first = run_backfill(pack.id, provider.version, batch_size=32)
    assert first["newly_completed"] == records and first["coverage"]["complete"] == records
    checks["real_onnx_backfill"] = {"passed": True, "duration_s": first["duration_s"], "throughput_per_s": first["throughput_per_s"], "coverage": first["coverage"]}
    repeat = run_backfill(pack.id, provider.version, batch_size=32)
    assert repeat["newly_completed"] == 0
    checks["idempotent_backfill"] = {"passed": True, "duration_s": repeat["duration_s"]}
    build = rebuild_cluster_build(pack.id, provider.version, k=8, max_distance=2.0)
    assert build["assignments"] == records and build["status"] == "built"
    checks["versioned_cluster_build"] = {"passed": True, "duration_s": build["duration_s"], "assignments": build["assignments"], "clusters": build["clusters"]}
    try:
        activate_cluster_build(pack.id, build["build_id"])
    except ValueError as exc:
        assert "approved retrieval scorecard" in str(exc)
    else:
        raise AssertionError("semantic promotion was not blocked")
    checks["unapproved_promotion_rejected"] = {"passed": True}
    with domain_con(pack.id, read_only=True) as con:
        candidates = [dict(zip(("record_id", "text", "category"), r)) for r in con.execute("SELECT record_id, text, category FROM records ORDER BY record_id").fetchall()]
    ranked = rank_semantic(pack.id, samples[0][1], candidates)
    assert ranked["status"] == "performed" and ranked["ranked"][0]["category"] == samples[0][0]
    assert ranked["ranked"][0]["sim_score"] > 0.99
    checks["semantic_retrieval_exact_replay"] = {"passed": True, "top_score": ranked["ranked"][0]["sim_score"], "note": "Exact replay verifies plumbing; not unseen retrieval accuracy."}
    rid = candidates[0]["record_id"]
    with domain_con(pack.id, read_only=False) as con:
        con.execute("UPDATE records SET text = 'updated electrical wiring complaint' WHERE record_id = ?", [rid])
    assert get_embedding(pack.id, rid, provider.version) is None
    assert coverage_for_version(pack.id, provider.version)["complete"] == records - 1
    job = enqueue("embedding_backfill", {"pack_id": pack.id, "embedding_version": provider.version}, idempotency_key="technical-refresh")
    duplicate = enqueue("embedding_backfill", {"pack_id": pack.id, "embedding_version": provider.version}, idempotency_key="technical-refresh")
    assert duplicate["job_id"] == job["job_id"] and duplicate["duplicate"]
    completed = run_next(worker_id="technical-worker")
    assert completed["status"] == "done" and get_embedding(pack.id, rid, provider.version) is not None
    checks["queued_stale_source_refresh"] = {"passed": True, "job_status": completed["status"], "coverage": coverage_for_version(pack.id, provider.version)}
    from src.ml_runtime.anomalies import recompute_weekly_anomalies
    assert recompute_weekly_anomalies(pack.id) == []
    checks["fixture_provenance_excluded_from_live_anomalies"] = {"passed": True}
    os.environ["FRONTLINE_EMBEDDING_MODE"] = "rollback"
    assert active_embedder().version == HASH_EMBEDDING_VERSION
    rollback_cluster_build(pack.id, build["build_id"])
    checks["hash_rollback"] = {"passed": True}
    report["pair_diagnostic"] = evaluate_pairs({"hash": HashEmbedder(), "onnx": provider})
    report["category_diagnostics"] = {profile: _category_diagnostic(pack, provider, profile) for profile in ("labels", "descriptions")}
    report["rules_category_diagnostic_accuracy"] = round(sum(extract_pack_category(text, InteractionContext(interaction_id="diag", pack=pack), rules_only=True) == cat for cat, text in samples) / len(samples), 4)
    report["technical_checks_passed"] = all(check["passed"] for check in checks.values())
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, default=1000)
    parser.add_argument("--out", default="reports/technical/ml_pipeline.json")
    args = parser.parse_args(argv)
    if args.records < 76:
        parser.error("--records must be at least 76 to cover the diagnostic corpus")
    with tempfile.TemporaryDirectory(prefix="tracex-technical-") as tmp:
        report = _verify(Path(tmp), args.records)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(out), "checks": report["checks"], "category_diagnostics": {p: {k: v for k, v in r.items() if k not in {"rows", "per_category"}} for p, r in report["category_diagnostics"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
