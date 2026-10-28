"""Model identity, source freshness, inference admission, and rollout safety."""

from concurrent.futures import TimeoutError
from pathlib import Path
from types import SimpleNamespace
import threading
import time

import pytest

from src.data.warehouse import domain_con
from src.ml_runtime.embedding_backfill import run_backfill
from src.ml_runtime.embedding_runtime import reset_embedding_runtime
from src.ml_runtime.embedding_store import completed_ids, coverage_for_version, get_embedding, get_embeddings_for_records
from src.ml_runtime.inference_deadline import InferenceBusy, InferenceDeadline
from src.ml_runtime.onnx_embedder import ToySemanticEmbedder


@pytest.fixture
def semantic_corpus(monkeypatch, seed_automotive_pack):
    monkeypatch.setenv("FRONTLINE_EMBEDDING_TOY", "1")
    monkeypatch.setenv("FRONTLINE_EMBEDDING_MODE", "shadow")
    monkeypatch.delenv("FRONTLINE_SEMANTIC_MODEL_SHA256", raising=False)
    reset_embedding_runtime()
    version = ToySemanticEmbedder().version
    run_backfill("automotive_nhtsa", version, batch_size=16)
    yield version
    reset_embedding_runtime()


def test_text_change_invalidates_retrieval_and_resumes_backfill(semantic_corpus):
    version = semantic_corpus
    pack = "automotive_nhtsa"
    rid = sorted(completed_ids(pack, version))[0]
    before = get_embedding(pack, rid, version)
    with domain_con(pack, read_only=False) as con:
        con.execute("UPDATE records SET text = 'engine stalls with smoke on highway' WHERE record_id = ?", [rid])
    assert rid not in completed_ids(pack, version)
    assert get_embedding(pack, rid, version) is None
    assert rid not in get_embeddings_for_records(pack, [rid], version)
    coverage = coverage_for_version(pack, version)
    assert coverage["stale"] == 1
    assert coverage["complete"] == coverage["eligible"] - 1
    report = run_backfill(pack, version)
    assert report["newly_completed"] == 1
    assert get_embedding(pack, rid, version).values != before.values
    assert run_backfill(pack, version)["newly_completed"] == 0


def test_orphan_vectors_cannot_inflate_coverage(semantic_corpus):
    pack, version = "automotive_nhtsa", semantic_corpus
    rid = sorted(completed_ids(pack, version))[0]
    with domain_con(pack, read_only=False) as con:
        con.execute("DELETE FROM records WHERE record_id = ?", [rid])
    assert rid not in completed_ids(pack, version)
    assert coverage_for_version(pack, version)["complete"] == coverage_for_version(pack, version)["eligible"]


def test_source_change_during_inference_never_marks_old_vector_current(semantic_corpus, monkeypatch):
    pack, version = "automotive_nhtsa", semantic_corpus
    rid = sorted(completed_ids(pack, version))[0]
    with domain_con(pack, read_only=False) as con:
        con.execute("UPDATE records SET text = 'first revised text' WHERE record_id = ?", [rid])
    class RacingProvider(ToySemanticEmbedder):
        def embed_many(self, texts):
            vectors = super().embed_many(texts)
            with domain_con(pack, read_only=False) as con:
                con.execute("UPDATE records SET text = 'second revision during inference' WHERE record_id = ?", [rid])
            return vectors
    monkeypatch.setattr("src.ml_runtime.embedding_backfill._select_embedder", lambda _: RacingProvider())
    result = run_backfill(pack, version)
    assert result["run_status"] == "partial"
    assert get_embedding(pack, rid, version) is None


def test_timed_out_native_work_holds_capacity_until_finished():
    runner = InferenceDeadline(workers=1)
    entered, release = threading.Event(), threading.Event()
    def blocked():
        entered.set()
        release.wait(2)
        return 42
    try:
        with pytest.raises(TimeoutError):
            runner.run(blocked, deadline=time.monotonic() + 0.03)
        assert entered.is_set()
        for _ in range(20):
            with pytest.raises(InferenceBusy):
                runner.run(lambda: 0, deadline=time.monotonic() + 1)
        release.set()
        runner._pool.shutdown(wait=True)
    finally:
        release.set()


@pytest.mark.parametrize("module,provider_name", [
    ("src.ml_runtime.category_zeroshot", "get_category_embedder"),
    ("src.ml_runtime.slm_runtime", "get_slm_embedder"),
])
def test_deadline_includes_cold_provider_loading(monkeypatch, pack, module, provider_name):
    import importlib
    runtime = importlib.import_module(module)
    runner = InferenceDeadline(workers=1)
    entered, release = threading.Event(), threading.Event()
    def cold():
        entered.set()
        release.wait(2)
        return ToySemanticEmbedder()
    monkeypatch.setattr(runtime, provider_name, cold)
    monkeypatch.setattr(runtime, "LOCAL_INFERENCE", runner)
    try:
        started = time.monotonic()
        result = runtime.predict_category_zero_shot("the engine stalls", pack, timeout_ms=20)
        assert entered.is_set()
        assert result.category is None
        assert time.monotonic() - started < 0.3
        assert not release.is_set()
    finally:
        release.set()
        runner._pool.shutdown(wait=True)


def _pack(categories):
    gaz = SimpleNamespace(values=categories, canonical={c.lower(): c for c in categories})
    return SimpleNamespace(id="same_pack", taxonomy={}, gazetteer_for_slot=lambda _: gaz)


