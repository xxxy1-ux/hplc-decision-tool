"""
Core chromatographic calculations.

The functions are intentionally simple and deterministic.
They do not call AI and do not depend on frontend JavaScript.
"""

from __future__ import annotations

from typing import Any


def to_float(value: Any) -> float | None:
    """Convert form input to float. Empty or invalid values become None."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def calculate_k(retention_time: float | None, void_time: float | None) -> float | None:
    """Retention factor: k = (tR - t0) / t0."""
    if retention_time is None or void_time in (None, 0):
        return None
    return (retention_time - void_time) / void_time


def calculate_rs(
    tr1: float | None,
    tr2: float | None,
    w1: float | None,
    w2: float | None,
) -> float | None:
    """Resolution: Rs = 2(tR2 - tR1) / (w1 + w2)."""
    if None in (tr1, tr2, w1, w2):
        return None
    denominator = w1 + w2
    if denominator == 0:
        return None
    return 2 * (tr2 - tr1) / denominator


def calculate_alpha(k1: float | None, k2: float | None) -> float | None:
    """Selectivity: alpha = larger k / smaller k."""
    if k1 is None or k2 is None:
        return None
    small = min(k1, k2)
    large = max(k1, k2)
    if small == 0:
        return None
    return large / small


def calculate_n(retention_time: float | None, width_half_height: float | None) -> float | None:
    """Efficiency: N = 5.54 * (tR / W_half_height)^2."""
    if retention_time is None or width_half_height in (None, 0):
        return None
    return 5.54 * (retention_time / width_half_height) ** 2


def calculate_hetp(column_length: float | None, n_value: float | None) -> float | None:
    """HETP = column length / N."""
    if column_length is None or n_value in (None, 0):
        return None
    return column_length / n_value


def status_k(k: float | None) -> str:
    if k is None:
        return ""
    if k < 1:
        return "LOW"
    if k <= 20:
        return "OK"
    return "HIGH"


def status_rs(rs: float | None, rs_spec: float = 1.4) -> str:
    if rs is None:
        return ""
    if rs >= rs_spec:
        return "PASS" if rs >= 1.6 else "MARGINAL"
    return "FAIL"


def status_alpha(alpha: float | None) -> str:
    if alpha is None:
        return ""
    if alpha >= 1.1:
        return "GOOD"
    if alpha >= 1.05:
        return "MARGINAL"
    return "POOR"


def status_n(n_value: float | None) -> str:
    if n_value is None:
        return ""
    if n_value >= 10000:
        return "GOOD"
    if n_value >= 5000:
        return "ADEQUATE"
    return "LOW"


def status_hetp(hetp: float | None) -> str:
    if hetp is None:
        return ""
    if hetp <= 0.02:
        return "EXCELLENT"
    if hetp <= 0.05:
        return "GOOD"
    return "HIGH"


def classify_peak_count(observed_peak_count: int | None) -> str:
    if observed_peak_count is None:
        return ""
    if observed_peak_count == 7:
        return "7"
    if observed_peak_count < 7:
        return "<7"
    return ">7"


def classify_runtime(total_run_time: float | None, run_time_spec: float = 20) -> str:
    if total_run_time is None:
        return ""
    return "<20" if total_run_time < run_time_spec else ">20"


def classify_rs_overall(rs_values: list[float | None], rs_spec: float = 1.4) -> str:
    valid_rs = [value for value in rs_values if value is not None]
    if not valid_rs:
        return "N/A"

    rs_min = min(valid_rs)
    fail_count = sum(1 for value in valid_rs if value < rs_spec)

    if rs_min >= rs_spec:
        has_marginal = any(rs_spec <= value < 1.6 for value in valid_rs)
        return "MARGINAL" if has_marginal else "PASS"

    if rs_min < 0.8:
        return "FAIL_SEVERE"

    return "FAIL_MULTI" if fail_count > 1 else "FAIL_SINGLE"


def build_composite_key(
    observed_peak_count: int | None,
    total_run_time: float | None,
    rs_values: list[float | None],
    run_time_spec: float = 20,
    rs_spec: float = 1.4,
) -> dict[str, str]:
    """
    Build the Lookup_Master composite key.

    The original matrix uses detailed FAIL_SINGLE / FAIL_MULTI / FAIL_SEVERE for
    some 7-peak short-runtime cases, but generic FAIL for some other paths.
    This function normalises those cases so the rule dictionary can fire.
    """
    peak_cat = classify_peak_count(observed_peak_count)
    runtime_cat = classify_runtime(total_run_time, run_time_spec)

    if peak_cat == ">7":
        rs_cat = "N/A"
    else:
        rs_cat = classify_rs_overall(rs_values, rs_spec)

    lookup_rs_cat = rs_cat

    # Matrix has generic FAIL for these cases.
    if rs_cat.startswith("FAIL"):
        if (peak_cat == "7" and runtime_cat == ">20") or peak_cat == "<7":
            lookup_rs_cat = "FAIL"

    composite_key = f"{peak_cat}|{runtime_cat}|{lookup_rs_cat}"

    return {
        "peak_cat": peak_cat,
        "runtime_cat": runtime_cat,
        "rs_cat": rs_cat,
        "lookup_rs_cat": lookup_rs_cat,
        "composite_key": composite_key,
    }


def analyse_peak_data(form_data: dict[str, Any]) -> dict[str, Any]:
    """
    Convert HTML form data into calculated chromatographic outputs.
    Expected peak labels:
    uracil, c1, c2, c3, c4, c5, c6
    """
    run_time_spec = to_float(form_data.get("run_time_spec")) or 20
    rs_spec = to_float(form_data.get("rs_spec")) or 1.4
    total_run_time = to_float(form_data.get("total_run_time"))
    void_time = to_float(form_data.get("void_time"))
    column_length = to_float(form_data.get("column_length"))

    observed_peak_count_raw = to_float(form_data.get("observed_peak_count"))
    observed_peak_count = int(observed_peak_count_raw) if observed_peak_count_raw is not None else None

    labels = ["uracil", "c1", "c2", "c3", "c4", "c5", "c6"]

    peaks = []
    for label in labels:
        tr = to_float(form_data.get(f"{label}_tr"))
        usp_width = to_float(form_data.get(f"{label}_usp_width"))
        half_width = to_float(form_data.get(f"{label}_half_width"))

        k_value = None if label == "uracil" else calculate_k(tr, void_time)
        n_value = calculate_n(tr, half_width)
        hetp_value = calculate_hetp(column_length, n_value)

        peaks.append(
            {
                "label": label.upper(),
                "tr": tr,
                "usp_width": usp_width,
                "half_width": half_width,
                "k": k_value,
                "k_status": status_k(k_value),
                "n": n_value,
                "n_status": status_n(n_value),
                "hetp": hetp_value,
                "hetp_status": status_hetp(hetp_value),
            }
        )

    rs_pairs = []
    for i in range(len(peaks) - 1):
        left = peaks[i]
        right = peaks[i + 1]
        rs_value = calculate_rs(left["tr"], right["tr"], left["usp_width"], right["usp_width"])
        rs_pairs.append(
            {
                "pair": f'{left["label"]}-{right["label"]}',
                "rs": rs_value,
                "status": status_rs(rs_value, rs_spec),
            }
        )

    alpha_pairs = []
    analytes = peaks[1:]  # c1-c6 only
    for i in range(len(analytes) - 1):
        left = analytes[i]
        right = analytes[i + 1]
        alpha_value = calculate_alpha(left["k"], right["k"])
        alpha_pairs.append(
            {
                "pair": f'{left["label"]}-{right["label"]}',
                "alpha": alpha_value,
                "status": status_alpha(alpha_value),
            }
        )

    rs_values = [item["rs"] for item in rs_pairs]
    key_data = build_composite_key(
        observed_peak_count=observed_peak_count,
        total_run_time=total_run_time,
        rs_values=rs_values,
        run_time_spec=run_time_spec,
        rs_spec=rs_spec,
    )

    return {
        "run_time_spec": run_time_spec,
        "rs_spec": rs_spec,
        "total_run_time": total_run_time,
        "void_time": void_time,
        "column_length": column_length,
        "observed_peak_count": observed_peak_count,
        "peaks": peaks,
        "rs_pairs": rs_pairs,
        "alpha_pairs": alpha_pairs,
        "rs_min": min([v for v in rs_values if v is not None], default=None),
        "key_data": key_data,
    }


def round_or_blank(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return str(round(value, digits))
