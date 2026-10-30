"""Create a small allow-listed replay bundle; no raw inputs, weights or credentials."""
import argparse
import json
from pathlib import Path
import zipfile

from scripts.public_replay import ROOT, INDEX, validate


def package(destination: Path):
    validate()
    index = json.loads((ROOT/INDEX).read_text())
    paths = [INDEX, "reports/hackathon/CLAIM_INDEX.md", "scripts/public_replay.py", "LICENSE"]
    paths += [a["path"] for a in index["artifacts"]]
    destination.parent.mkdir(parents=True, exist_ok=True)
    readme = ("# TraceX public saved-evidence replay\n\n"
              "Run `python -m scripts.public_replay` here with Python 3.10+. Only the standard library is needed.\n\n"
              "This verifies saved-artifact hashes, denominators and quotation spans. It does not rerun models, "
              "the full detector experiment or a human study. The saved source/citation examples are fictional "
              "integration data; the historical counts retain their original scope. No API credit is used.\n\n"
              "Full source: https://github.com/rahulx2001/TraceX\n")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", readme)
        for path in sorted(set(paths)):
            assert path not in {".env", "data"} and ".." not in Path(path).parts
            archive.write(ROOT/path, path)
    return {"bundle": str(destination), "bytes": destination.stat().st_size,
            "files": len(set(paths))+1, "model_calls": 0, "private_caches_included": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"reports/hackathon/public_replay/TraceX-public-replay.zip")
    args = parser.parse_args()
    print(json.dumps(package(args.output), indent=2))


if __name__ == "__main__":
    main()
