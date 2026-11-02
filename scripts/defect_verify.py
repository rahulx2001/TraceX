"""Replay the already-recorded repair without tuning or creating a new result."""
import json

from scripts.ai_oos_backtest import canonical_hash
from scripts.defect_prediction_eval import inputs, compare, without_known_recalls
from scripts.defect_repair import OUT


def main():
    p, c, r, hashes = inputs()
    frozen = json.loads((OUT / "prediction_config.json").read_text())
    saved = json.loads((OUT / "prediction_results.json").read_text())
    if canonical_hash(frozen['body']) != frozen['sha256'] or saved['config_sha256'] != frozen['sha256']:
        raise ValueError('Config/result hash mismatch')
    if hashes != frozen['body']['hashes']:
        raise ValueError('Input or implementation hashes changed since freezing')
    start, end = p['evaluation_window']
    for name, frame in [('all_reports', c), ('excluding_explicit_recall_reports', without_known_recalls(c))]:
        actual = compare(frame, r, frozen['body']['config'], start, end)
        if actual != saved[name]:
            raise ValueError(f'Replay differs: {name}')
        print(f'{name}: exact replay match, including all 100 random draws')


if __name__ == '__main__':
    main()