def test_category_caches_follow_pack_contents_and_provider(monkeypatch):
    from src.ml_runtime.category_zeroshot import get_category_centroids, reset_category_centroids_cache
    from src.ml_runtime.slm_runtime import get_pack_category_vectors, reset_slm_cache
    reset_category_centroids_cache()
    reset_slm_cache()
    provider = ToySemanticEmbedder(version_tag="first")
    monkeypatch.setattr("src.ml_runtime.slm_runtime.get_slm_embedder", lambda: provider)
    first_pack, second_pack = _pack(["ENGINE"]), _pack(["SERVICE BRAKES"])
    cc1 = get_category_centroids(first_pack, provider)
    cc2 = get_category_centroids(second_pack, provider)
    cv1 = get_pack_category_vectors(first_pack)
    cv2 = get_pack_category_vectors(second_pack)
    assert cc1.categories != cc2.categories
    assert cv1.categories != cv2.categories
    provider = ToySemanticEmbedder(version_tag="second")
    assert get_pack_category_vectors(second_pack) is not cv2
    assert get_category_centroids(second_pack, provider) is not cc2


def test_semantic_cache_rechecks_expected_sha_without_reset(monkeypatch):
    from src.ml_runtime.embedding_runtime import semantic_embedder
    from src.ml_runtime.embedding_space import ArtifactIntegrityError
    monkeypatch.setenv("FRONTLINE_EMBEDDING_TOY", "1")
    monkeypatch.delenv("FRONTLINE_SEMANTIC_MODEL_SHA256", raising=False)
    reset_embedding_runtime()
    semantic_embedder()
    monkeypatch.setenv("FRONTLINE_SEMANTIC_MODEL_SHA256", "f" * 64)
    # Backfill independently checks the expected checksum, including toy metadata.
    with pytest.raises(ArtifactIntegrityError):
        run_backfill("automotive_nhtsa", ToySemanticEmbedder().version)
    reset_embedding_runtime()


def test_process_provider_tracks_directory_and_settings(monkeypatch, tmp_path):
    from src.ml_runtime import onnx_embedder as runtime
    calls = []
    def provider(directory, **kwargs):
        calls.append(directory)
        return SimpleNamespace(_dir=directory, _intra_threads=kwargs.get("intra_op_threads", 1),
                               _inter_threads=1, _max_batch=kwargs.get("max_batch_size", 32),
                               _artifact_cache_key=runtime.artifact_cache_key(directory))
    runtime.reset_process_onnx_embedder()
    monkeypatch.setattr(runtime, "OnnxSemanticEmbedder", provider)
    monkeypatch.setenv("FRONTLINE_ONNX_INTRA_THREADS", "1")
    a = runtime.get_process_onnx_embedder(tmp_path / "a")
    assert runtime.get_process_onnx_embedder(tmp_path / "a") is a
    b = runtime.get_process_onnx_embedder(tmp_path / "b")
    assert b is not a
    assert runtime.get_process_onnx_embedder(tmp_path / "b", intra_op_threads=2) is not b
    assert len(calls) == 3
    runtime.reset_process_onnx_embedder()


def test_semantic_startup_and_activation_require_active_matching_model(semantic_corpus, monkeypatch):
    from src.ml_runtime.cluster_builds import rebuild_cluster_build, activate_cluster_build, approve_retrieval_scorecard
    from src.ml_runtime.embedding_runtime import validate_startup_config
    from src.ml_runtime.embedding_space import EmbeddingUnavailableError
    pack, version = "automotive_nhtsa", semantic_corpus
    build = rebuild_cluster_build(pack, version, k=2)
    monkeypatch.setenv("FRONTLINE_EMBEDDING_MODE", "semantic")
    monkeypatch.setenv("FRONTLINE_ACTIVE_CLUSTER_BUILD_ID", build["build_id"])
    monkeypatch.setenv("DOMAIN_PACK", pack)
    with pytest.raises(EmbeddingUnavailableError, match="not active"):
        validate_startup_config()
    approve_retrieval_scorecard(pack, embedding_version=version, model_key="wrong-model",
                               dataset_id="fixture", scorecard={"approved": True, "recall": 1, "ndcg": 1})
    with pytest.raises(ValueError, match="approved retrieval scorecard"):
        activate_cluster_build(pack, build["build_id"])
    approve_retrieval_scorecard(pack, embedding_version=version, model_key="toy-semantic-v1",
                               dataset_id="fixture", scorecard={"approved": True, "recall": 1, "ndcg": 1})
    activate_cluster_build(pack, build["build_id"])
    assert validate_startup_config()["ok"]


@pytest.mark.parametrize("argv", [["--iters", "0"], ["--concurrency", "0"], ["--concurrency", "x"], ["--concurrency", "300"]])
def test_benchmark_rejects_invalid_load_before_loading_model(argv):
    from scripts.embedding_benchmark import main
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_benchmark_memory_units_and_missing_model(monkeypatch, tmp_path):
    from scripts import embedding_benchmark as benchmark
    from src.ml_runtime.embedding_space import ArtifactIntegrityError
    monkeypatch.setattr(benchmark.resource, "getrusage", lambda _: SimpleNamespace(ru_maxrss=128 * 1024))
    monkeypatch.setattr(benchmark.platform, "system", lambda: "Linux")
    assert benchmark._rss_mb() == 128
    monkeypatch.setattr(benchmark, "semantic_artifact_dir", lambda: tmp_path)
    with pytest.raises(ArtifactIntegrityError):
        benchmark.main(["--iters", "1", "--concurrency", "1"])
    assert not (tmp_path / "embedding_benchmark.json").exists()
