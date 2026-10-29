"""The defect exporter must stay readable by the accuracy evaluator."""

from __future__ import annotations

import pandas as pd

from scripts.defect_accuracy import load_classifications
from scripts.defect_classify import PROMPT_VERSION, export, load_recalls, open_cache


def test_export_round_trip_keeps_provenance(tmp_path):
    con = open_cache(tmp_path / "classifications.sqlite")
    con.execute(
        """
        INSERT INTO classifications (
            record_id, input_type, model, prompt_version, taxonomy_sha256,
            component, label_id, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ["r1", "complaint", "muse-spark-1.3", PROMPT_VERSION, "abc", "BRAKES", "d1", "ok", "2026-10-28T00:00:00Z"],
    )
    con.commit()
    export(
        con,
        model="muse-spark-1.3",
        taxonomy_sha="abc",
        complaints_in=[{
            "record_id": "r1", "input_type": "complaint", "odino": "1", "cmplid": "2",
            "datea": "2020-01-01", "make": "HONDA", "vehicle_model": "CIVIC", "year": 2019,
            "component": "BRAKES", "text": "noise",
        }],
        recalls_in=[],
        out_dir=tmp_path,
    )
    loaded = load_classifications(tmp_path / "classifications.parquet")
    row = loaded.iloc[0]
    assert row["model"] == "muse-spark-1.3"
    assert row["prompt_version"] == PROMPT_VERSION
    assert row["taxonomy_sha256"] == "abc"
    assert row["label_id"] == "d1"

    empty = tmp_path / "empty"
    export(con, model="muse-spark-1.3", taxonomy_sha="missing", complaints_in=[], recalls_in=[], out_dir=empty)
    blank = pd.read_parquet(empty / "classifications.parquet")
    assert {"model", "prompt_version", "taxonomy_sha256"} <= set(blank.columns)


def test_recall_records_keep_backtest_join_keys(tmp_path):
    # The backtest joins recall labels on campno/component/desc_defect.
    pd.DataFrame([{
        "campno": "C1", "component": "FUEL SYSTEM", "desc_defect": "DEFECT TEXT HERE",
        "rcdate": "2021-03-04", "make": "HONDA", "model": "CIVIC", "year": 2020,
    }]).to_parquet(tmp_path / "recalls.parquet")
    recs = load_recalls(tmp_path / "recalls.parquet")
    assert recs[0]["campno"] == "C1"
    assert recs[0]["desc_defect"] == "DEFECT TEXT HERE"
