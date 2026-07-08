from hplc_engine.rules_master import fire_master_rule


def test_fire_master_rule_pass():
    rule = fire_master_rule("7|<20|PASS")
    assert rule["rule_id"] == 1


def test_fire_master_rule_missing():
    rule = fire_master_rule("missing-key")
    assert rule["rule_id"] == "NO_MATCH"
