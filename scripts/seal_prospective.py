"""Human-run snapshot collector. Procedural custody, not enforced no-peeking."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import zipfile

from src.eval.improvement_protocol import digest,write_once
from src.eval.prospective_io import (CUSTODY,MANIFEST,PHASE,load,now,today,safe_id,external_root,atomic_json,manifest_chain,blob)

ROOT=Path(__file__).resolve().parents[1]


def fetch(url,destination):
    with urllib.request.urlopen(url,timeout=120) as response, destination.open("xb") as output:
        while chunk:=response.read(1024*1024):output.write(chunk)


def row_count(path):
    with zipfile.ZipFile(path) as z:
        names=[n for n in z.namelist() if not n.endswith("/")]
        if len(names)!=1: raise ValueError("Expected one NHTSA flat file per ZIP")
        with z.open(names[0]) as stream:return sum(bool(line.strip()) for line in stream)


def seal(args, *, root=ROOT, fetcher=fetch):
    if not args.seal: raise ValueError("--seal is required")
    if not args.confirm_public_data: raise ValueError("--confirm-public-data is required")
    protocol=load(root/PHASE/"protocol.json");window=protocol["prospective"]
    start=date.fromisoformat(args.start);end=date.fromisoformat(args.end)
    if not window["flag_start"]<=start.isoformat()<=end.isoformat()<=window["flag_end"]: raise ValueError("Flag dates outside 2027-2028")
    if today()<end.isoformat(): raise ValueError("Cannot collect a future period")
    custody=external_root(root,args.custody_root,writable=True);sid=safe_id(args.snapshot_id)
    manifest,chain=manifest_chain(root,"HEAD")
    if (root/MANIFEST).read_bytes()!=blob(root,"HEAD",MANIFEST): raise ValueError("Commit prior manifest before collection")
    if manifest["status"] not in ["reserved","collecting"]: raise ValueError("Manifest is already frozen")
    if sid in {s["snapshot_id"] for s in manifest["snapshots"]} or (custody/sid).exists(): raise ValueError("Duplicate snapshot ID")
    lock=root/"data/prospective/.collection.lock"
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        folder=custody/sid;folder.mkdir(exist_ok=False)
        files=[]
        for source in protocol["sources"]:
            if not source["url"].startswith("https://static.nhtsa.gov/"): raise ValueError("Unregistered source host")
            name=source["id"]+".zip";dest=folder/name
            fetcher(source["url"],dest)
            files.append(dict(source_id=source["id"],source_url=source["url"],file=name,sha256=digest(dest),rows=row_count(dest),bytes=dest.stat().st_size))
        snapshot=dict(schema_version=1,snapshot_id=sid,snapshot_date=today(),created_at=now(),flag_start=args.start,flag_end=args.end,files=files)
        write_once(folder/"snapshot.json",snapshot)
        entry={**snapshot,"snapshot_sha256":digest(folder/"snapshot.json")}
        previous=digest(root/MANIFEST)
        updated={**manifest,"status":"collecting","updated_at":now(),"prev_sha256":previous,"snapshots":manifest["snapshots"]+[entry]}
        log=root/"reports/improvement/prospective/collection_log.jsonl";log.parent.mkdir(parents=True,exist_ok=True)
        # Failure after either metadata write is explicit; never reuse the reserved snapshot ID.
        atomic_json(root/MANIFEST,updated)
        record=dict(snapshot_id=sid,snapshot_sha256=entry["snapshot_sha256"],manifest_sha256=digest(root/MANIFEST),prev_sha256=previous,created_at=now(),files=files)
        with log.open("a") as f:f.write(json.dumps(record,sort_keys=True)+"\n");f.flush();os.fsync(f.fileno())
        return record
    finally:
        lock.unlink()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seal",action="store_true");p.add_argument("--confirm-public-data",action="store_true")
    for name in ["custody-root","start","end","snapshot-id"]:p.add_argument("--"+name,required=True)
    args=p.parse_args()
    try:print(json.dumps(seal(args),indent=2))
    except (ValueError,OSError) as exc:p.exit(2,str(exc)+"\n")


if __name__=="__main__":main()
