from hplc_engine.calculations import (
    calculate_k,
    calculate_rs,
    calculate_alpha,
    calculate_n,
    calculate_hetp,
    classify_peak_count,
    classify_runtime,
    classify_rs_overall,
    build_composite_key,
)


def test_calculate_k():
    assert calculate_k(5, 1) == 4


def test_calculate_rs():
    assert calculate_rs(3, 5, 0.5, 0.5) == 4


def test_calculate_alpha():
    assert calculate_alpha(2, 4) == 2


def test_calculate_n():
    assert round(calculate_n(10, 0.5), 3) == 2216.0


def test_calculate_hetp():
    assert calculate_hetp(150, 10000) == 0.015


def test_classify_peak_count():
    assert classify_peak_count(7) == "7"
    assert classify_peak_count(6) == "<7"
    assert classify_peak_count(8) == ">7"


def test_classify_runtime():
    assert classify_runtime(19.9, 20) == "<20"
    assert classify_runtime(20, 20) == ">20"


def test_classify_rs_overall():
    assert classify_rs_overall([1.7, 1.8]) == "PASS"
    assert classify_rs_overall([1.45, 1.8]) == "MARGINAL"
    assert classify_rs_overall([1.2, 1.8]) == "FAIL_SINGLE"
    assert classify_rs_overall([1.2, 1.1]) == "FAIL_MULTI"
    assert classify_rs_overall([0.7, 1.8]) == "FAIL_SEVERE"
    assert classify_rs_overall([None, None]) == "N/A"


def test_build_composite_key():
    result = build_composite_key(
        observed_peak_count=7,
        total_run_time=18,
        rs_values=[1.7, 1.8],
    )
    assert result["composite_key"] == "7|<20|PASS"
