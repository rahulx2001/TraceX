"""The defect pipeline must be runnable from the inputs it documents."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from scripts.defect_classify import main as classify_main
from scripts.defect_prepare_inputs import prepare
from scripts.ingest_nhtsa import _FLAT_FIELDS
from scripts.ingest_recalls import FLAT_RCL_FIELDS
from src.config import REPO_ROOT


def _flat_line(fields: list[str], values: dict[str, str]) -> str:
    row = [values.get(name, "") for name in fields]
    return "\t".join(row)


def _complaint(odino: str, text: str, component: str = "BRAKES") -> str:
    return _flat_line(_FLAT_FIELDS, {
        "CMPLID": f"c{odino}",
        "ODINO": odino,
        "MAKETXT": "HONDA",
        "MODELTXT": "CIVIC",
        "YEARTXT": "2019",
        "COMPDESC": component,
        "DATEA": "20190115",
        "CDESCR": text,
    })


def _recall(campno: str, desc: str) -> str:
    return _flat_line(FLAT_RCL_FIELDS, {
        "CAMPNO": campno,
        "MAKETXT": "HONDA",
        "MODELTXT": "CIVIC",
        "YEARTXT": "2019",
        "COMPNAME": "BRAKES",
        "DESC_DEFECT": desc,
        "RCDATE": "20190301",
    })


def _zip(path: Path, member: str, lines: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(member, "\n".join(lines) + "\n")
    return path


def _fixtures(tmp_path: Path) -> tuple[Path, Path]:
    complaints = _zip(tmp_path / "FLAT_CMPL.zip", "CMPL.txt", [
        _complaint("1", "short"),
        _complaint("1", "a longer braking noise narrative"),  # duplicate key: longest wins
        _complaint("2", "brake pedal feels soft", component="BRAKES"),
        _flat_line(_FLAT_FIELDS, {"ODINO": "3", "CDESCR": "outside window", "DATEA": "20100101"}),
    ])
    recalls = _zip(tmp_path / "FLAT_RCL.zip", "RCL.txt", [
        _recall("R1", "brake hose may leak"),
        _recall("R1", "brake hose may leak"),  # duplicate identity: keep one
        _recall("R2", "caliper piston may seize"),
    ])
    return complaints, recalls


def test_prepare_writes_parquet_the_classifier_can_read(tmp_path, capsys):
    complaints_zip, recalls_zip = _fixtures(tmp_path)
    out = tmp_path / "defect"
    manifest = prepare(out_dir=out, complaints_zip=str(complaints_zip), recalls_zip=str(recalls_zip))

    complaints = pd.read_parquet(out / "complaints.parquet")
    recalls = pd.read_parquet(out / "recall_descriptions.parquet")
    assert list(complaints.columns) == [
        "datea", "odino", "cmplid", "make", "model", "year", "component", "text",
    ]
    assert list(recalls.columns) == [
        "campno", "component", "compdesc", "desc_defect", "rcdate", "make", "model", "year",
    ]
    # Three distinct ODINO|component keys, but ODINO 1 appears twice: the
    # longer narrative must be kept, and the out-of-window row dropped.
    assert len(complaints) == 2
    kept = complaints[complaints["odino"] == "1"].iloc[0]
    assert kept["text"] == "a longer braking noise narrative"
    assert set(complaints["datea"]) == {"2019-01-15"}
    # Duplicate campaign/component/description identity collapses to one row.
    assert len(recalls) == 2
    recall = recalls[recalls["campno"] == "R1"].iloc[0]
    assert recall["rcdate"] == "2019-03-01"

    assert manifest["complaints"]["rows"] == 2
    assert manifest["complaints"]["tally"]["collapsed"] == 1
    assert manifest["recalls"]["tally"]["collapsed"] == 1
    manifest_on_disk = json.loads((out / "defect_input_manifest.json").read_text())
    assert manifest_on_disk["sources"]["complaints"]["sha256"]

    # The actual classifier dry run reads these files without a model call.
    rc = classify_main([
        "--dry-run", "--limit", "1", "--input", "both",
        "--complaints", str(out / "complaints.parquet"),
        "--recalls", str(out / "recall_descriptions.parquet"),
        "--taxonomy", str(REPO_ROOT / "reports/defect/taxonomy.json"),
        "--out-dir", str(tmp_path / "estimate"),
    ])
    assert rc == 0
    printed = capsys.readouterr().out
    assert "records_estimated" in printed
    assert "no network call" in printed


def test_missing_input_names_the_preparation_command(tmp_path):
    with pytest.raises(SystemExit) as exc:
        classify_main([
            "--dry-run", "--input", "complaints",
            "--complaints", str(tmp_path / "absent.parquet"),
            "--out-dir", str(tmp_path / "estimate"),
        ])
    assert exc.value.code != 0
    message = str(exc.value.code)
    assert "scripts.defect_prepare_inputs" in message
    assert "absent.parquet" in message
