"""Append-only run provenance and checks separating development from opened tests."""
from __future__ import annotations

import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

SEEDS = [17,29,43,71,101]
RANDOM_SEEDS = list(range(2026103100,2026103200))
DEVELOPMENT_END = "2020-12-31"
FIELDS = ["run_id","exact_command","cwd","config_hash","config_hash_definition","data_hash","data_hash_definition",
          "code_commit","seed","split","status","exit_code","started_at","finished_at","log"]


def digest(path):
    with Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()


def canonical(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def write_once(path, body):
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x") as f:json.dump(body,f,indent=2,allow_nan=False);f.write("\n")


def check_development(frame, date_column):
    if frame[date_column].isna().any() or not frame[date_column].astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        raise ValueError("Every development row requires a valid ISO date")
    for day in frame[date_column]:date.fromisoformat(day)
    if not frame[date_column].between("2015-01-01",DEVELOPMENT_END).all():
        raise ValueError("Opened 2021-2024/2025 tests and newer outcomes cannot enter development")


def require_disjoint(fit_ids, calibration_ids, evaluation_ids):
    sets = [set(x) for x in (fit_ids,calibration_ids,evaluation_ids)]
    if any(sets[i]&sets[j] for i in range(3) for j in range(i)):
        raise ValueError("Fitting, calibration and evaluation identities overlap")


def require_final_test(manifest, *, today=None):
    today = today or date.today().isoformat()
    if manifest.get("status") != "data_frozen" or not manifest.get("data_hashes"):
        raise ValueError("Prospective reservation is not a frozen, available test dataset")
    if today < manifest["outcome_end"]:
        raise ValueError("Test follow-up is incomplete")
    if not manifest.get("untouched_attestation"):
        raise ValueError("Untouched test attestation is required")


class Run:
    """Exclusive run reservation precedes execution; failures are retained."""
    def __init__(self, root, run_id, config, input_paths, command, *, seed=None, split="development"):
        self.root=Path(root);self.run_id=run_id
        if not run_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in run_id):
            raise ValueError("Unsafe run ID")
        self.path=self.root/"reports/improvement/runs"/run_id
        self.path.mkdir(parents=True,exist_ok=False)
        commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=self.root,text=True).strip()
        code_files=[p for directory in ["src","scripts"] for p in (self.root/directory).rglob("*.py")]
        inputs={str(Path(p).relative_to(self.root)):digest(p) for p in input_paths}
        self.meta=dict(run_id=run_id,config=config,config_hash=canonical(config),input_hashes=inputs,data_hash=canonical(inputs),
                       code_commit=commit,code_hash=canonical({str(p.relative_to(self.root)):digest(p) for p in sorted(code_files)}),
                       seed=seed,split=split,exact_command=command,started_at=datetime.now(timezone.utc).isoformat())
        write_once(self.path/"started.json",self.meta)

    def finish(self,status, *, exit_code=0):
        end=datetime.now(timezone.utc).isoformat()
        write_once(self.path/"finished.json",dict(status=status,exit_code=exit_code,finished_at=end))
        row={k:self.meta.get(k,"") for k in FIELDS}
        row.update(cwd=str(self.root),config_hash_definition="canonical config JSON",data_hash_definition="canonical input-path/hash mapping",
                   status=status,exit_code=exit_code,finished_at=end,log=str(self.path.relative_to(self.root)))
        with (self.root/"reports/improvement/experiments.csv").open("a",newline="") as f:
            csv.DictWriter(f,fieldnames=FIELDS).writerow(row)
