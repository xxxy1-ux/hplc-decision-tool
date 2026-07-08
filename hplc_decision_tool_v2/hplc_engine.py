from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from rules import lookup_master_rule, lookup_resolution_rule

PEAK_LABELS = ["Uracil", "C1", "C2", "C3", "C4", "C5", "C6"]


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def rounded(value: Optional[float], digits: int = 3) -> Optional[float]:
    return None if value is None else round(value, digits)


@dataclass
class PeakData:
    peak_number: int
    label: str
    retention_time: Optional[float] = None
    area: Optional[float] = None
    height: Optional[float] = None
    usp_width: Optional[float] = None
    tailing_factor: Optional[float] = None
    signal_to_noise: Optional[float] = None

    @classmethod
    def from_form(cls, index: int, form: Dict[str, Any]) -> "PeakData":
        return cls(
            peak_number=index,
            label=PEAK_LABELS[index],
            retention_time=to_float(form.get(f"peak_{index}_rt")),
            area=to_float(form.get(f"peak_{index}_area")),
            height=to_float(form.get(f"peak_{index}_height")),
            usp_width=to_float(form.get(f"peak_{index}_width")),
            tailing_factor=to_float(form.get(f"peak_{index}_tailing")),
            signal_to_noise=to_float(form.get(f"peak_{index}_sn")),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LeverState:
    lever_state: str
    next_action: str
    rationale: str

    def to_dict(self) -> dict:
        return asdict(self)


LEVER_ACTIONS = {
    "L1": ("Try retention first: adjust organic solvent % in mobile phase", "Retention is the safest first adjustment: it changes elution times without altering selectivity or efficiency."),
    "L2": ("Try selectivity: adjust pH, change organic modifier, or switch column chemistry", "Selectivity changes (α) usually have the largest impact on resolution per unit change."),
    "L3": ("Try efficiency: reduce particle size, increase column length, or check extra-column dead volume", "Efficiency gains are incremental but can push marginal Rs above specification."),
    "L4": ("Try gradient elution: optimise gradient slope or add isocratic holds", "Gradient changes are more complex and are best used after simpler levers are exhausted."),
    "L5": ("Escalate to method redevelopment", "All standard optimisation levers have been exhausted."),
    "L6": ("Restart with isocratic optimisation", "Gradient was attempted before simpler levers, so restart systematic optimisation from retention/selectivity."),
}


def determine_lever_state(retention: bool, selectivity: bool, efficiency: bool, gradient: bool) -> LeverState:
    if gradient and not retention and not selectivity and not efficiency:
        state = "L6"
    elif retention and selectivity and efficiency and gradient:
        state = "L5"
    elif retention and selectivity and efficiency:
        state = "L4"
    elif retention and selectivity:
        state = "L3"
    elif retention:
        state = "L2"
    else:
        state = "L1"
    action, rationale = LEVER_ACTIONS[state]
    return LeverState(state, action, rationale)


def k_status(k: Optional[float]) -> str:
    if k is None:
        return ""
    if k < 1:
        return "LOW"
    if k > 20:
        return "HIGH"
    return "OK"


def rs_pair_status(rs: Optional[float], rs_spec: float) -> str:
    if rs is None:
        return ""
    if rs < 0.8:
        return "FAIL_SEVERE"
    if rs < rs_spec:
        return "FAIL"
    if rs <= rs_spec + 0.2:
        return "MARGINAL"
    return "PASS"


def alpha_status(alpha: Optional[float]) -> str:
    if alpha is None:
        return ""
    if alpha >= 1.1:
        return "GOOD"
    if alpha >= 1.05:
        return "MARGINAL"
    return "POOR"


def n_status(n: Optional[float]) -> str:
    if n is None:
        return ""
    if n >= 10000:
        return "GOOD"
    if n >= 5000:
        return "ADEQUATE"
    return "LOW"


def hetp_status(hetp: Optional[float]) -> str:
    if hetp is None:
        return ""
    if hetp <= 0.02:
        return "EXCELLENT"
    if hetp <= 0.05:
        return "GOOD"
    return "HIGH"


def calculate_parameters(peaks: List[PeakData], void_time: Optional[float], column_length: Optional[float], rs_spec: float = 1.4) -> Dict[str, Any]:
    k_by_label: Dict[str, Optional[float]] = {"Uracil": None}
    retention_factors = []
    for peak in peaks[1:]:
        k = safe_div(None if peak.retention_time is None or void_time is None else peak.retention_time - void_time, void_time)
        k_by_label[peak.label] = k
        retention_factors.append({"peak": peak.label, "tR": rounded(peak.retention_time), "k": rounded(k), "status": k_status(k)})

    resolution_pairs = []
    rs_values: List[float] = []
    fail_count = 0
    marginal_count = 0
    worst_pair = None
    for i in range(len(peaks) - 1):
        p1, p2 = peaks[i], peaks[i + 1]
        numerator = None if p1.retention_time is None or p2.retention_time is None else 2 * (p2.retention_time - p1.retention_time)
        denominator = None if p1.usp_width is None or p2.usp_width is None else p1.usp_width + p2.usp_width
        rs = safe_div(numerator, denominator)
        status = rs_pair_status(rs, rs_spec)
        if rs is not None:
            rs_values.append(rs)
            if rs < rs_spec:
                fail_count += 1
            if rs_spec <= rs <= rs_spec + 0.2:
                marginal_count += 1
            if worst_pair is None or rs < worst_pair["raw_rs"]:
                worst_pair = {"pair": f"{p1.label}–{p2.label}", "raw_rs": rs, "index": i}
        resolution_pairs.append({"pair": f"{p1.label}–{p2.label}", "rs": rounded(rs), "status": status})

    rs_min = min(rs_values) if rs_values else None
    if rs_min is None:
        rs_cat = "N/A"
    elif rs_min < 0.8:
        rs_cat = "FAIL_SEVERE"
    elif rs_min < rs_spec:
        rs_cat = "FAIL_MULTI" if fail_count > 1 else "FAIL_SINGLE"
    elif marginal_count > 0:
        rs_cat = "MARGINAL"
    else:
        rs_cat = "PASS"

    selectivity_pairs = [{"pair": "Uracil–C1", "alpha": None, "status": "N/A (void pair)"}]
    alpha_by_pair: Dict[str, Optional[float]] = {}
    for i in range(1, len(peaks) - 1):
        p1, p2 = peaks[i], peaks[i + 1]
        k1, k2 = k_by_label.get(p1.label), k_by_label.get(p2.label)
        if k1 is None or k2 is None or min(k1, k2) == 0:
            alpha = None
        else:
            alpha = max(k1, k2) / min(k1, k2)
        pair_name = f"{p1.label}–{p2.label}"
        alpha_by_pair[pair_name] = alpha
        selectivity_pairs.append({"pair": pair_name, "alpha": rounded(alpha), "status": alpha_status(alpha)})

    efficiency_data = []
    analyte_ns: List[float] = []
    for peak in peaks:
        n = None
        if peak.retention_time is not None and peak.usp_width is not None and peak.usp_width != 0:
            n = 5.54 * (peak.retention_time / peak.usp_width) ** 2
        hetp = safe_div(column_length, n)
        if peak.peak_number > 0 and n is not None:
            analyte_ns.append(n)
        efficiency_data.append({
            "peak": peak.label,
            "tR": rounded(peak.retention_time),
            "wHalf": rounded(peak.usp_width),
            "n": rounded(n, 1),
            "nStatus": n_status(n),
            "hetp": rounded(hetp, 5),
            "hetpStatus": hetp_status(hetp),
        })

    average_n = sum(analyte_ns) / len(analyte_ns) if analyte_ns else None

    return {
        "retentionFactors": retention_factors,
        "resolutionPairs": resolution_pairs,
        "rsMin": rounded(rs_min),
        "rsMinStatus": rs_cat,
        "selectivityPairs": selectivity_pairs,
        "efficiencyData": efficiency_data,
        "averageN": rounded(average_n, 1),
        "averageNStatus": n_status(average_n),
        "kByLabel": {key: rounded(value) for key, value in k_by_label.items()},
        "rawKByLabel": k_by_label,
        "alphaByPair": {key: rounded(value) for key, value in alpha_by_pair.items()},
        "rawAlphaByPair": alpha_by_pair,
        "worstPair": worst_pair,
        "failCount": fail_count,
        "marginalCount": marginal_count,
    }


def peak_cat(observed_peak_count: Optional[int]) -> str:
    if observed_peak_count is None:
        return ""
    if observed_peak_count == 7:
        return "7"
    if observed_peak_count < 7:
        return "<7"
    return ">7"


def runtime_cat(total_runtime: Optional[float], runtime_spec: float = 20.0) -> str:
    if total_runtime is None:
        return ""
    return "<20" if total_runtime < runtime_spec else ">20"


def classify_resolution_subproblem(calculated: Dict[str, Any], rs_spec: float = 1.4) -> Dict[str, str]:
    rs_min = calculated.get("rsMin")
    k_by_label = calculated.get("rawKByLabel", {})
    worst_pair = calculated.get("worstPair") or {}
    if rs_min is None:
        return {"rsRange": "ANY", "kCondition": "ANY", "alphaCondition": "ANY", "composite": "ANY|ANY|ANY"}

    rs_range = "SEVERE" if rs_min < 0.8 else "MODERATE" if rs_min < rs_spec else "ANY"

    analyte_ks = [k for label, k in k_by_label.items() if label != "Uracil" and k is not None]
    early_ks = [k_by_label.get("C1"), k_by_label.get("C2")]
    late_ks = [k_by_label.get("C5"), k_by_label.get("C6")]

    if any(k is not None and k < 1 for k in early_ks):
        k_condition = "EARLY_LOW"
    elif any(k is not None and k > 20 for k in late_ks):
        k_condition = "LATE_HIGH"
    elif any(k is not None and k < 1 for k in analyte_ks):
        k_condition = "LOW"
    else:
        k_condition = "ADEQUATE"

    alpha_condition = "ANY"
    pair = worst_pair.get("pair")
    if pair and pair != "Uracil–C1":
        alpha_raw = calculated.get("rawAlphaByPair", {}).get(pair)
        if alpha_raw is not None:
            alpha_condition = "LOW" if alpha_raw < 1.05 else "ADEQUATE"
    elif rs_range in ("SEVERE", "MODERATE"):
        alpha_condition = "ANY"

    return {"rsRange": rs_range, "kCondition": k_condition, "alphaCondition": alpha_condition, "composite": f"{rs_range}|{k_condition}|{alpha_condition}"}


def run_diagnostics(peaks: List[PeakData], form_data: Dict[str, Any], total_runtime: Optional[float]) -> Dict[str, Any]:
    reference_total_area = to_float(form_data.get("reference_total_area"))
    reference_peak_area = to_float(form_data.get("reference_peak_area"))
    expected_last_elution_time = to_float(form_data.get("expected_last_elution_time"))
    expected_void_time = to_float(form_data.get("expected_void_time"))
    spiking_result = (form_data.get("spiking_result") or "not_done").strip()

    tests = []
    decision_path = []

    observed_area = sum(p.area or 0 for p in peaks if p.area is not None)
    if reference_total_area:
        ratio = observed_area / reference_total_area
        if 0.85 <= ratio <= 1.15:
            total_area_signal = "MERGED"
            total_area_result = "PASS"
            evidence = f"Observed total area is {ratio:.2f}× reference total area, within ±15%."
        elif ratio < 0.85:
            total_area_signal = "ABSENT"
            total_area_result = "FAIL"
            evidence = f"Observed total area is {ratio:.2f}× reference total area, >15% deficit."
        else:
            total_area_signal = "INCONCLUSIVE"
            total_area_result = "WARN"
            evidence = f"Observed total area is {ratio:.2f}× reference total area, above tolerance."
    else:
        total_area_signal = "UNKNOWN"
        total_area_result = "N/A"
        evidence = "Reference total area not provided."
    tests.append({"testName": "Total Area", "result": total_area_result, "indicator": total_area_signal, "confidence": "HIGH" if total_area_signal in {"MERGED", "ABSENT"} else "LOW", "evidence": evidence})

    enriched_peaks = []
    if reference_peak_area:
        for p in peaks[1:]:
            if p.area is not None and p.area >= 1.8 * reference_peak_area:
                enriched_peaks.append(p.label)
        if enriched_peaks:
            individual_signal = "MERGED"
            evidence = f"Peak(s) {', '.join(enriched_peaks)} are ≥1.8× reference peak area."
            individual_result = "PASS"
        else:
            individual_signal = "ABSENT"
            evidence = "No observed peak is ≥1.8× reference peak area."
            individual_result = "FAIL"
    else:
        individual_signal = "UNKNOWN"
        individual_result = "N/A"
        evidence = "Reference individual peak area not provided."
    tests.append({"testName": "Individual Area", "result": individual_result, "indicator": individual_signal, "confidence": "MEDIUM", "evidence": evidence})

    abnormal_shapes = [p.label for p in peaks[1:] if p.tailing_factor is not None and p.tailing_factor > 2.0]
    if abnormal_shapes:
        shape_signal = "MERGED"
        shape_result = "PASS"
        evidence = f"Peak(s) {', '.join(abnormal_shapes)} have tailing/asymmetry factor > 2.0."
    else:
        shape_signal = "ABSENT"
        shape_result = "FAIL"
        evidence = "No peak has tailing/asymmetry factor > 2.0."
    tests.append({"testName": "Peak Shape", "result": shape_result, "indicator": shape_signal, "confidence": "MEDIUM", "evidence": evidence})

    uracil_rt = peaks[0].retention_time if peaks else None
    if expected_void_time and uracil_rt:
        void_shift_pct = abs(uracil_rt - expected_void_time) / expected_void_time
        if void_shift_pct > 0.15:
            void_signal = "SYSTEM_ERROR"
            void_result = "FAIL"
            evidence = f"Uracil void marker shifted by {void_shift_pct:.0%} from expected."
        else:
            void_signal = "OK"
            void_result = "PASS"
            evidence = f"Uracil void marker is within ±15% of expected."
    else:
        void_signal = "UNKNOWN"
        void_result = "N/A"
        evidence = "Expected void time or observed uracil retention time not provided."
    tests.append({"testName": "Void Marker", "result": void_result, "indicator": void_signal, "confidence": "HIGH" if void_signal in {"SYSTEM_ERROR", "OK"} else "LOW", "evidence": evidence})

    if expected_last_elution_time and total_runtime:
        if total_runtime < expected_last_elution_time:
            window_signal = "ABSENT"
            window_result = "FAIL"
            evidence = f"Run ends at {total_runtime:g} min before expected last elution at {expected_last_elution_time:g} min."
        else:
            window_signal = "OK"
            window_result = "PASS"
            evidence = "Run window is long enough for expected last elution."
    else:
        window_signal = "UNKNOWN"
        window_result = "N/A"
        evidence = "Expected last elution time not provided."
    tests.append({"testName": "Run-Window Truncation", "result": window_result, "indicator": window_signal, "confidence": "HIGH" if window_signal in {"ABSENT", "OK"} else "LOW", "evidence": evidence})

    if spiking_result == "coelutes":
        spiking_signal = "MERGED"
        spiking_result_label = "PASS"
        evidence = "Spiked compound co-elutes with an existing peak."
    elif spiking_result == "new_peak":
        spiking_signal = "ABSENT"
        spiking_result_label = "PASS"
        evidence = "Spiked compound produces a new separate peak."
    else:
        spiking_signal = "UNKNOWN"
        spiking_result_label = "N/A"
        evidence = "Spiking test not performed."
    tests.append({"testName": "Spiking", "result": spiking_result_label, "indicator": spiking_signal, "confidence": "DEFINITIVE" if spiking_signal in {"MERGED", "ABSENT"} else "LOW", "evidence": evidence})

    if window_signal == "ABSENT":
        determination, confidence, recommended_action = "ABSENT", "HIGH", "Extend the run time and re-inject."
        decision_path.append("Step 1: Run-window check indicates missing peaks may not have eluted.")
    elif void_signal == "SYSTEM_ERROR":
        determination, confidence, recommended_action = "SYSTEM_ERROR", "HIGH", "Check tubing, column connections, flow path, and void marker behaviour before method diagnosis."
        decision_path.append("Step 2: Void marker shift suggests a system integrity issue.")
    elif spiking_signal in {"MERGED", "ABSENT"}:
        determination, confidence = spiking_signal, "DEFINITIVE"
        recommended_action = "Use the spiking result as the definitive conclusion and apply the corresponding matrix fix."
        decision_path.append("Step 5: Spiking test overrides earlier indirect evidence.")
    elif total_area_signal == "MERGED" and (individual_signal == "MERGED" or shape_signal == "MERGED"):
        determination, confidence, recommended_action = "MERGED", "HIGH", "Adjust selectivity first; confirm with gradient scouting or spiking if needed."
        decision_path.append("Steps 3–4: Mass balance plus local area/shape evidence supports co-elution.")
    elif total_area_signal == "ABSENT" and individual_signal != "MERGED" and shape_signal != "MERGED":
        determination, confidence, recommended_action = "ABSENT", "MEDIUM", "Check sample preparation/recovery and consider extending run time or increasing retention."
        decision_path.append("Steps 3–4: Area deficit with clean peaks supports absence.")
    elif total_area_signal in {"MERGED", "ABSENT"}:
        determination, confidence, recommended_action = total_area_signal, "MEDIUM", "Evidence is incomplete; perform spiking test to confirm."
        decision_path.append("Step 3: Mass balance gives a preliminary conclusion, but confirmatory evidence is limited.")
    else:
        determination, confidence, recommended_action = "INCONCLUSIVE", "LOW", "Provide reference area data or perform a spiking test."
        decision_path.append("Insufficient diagnostic evidence; no deterministic conclusion can be made.")

    return {"determination": determination, "confidence": confidence, "tests": tests, "decisionTreePath": decision_path, "recommendedAction": recommended_action}


def analyse_run(payload: Dict[str, Any]) -> Dict[str, Any]:
    runtime_spec = to_float(payload.get("run_time_spec")) or 20.0
    rs_spec = to_float(payload.get("rs_spec")) or 1.4
    observed_peak_count = to_int(payload.get("observed_peak_count"))
    total_runtime = to_float(payload.get("total_run_time"))
    void_time = to_float(payload.get("void_time"))
    column_length = to_float(payload.get("column_length"))
    peaks = payload.get("peaks") or []
    if peaks and isinstance(peaks[0], dict):
        peaks = [PeakData(**p) for p in peaks]

    calculated = calculate_parameters(peaks, void_time, column_length, rs_spec)
    p_cat = peak_cat(observed_peak_count)
    rt_cat = runtime_cat(total_runtime, runtime_spec)
    rule, lookup_key, duplicate_guidance = lookup_master_rule(p_cat, rt_cat, calculated["rsMinStatus"])

    resolution_subproblem = classify_resolution_subproblem(calculated, rs_spec)
    resolution_rule = None
    if rule and rule.rule_id in {2, 5, 8}:
        resolution_rule = lookup_resolution_rule(
            resolution_subproblem["rsRange"],
            resolution_subproblem["kCondition"],
            resolution_subproblem["alphaCondition"],
        )

    diagnostics = None
    if observed_peak_count is not None and observed_peak_count < 7:
        diagnostics = run_diagnostics(peaks, payload, total_runtime)

    return {
        "calculated": calculated,
        "peakCat": p_cat,
        "runtimeCat": rt_cat,
        "rsCat": calculated["rsMinStatus"],
        "lookupKey": lookup_key,
        "rule": rule.to_dict() if rule else None,
        "duplicateGuidance": [r.to_dict() for r in duplicate_guidance],
        "resolutionSubproblem": resolution_subproblem,
        "resolutionRule": resolution_rule.to_dict() if resolution_rule else None,
        "diagnostics": diagnostics,
    }
