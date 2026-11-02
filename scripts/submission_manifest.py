"""Create/verify a commit-pinned source manifest without self hashes or local caches.

Run after the intended source commit. Commit the resulting manifest separately;
its source_commit identifies the source tree, not the manifest's own commit.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "de3c48394675636e3b5b030dfc24ca32c37d8ddd"
OUTPUT = "reports/hackathon/source_manifest.json"
MEDIA = {".mp4", ".webm", ".wav", ".aiff", ".zip", ".duckdb", ".wal"}


def git(*args, root=ROOT):
    return subprocess.check_output(["git", *args], cwd=root)


def included(path):
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts or path == OUTPUT:
        return False
    if p.parts[0] in {".git", ".venv", ".venv-hackathon", "data", "node_modules"}:
        return False
    if "node_modules" in p.parts or "__pycache__" in p.parts or path.startswith("dashboard/dist/"):
        return False
    if p.name == ".env" or p.name.startswith(".env."):
        return p.name in {".env.example", ".env.hackathon.example"}
    if p.suffix in MEDIA or any(token in p.name for token in ("operator_api_key", "session_secret", "supervisor_token")):
        return False
    return True


def create(commit="HEAD", baseline=BASELINE, root=ROOT):
    revision = git("rev-parse", "--verify", commit+"^{commit}", root=root).decode().strip()
    base = git("rev-parse", "--verify", baseline+"^{commit}", root=root).decode().strip()
    git("merge-base", "--is-ancestor", base, revision, root=root)
    records = []
    for raw in git("ls-tree", "-r", "-z", revision, root=root).split(b"\0"):
        if not raw:
            continue
        meta, encoded_path = raw.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        path = encoded_path.decode()
        if kind != "blob" or not included(path):
            continue
        body = git("cat-file", "blob", oid, root=root)
        records.append({"path": path, "mode": mode, "git_blob": oid, "bytes": len(body),
                        "sha256": hashlib.sha256(body).hexdigest()})
    changed = git("diff", "--name-status", "--no-renames", base, revision, root=root).decode().splitlines()
    return {"schema_version": 2, "recorded_at": datetime.now(timezone.utc).isoformat(), "committed": True,
            "base_commit": base, "source_commit": revision, "source_tree": git("rev-parse", revision+"^{tree}", root=root).decode().strip(),
            "scope": "Tracked source/artifacts at source_commit; excludes local credentials, data caches, generated media and this manifest. The imported baseline remains reused work.",
            "manifest_self_excluded": OUTPUT,
            "event_delta": [{"status": line.split("\t", 1)[0], "path": line.split("\t", 1)[1]} for line in changed if included(line.split("\t", 1)[1])],
            "files": records}


def verify(manifest, *, root=ROOT, worktree=False):
    expected = create(manifest["source_commit"], manifest["base_commit"], root)
    assert manifest["files"] == expected["files"], "Committed source inventory/hash differs"
    assert manifest["event_delta"] == expected["event_delta"], "Committed contribution delta differs"
    assert manifest["source_tree"] == expected["source_tree"], "Source tree identity differs"
    if worktree:
        for entry in manifest["files"]:
            path = root/entry["path"]
            body = path.readlink().as_posix().encode() if path.is_symlink() else path.read_bytes()
            assert hashlib.sha256(body).hexdigest() == entry["sha256"], f"Working source changed: {entry['path']}"
    return {"ok": True, "source_commit": manifest["source_commit"], "files": len(manifest["files"]),
            "event_delta_files": len(manifest["event_delta"]), "worktree_checked": worktree}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("create", "verify"))
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--baseline", default=BASELINE)
    parser.add_argument("--manifest", type=Path, default=ROOT/OUTPUT)
    parser.add_argument("--worktree", action="store_true")
    args = parser.parse_args()
    if args.phase == "create":
        body = create(args.commit, args.baseline)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(body, indent=2)+"\n")
        print(json.dumps({"manifest": str(args.manifest), "source_commit": body["source_commit"], "files": len(body["files"])}))
    else:
        print(json.dumps(verify(json.loads(args.manifest.read_text()), worktree=args.worktree)))


if __name__ == "__main__":
    main()
