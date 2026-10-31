"""Local research baselines; never loaded by the production detector."""
from __future__ import annotations

import numpy as np
from src.eval.improvement_protocol import require_disjoint


def binary_model(kind, seed):
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if kind == "logistic":
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.,max_iter=1000,random_state=seed))
    if kind == "gradient_boosting":
        return GradientBoostingClassifier(n_estimators=50,max_depth=2,min_samples_leaf=5,learning_rate=.05,random_state=seed)
    raise ValueError("Unknown model")


def text_model(seed):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    return make_pipeline(TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True,min_df=1,max_features=20000),
                         LogisticRegression(C=1.,max_iter=1000,class_weight="balanced",random_state=seed))


def embedding_model(seed):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=1.,max_iter=1000,class_weight="balanced",random_state=seed)


def fit_calibrator(scores, y, *, method, fit_ids, calibration_ids, evaluation_ids):
    """Fit on unique calibration examples, disjoint from fitting and evaluation.

    Each calibration identifier corresponds to one score/outcome row. Callers
    must also enforce campaign/time-group separation before constructing rows.
    """
    calibration_ids=list(calibration_ids)
    require_disjoint(fit_ids,calibration_ids,evaluation_ids)
    scores=np.asarray(scores,dtype=float); y=np.asarray(y)
    if scores.ndim!=1 or y.ndim!=1 or scores.shape!=y.shape or not np.isfinite(scores).all() or not np.isin(y,[0,1]).all():
        raise ValueError("Invalid calibration data")
    if len(calibration_ids)!=len(y) or len(set(calibration_ids))!=len(y):
        raise ValueError("One unique calibration identity is required per outcome")
    if len(y)<10 or min(int(y.sum()),int((1-y).sum()))<2:
        raise ValueError("Insufficient independent calibration support (10 rows and 2 of each outcome required)")
    if method == "platt":
        from sklearn.linear_model import LogisticRegression
        model=LogisticRegression(C=1.,max_iter=1000,random_state=17).fit(scores.reshape(-1,1),y)
        return lambda x:model.predict_proba(np.asarray(x).reshape(-1,1))[:,1]
    if method == "isotonic":
        if len(y)<100:raise ValueError("Isotonic requires at least 100 calibration outcomes")
        from sklearn.isotonic import IsotonicRegression
        model=IsotonicRegression(y_min=0,y_max=1,out_of_bounds="clip").fit(scores,y)
        return model.predict
    raise ValueError("Unknown calibration method")


def choose_operating_point(rows, *, required_precision=.8, required_recall=.7):
    """Choose from calibration/development rows only; never fall back to a failed gate."""
    if any(r.get("split") not in {"calibration","development_validation"} for r in rows):
        raise ValueError("Operating points cannot be selected on test results")
    qualified=[r for r in rows if r["precision"] is not None and r["recall"] is not None
               and r["precision"]>=required_precision and r["recall"]>=required_recall and r["mature_alerts"]>=10]
    if not qualified:return None
    return max(qualified,key=lambda r:(r["utility"],r["precision"],r["recall"],r["threshold"]))
