"""Issue names must retain pack identity and never change case counts."""
from src.data.warehouse import domain_con, ops_con
from src.frontline.wallboard import build_wallboard


def add_case(cid, pack, cluster, category, severity="Medium", status="open"):
    with ops_con() as con:
        con.execute(
            """INSERT INTO cases (case_id, interaction_id, pack_id, created_at,
               category, severity, severity_source, priority, cluster_match_id, status)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, 'rules', 2, ?, ?)""",
            [cid, "int_" + cid, pack, category, severity, cluster, status],
        )


def test_names_are_pack_scoped_and_counts_keep_followups(reset_ops_db, seed_automotive_pack):
    # Same numeric ID in two packs must retain distinct names and volumes.
    with domain_con("finance_cfpb", read_only=False) as con:
        con.execute("INSERT INTO clusters (cluster_id, pack_id, category) VALUES (14, 'finance_cfpb', 'Credit reporting')")
    add_case("auto1", "automotive_nhtsa", 14, "Other", "High")
    add_case("auto2", "automotive_nhtsa", 14, "Other", "Low", "pending_followup")
    add_case("auto3", "automotive_nhtsa", 14, "Other", "Critical", "closed")
    add_case("fin1", "finance_cfpb", 14, "Other")
    groups = build_wallboard()["top_risk_clusters"]
    assert [(g["pack_id"], g["open_cases"]) for g in groups] == [("automotive_nhtsa", 2), ("finance_cfpb", 1)]
    assert groups[0]["category"] == "SERVICE BRAKES"
    assert groups[0]["max_severity"] == "High"
    assert groups[1]["category"] == "Credit reporting"
    assert len(build_wallboard(pack_id="automotive_nhtsa")["top_risk_clusters"]) == 1


def test_missing_domain_keeps_case_category_and_uncategorized_group(reset_ops_db, monkeypatch):
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("No domain warehouse")

    monkeypatch.setattr("src.frontline.wallboard.domain_con", unavailable)
    add_case("one", "automotive_nhtsa", 99, "SUSPENSION", "Critical")
    add_case("two", "automotive_nhtsa", 99, "SUSPENSION", "Low")
    add_case("three", "automotive_nhtsa", 100, None)
    groups = build_wallboard()["top_risk_clusters"]
    assert groups[0]["category"] == "SUSPENSION"
    assert groups[0]["open_cases"] == 2
    assert groups[0]["max_severity"] == "Critical"
    assert groups[1]["category"] is None
