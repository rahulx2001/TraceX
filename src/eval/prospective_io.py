"""Procedural custody and tamper evidence. This is not access control."""
from __future__ import annotations

from datetime import datetime, timezone, date
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

from src.eval.improvement_protocol import digest, write_once

MANIFEST = "data/prospective/manifest.json"
CUSTODY = "data/prospective/custody.json"
PHASE = "reports/improvement/phase1"


def now(): return datetime.now(timezone.utc).isoformat()
def today(): return datetime.now(timezone.utc).date().isoformat()
def load(path): return json.loads(Path(path).read_text())
def git(root, *args): return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
def blob(root, ref, path): return subprocess.check_output(["git","show",f"{ref}:{path}"],cwd=root)


def safe_id(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}",value): raise ValueError("Unsafe identifier")
    return value


def external_root(root, value, *, writable=False):
    raw=Path(value).expanduser().absolute()
    if any(p.is_symlink() for p in [raw,*raw.parents]): raise ValueError("Symlinked custody root")
    path=raw.resolve(); root=Path(root).resolve()
    worktrees=[Path(line[9:]).resolve() for line in git(root,"worktree","list","--porcelain").splitlines() if line.startswith("worktree ")]
    if any(path==tree or tree in path.parents for tree in [root,*worktrees]):
        raise ValueError("Custody root must be outside repository worktrees")
    if not path.is_dir(): raise ValueError("Custody root is not a directory")
    marker=path/".rca-custody"
    if marker.is_symlink() or not marker.is_file(): raise ValueError("Missing custody marker")
    expected=load(root/CUSTODY)["volume_marker_uuid"]
    uuid.UUID(expected)
    if marker.read_text().strip()!=expected: raise ValueError("Custody marker UUID mismatch")
    if writable and (not os.access(path,os.W_OK) or not path.stat().st_mode&0o222):
        raise ValueError("Custody root is not writable")
    return path


def external_file(custody, relative):
    rel=Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts: raise ValueError("Unsafe external file name")
    p=custody/rel
    if any(x.is_symlink() for x in [p,*p.parents] if x!=custody.parent): raise ValueError("Symlinked custody file")
    if custody.resolve() not in p.resolve().parents or not p.is_file(): raise ValueError("Missing external file")
    return p


def atomic_json(path, value):
    """Same-directory replacement; original committed manifest remains in git."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=".manifest-",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"w") as f:
            json.dump(value,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def manifest_chain(root, ref):
    import hashlib
    commits=git(root,"rev-list","--reverse",ref,"--",MANIFEST).splitlines()
    if not commits: raise ValueError("No committed manifest history")
    previous=None;last=None;records=[]
    protocol=load(root/PHASE/"protocol.json")
    expected={k:protocol["prospective"][k] for k in ["flag_start","flag_end","outcome_cutoff"]}
    for commit in commits:
        raw=blob(root,commit,MANIFEST);m=json.loads(raw)
        if m["prev_sha256"]!=previous: raise ValueError("Broken manifest hash chain")
        if m["window"]!=expected or m["minimum_campaigns"]!=protocol["prospective"]["min_campaigns"]:
            raise ValueError("Manifest changed registered window or sample minimum")
        if last:
            if m["snapshots"][:len(last["snapshots"])]!=last["snapshots"]: raise ValueError("Snapshot history was rewritten")
            if last["status"]=="data_frozen" and m["status"]!="data_frozen": raise ValueError("Frozen manifest reopened")
        ids=[s["snapshot_id"] for s in m["snapshots"]]
        if len(ids)!=len(set(ids)): raise ValueError("Duplicate snapshot identity")
        previous=hashlib.sha256(raw).hexdigest();last=m
        records.append(dict(commit=commit,sha256=previous))
    if blob(root,ref,MANIFEST)!=blob(root,commits[-1],MANIFEST): raise ValueError("Manifest tip mismatch")
    return last,records


def verify_freeze(root):
    h=load(root/PHASE/"FREEZE_HASHES.json")
    fpath=root/PHASE/"freeze_manifest.json"
    if digest(fpath)!=h["freeze_manifest_sha256"]: raise ValueError("Frozen manifest hash mismatch")
    f=load(fpath)
    named={"preregistration_sha256":PHASE+"/PREREGISTRATION.md","protocol_sha256":PHASE+"/protocol.json",
           "collector_sha256":"scripts/seal_prospective.py","analysis_script_sha256":"scripts/final_prospective_eval.py",
           "candidate_sha256":f["candidate"]["path"]}
    for key,path in named.items():
        if digest(root/path)!=h[key]: raise ValueError("Frozen artifact hash mismatch: "+path)
    for path,expected in f["code"]["files"].items():
        if digest(root/path)!=expected: raise ValueError("Frozen artifact hash mismatch: "+path)
    if git(root,"rev-parse",h["freeze_commit"]+"^{tree}")!=h["freeze_tree"]: raise ValueError("Frozen tree mismatch")
    tag=git(root,"rev-parse",f["freeze_tag"]+"^{commit}")
    # Pin the hash index itself to the immutable annotated tag, not editable metadata.
    if blob(root,tag,PHASE+"/FREEZE_HASHES.json")!=(root/PHASE/"FREEZE_HASHES.json").read_bytes():
        raise ValueError("Freeze hash index differs from tag")
    for path,expected in f["code"]["files"].items():
        import hashlib
        if hashlib.sha256(blob(root,tag,path)).hexdigest()!=expected: raise ValueError("Tag/frozen file mismatch")
    return f,h,tag


def check_attestation(root, ref, manifest):
    import hashlib
    a=manifest.get("untouched_attestation")
    if not isinstance(a,dict) or a.get("custodian")!="Rahul Kumar Singh" or a.get("no_outcomes_inspected_during_development") is not True:
        raise ValueError("Missing committed untouched attestation")
    if a.get("type") not in ["self-attestation","signed"] or not a.get("attested_at"):
        raise ValueError("Incomplete attestation")
    path=Path(a.get("document_path",""))
    if path.is_absolute() or ".." in path.parts or not path.parts: raise ValueError("Unsafe attestation path")
    raw=blob(root,ref,path.as_posix())
    if hashlib.sha256(raw).hexdigest()!=a.get("sha256"): raise ValueError("Attestation hash mismatch")
    return a


def check_collection_log(root,ref,manifest,chain):
    raw=blob(root,ref,"reports/improvement/prospective/collection_log.jsonl")
    records=[json.loads(line) for line in raw.splitlines() if line.strip()]
    ids=[r["snapshot_id"] for r in records]
    if len(ids)!=len(set(ids)) or set(ids)!={s["snapshot_id"] for s in manifest["snapshots"]}:
        raise ValueError("Collection log does not match snapshot inventory")
    hashes={r["sha256"] for r in chain}
    for snapshot in manifest["snapshots"]:
        record=next(r for r in records if r["snapshot_id"]==snapshot["snapshot_id"])
        if record["snapshot_sha256"]!=snapshot["snapshot_sha256"] or record["files"]!=snapshot["files"] or record["manifest_sha256"] not in hashes or record["prev_sha256"] not in hashes:
            raise ValueError("Collection log hash mismatch")
