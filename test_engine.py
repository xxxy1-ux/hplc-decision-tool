import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hplc_engine import PeakData, analyse_run, calculate_parameters, determine_lever_state
from rules import lookup_master_rule, lookup_resolution_rule


def make_peaks():
    rts = [0.8, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    widths = [0.08, 0.10, 0.12, 0.13, 0.12, 0.15, 0.16]
    return [PeakData(i, label, retention_time=rts[i], area=1000, height=100, usp_width=widths[i], tailing_factor=1.1, signal_to_noise=100) for i, label in enumerate(["Uracil", "C1", "C2", "C3", "C4", "C5", "C6"])]


def test_calculation_pass():
    params = calculate_parameters(make_peaks(), void_time=0.8, column_length=150, rs_spec=1.4)
    assert params["retentionFactors"][0]["k"] == 1.5
    assert params["rsMinStatus"] == "PASS"
    assert params["averageN"] is not None


def test_master_lookup_exact_and_generic_fail():
    rule, key, duplicate = lookup_master_rule("7", "<20", "FAIL_SINGLE")
    assert rule.rule_id == 2
    assert key == "7|<20|FAIL_SINGLE"
    rule, key, duplicate = lookup_master_rule("<7", "<20", "FAIL_SINGLE")
    assert rule.rule_id == 7
    assert key == "<7|<20|FAIL"


def test_extra_peak_duplicate_guidance_preserved():
    rule, key, duplicate = lookup_master_rule(">7", "<20", "PASS")
    assert rule.rule_id == 10
    assert key == ">7|<20|N/A"
    assert duplicate and duplicate[0].rule_id == 18


def test_resolution_subrule_lookup():
    rule = lookup_resolution_rule("SEVERE", "LOW", "ADEQUATE")
    assert rule.rule_id == 1
    rule = lookup_resolution_rule("ANY", "LATE_HIGH", "ANY")
    assert rule.rule_id == 6


def test_lever_states():
    assert determine_lever_state(False, False, False, False).lever_state == "L1"
    assert determine_lever_state(True, False, False, False).lever_state == "L2"
    assert determine_lever_state(False, False, False, True).lever_state == "L6"


def test_full_analysis_fires_pass_rule():
    payload = {
        "method_name": "test",
        "run_time_spec": 20,
        "rs_spec": 1.4,
        "observed_peak_count": 7,
        "total_run_time": 19.5,
        "void_time": 0.8,
        "column_length": 150,
        "peaks": [p.__dict__ for p in make_peaks()],
        "lever_history": {},
    }
    result = analyse_run(payload)
    assert result["rule"]["rule_id"] == 1
    assert result["lookupKey"] == "7|<20|PASS"
