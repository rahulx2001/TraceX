# Baseline replication model card

Development-only evidence; not a candidate result and not a prospective estimate.

Mode B: Gamma-Poisson baseline; window 13 completed weeks, count >=2,
predictive tail <=0.2, 91-day cooldown. No trainable weights. The tail is a
ranking heuristic, not calibrated probability. No alternative satisfies the
pre-registered conservative selection rule; no complex fit was forced.

Scope: Ford/Honda/Hyundai/Kia/Toyota, MY2015–2024, repaired FUEL SYSTEM.
Model-labelled complaints and recall descriptions remain hypotheses.
Human semantic validation is 0/300. No human accuracy claim is permitted.

Development-only evidence; not a candidate result and not a prospective estimate.

All model training would use only 2015–2020. Both rolling training folds have
zero mature outcomes. Structured numpy logistic is implemented and tested on
synthetic fixtures only; it was not fitted to the real corpus. No sklearn or
scipy installation was needed. No boosting or embedding training was added.

Prospective use is offline replication of a frozen detector, not production
automation. Final inputs must include complete labels with pinned model, prompt
and taxonomy provenance. The harness will not buy labels, silently impute them
or substitute a different classifier if the original provider is unavailable.
Quarterly snapshots and received-date assumptions do not prove real-time
availability. No broader component or make generalization is established.

Development-only evidence; not a candidate result and not a prospective estimate.

Calibration and stronger semantic claims remain unavailable. Procedural
custody is tamper-evident, not access control; public outcomes can be re-fetched.
Any future production use requires independent labels, human review, monitoring,
security review and separate approval. No merge or promotion occurs here.
