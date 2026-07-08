import streamlit as st
import pandas as pd
from typing import Any

# =========================
# Page setup
# =========================

st.set_page_config(
    page_title="HPLC Decision Tool",
    page_icon="🧪",
    layout="wide",
)

# =========================
# Helper functions
# =========================

def to_float(value: Any) -> float | None:
    """Convert input value to float. Invalid values become None."""
    try:
        if value is None or value == "":
            return None
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


def round_value(value: float | None, digits: int = 3) -> str:
    if value is None:
        return ""
    return str(round(value, digits))


# =========================
# Status logic
# =========================

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


# =========================
# Composite key logic
# =========================

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
    valid_rs = [v for v in rs_values if v is not None]

    if not valid_rs:
        return "N/A"

    rs_min = min(valid_rs)
    fail_count = sum(1 for v in valid_rs if v < rs_spec)

    if rs_min >= rs_spec:
        has_marginal = any(rs_spec <= v < 1.6 for v in valid_rs)
        return "MARGINAL" if has_marginal else "PASS"

    if rs_min < 0.8:
        return "FAIL_SEVERE"

    if fail_count > 1:
        return "FAIL_MULTI"

    return "FAIL_SINGLE"


def build_composite_key(
    observed_peak_count: int | None,
    total_run_time: float | None,
    rs_values: list[float | None],
    run_time_spec: float = 20,
    rs_spec: float = 1.4,
) -> dict:
    peak_cat = classify_peak_count(observed_peak_count)
    runtime_cat = classify_runtime(total_run_time, run_time_spec)

    if peak_cat == ">7":
        rs_cat = "N/A"
    else:
        rs_cat = classify_rs_overall(rs_values, rs_spec)

    lookup_rs_cat = rs_cat

    # The matrix uses generic FAIL in some routes.
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


# =========================
# Rule dictionary
# =========================

LOOKUP_MASTER = {
    "7|<20|PASS": {
        "rule_id": 1,
        "scenario": "M1",
        "root_cause": "PASS — all specifications met",
        "diagnostic_action": "No action required.",
        "recommended_fix": "None — method is within specification.",
        "rationale": "All acceptance criteria are satisfied.",
    },
    "7|<20|MARGINAL": {
        "rule_id": "MARGINAL-7",
        "scenario": "M1B",
        "root_cause": "All peaks present, but one or more pairs are marginal.",
        "diagnostic_action": "Review the marginal pair and calculate k, alpha and N.",
        "recommended_fix": "Consider a small selectivity or efficiency improvement to increase robustness.",
        "rationale": "A marginal pair may pass now but fail under small method variation.",
    },
    "7|<20|FAIL_SINGLE": {
        "rule_id": 2,
        "scenario": "RS1",
        "root_cause": "Resolution failure on one adjacent pair",
        "diagnostic_action": "Calculate k, alpha and N for the worst pair.",
        "recommended_fix": "Apply a targeted fix using retention, selectivity, efficiency, then gradient priority.",
        "rationale": "Only one pair fails, so a focused adjustment may be sufficient.",
    },
    "7|<20|FAIL_MULTI": {
        "rule_id": 3,
        "scenario": "RS2",
        "root_cause": "Systemic resolution deficit",
        "diagnostic_action": "Check column condition, mobile phase preparation, flow rate and temperature.",
        "recommended_fix": "Replace column if N is degraded; re-prepare mobile phase; verify instrument settings.",
        "rationale": "Multiple failing pairs suggest a broader method or system problem.",
    },
    "7|<20|FAIL_SEVERE": {
        "rule_id": 13,
        "scenario": "RS3",
        "root_cause": "Severe resolution failure — near-complete co-elution",
        "diagnostic_action": "Check the worst pair and calculate alpha.",
        "recommended_fix": "Change selectivity first: organic modifier, pH or column chemistry.",
        "rationale": "Very low Rs usually cannot be fixed by efficiency alone.",
    },
    "7|>20|PASS": {
        "rule_id": 4,
        "scenario": "RT1",
        "root_cause": "Run time exceeded but resolution is adequate",
        "diagnostic_action": "Identify late-eluting peaks and check gradient slope, flow rate and column dimensions.",
        "recommended_fix": "Compress gradient, increase flow rate if Rs is maintained, or use a shorter column if suitable.",
        "rationale": "Resolution is achieved, so the aim is to move peaks earlier without losing separation.",
    },
    "7|>20|MARGINAL": {
        "rule_id": "RT-MARGINAL",
        "scenario": "RT1B",
        "root_cause": "Run time exceeded and resolution margin is weak.",
        "diagnostic_action": "Protect the marginal pair before shortening the run.",
        "recommended_fix": "Improve the marginal pair first, then optimise run time.",
        "rationale": "Shortening run time may reduce already marginal separation.",
    },
    "7|>20|FAIL": {
        "rule_id": 5,
        "scenario": "RT2",
        "root_cause": "Both run time and resolution fail",
        "diagnostic_action": "Prioritise resolution first. Calculate k, alpha and N for the worst pair.",
        "recommended_fix": "Fix resolution first, then re-optimise run time.",
        "rationale": "Shortening a failing method before fixing Rs may worsen separation.",
    },
    "<7|<20|PASS": {
        "rule_id": 6,
        "scenario": "M2",
        "root_cause": "Peaks missing — merged or absent",
        "diagnostic_action": "Use differential diagnosis: total area, peak shape, void marker, extended run and scouting run.",
        "recommended_fix": "If merged, adjust selectivity. If absent, extend run time or adjust retention.",
        "rationale": "Missing peaks need classification before the correct fix can be selected.",
    },
    "<7|<20|MARGINAL": {
        "rule_id": 12,
        "scenario": "M6",
        "root_cause": "Missing peak(s) with marginal resolution",
        "diagnostic_action": "Diagnose missing peaks and monitor the marginal pair.",
        "recommended_fix": "Fix missing peak issue first, then consider small selectivity adjustment.",
        "rationale": "The missing peak issue is more important than a borderline passing pair.",
    },
    "<7|<20|FAIL": {
        "rule_id": 7,
        "scenario": "M3",
        "root_cause": "Missing peaks and poor resolution among remaining peaks — likely co-elution",
        "diagnostic_action": "Confirm with area comparison and gradient scouting.",
        "recommended_fix": "Apply co-elution fixes: selectivity first, then efficiency.",
        "rationale": "Poor Rs plus missing peaks strongly suggests merged compounds.",
    },
    "<7|>20|PASS": {
        "rule_id": 8,
        "scenario": "M4",
        "root_cause": "Peaks likely beyond run window",
        "diagnostic_action": "Run extended blank or gradient scouting run to locate missing peaks.",
        "recommended_fix": "Extend run time and adjust method to elute strongly retained analytes.",
        "rationale": "Long runtime with missing peaks suggests late or strongly retained compounds.",
    },
    "<7|>20|MARGINAL": {
        "rule_id": "M4B",
        "scenario": "M4B",
        "root_cause": "Missing peaks, long run time and marginal separation.",
        "diagnostic_action": "Locate missing peaks first, then review marginal pair robustness.",
        "recommended_fix": "Extend or scout run to find missing analytes; then refine selectivity.",
        "rationale": "The method has both elution-window and robustness concerns.",
    },
    "<7|>20|FAIL": {
        "rule_id": 9,
        "scenario": "M5",
        "root_cause": "Multiple issues: missing peaks, poor resolution and long run time",
        "diagnostic_action": "Start systematic re-optimisation from retention, then selectivity, then efficiency.",
        "recommended_fix": "Begin fresh from retention optimisation and escalate sequentially.",
        "rationale": "Multiple failures mean incremental single-parameter fixes may not be enough.",
    },
    ">7|<20|N/A": {
        "rule_id": 10,
        "scenario": "X1",
        "root_cause": "Unexpected extra peaks — possible impurity, degradation product or contaminant",
        "diagnostic_action": "Run blank injection and solvent blank.",
        "recommended_fix": "If blank shows extra peak, clean system or replace contaminated phase/column. If sample-related, review sample preparation.",
        "rationale": "Extra peaks must be identified before method troubleshooting.",
    },
    ">7|>20|N/A": {
        "rule_id": 11,
        "scenario": "X2",
        "root_cause": "Extra peaks plus extended run",
        "diagnostic_action": "Run blank and solvent blank; investigate late-eluting interferents.",
        "recommended_fix": "Clean system; add wash step or stronger final wash if late contaminant persists.",
        "rationale": "Extra late peaks may be caused by contamination or carryover.",
    },
    "7|<20|N/A": {
        "rule_id": 14,
        "scenario": "D1",
        "root_cause": "Peaks and run time on spec, but peak data incomplete",
        "diagnostic_action": "Enter retention times and widths for all 7 peaks.",
        "recommended_fix": "Enter peak data to complete assessment.",
        "rationale": "Resolution cannot be assessed without peak data.",
    },
    "7|>20|N/A": {
        "rule_id": 15,
        "scenario": "D2",
        "root_cause": "Run time exceeded, but peak data incomplete",
        "diagnostic_action": "Enter retention times and widths for all 7 peaks.",
        "recommended_fix": "Enter peak data to complete assessment.",
        "rationale": "Run time is already high, but Rs cannot be assessed without peak data.",
    },
    "<7|<20|N/A": {
        "rule_id": 16,
        "scenario": "D3",
        "root_cause": "Fewer than 7 peaks observed; peak data incomplete",
        "diagnostic_action": "Enter peak data for merged-versus-absent diagnosis.",
        "recommended_fix": "Enter peak data to complete assessment.",
        "rationale": "Missing peaks cannot be diagnosed without supporting evidence.",
    },
    "<7|>20|N/A": {
        "rule_id": 17,
        "scenario": "D4",
        "root_cause": "Fewer than 7 peaks and run time exceeded; peak data incomplete",
        "diagnostic_action": "Enter peak data for full diagnosis.",
        "recommended_fix": "Enter peak data to complete assessment.",
        "rationale": "Multiple issues are suspected but need data confirmation.",
    },
}


def fire_master_rule(composite_key: str) -> dict:
    return LOOKUP_MASTER.get(
        composite_key,
        {
            "rule_id": "NO_MATCH",
            "scenario": "NO_MATCH",
            "root_cause": f"No rule found for composite key: {composite_key}",
            "diagnostic_action": "Check input values and rule dictionary.",
            "recommended_fix": "Add or correct this composite key in LOOKUP_MASTER.",
            "rationale": "Every valid input should map to one deterministic rule.",
        },
    )


# =========================
# Lever tracker
# =========================

def determine_lever_state(
    tried_retention: bool,
    tried_selectivity: bool,
    tried_efficiency: bool,
    tried_gradient: bool,
) -> dict:
    if tried_gradient and not (tried_retention or tried_selectivity or tried_efficiency):
        return {
            "state": "L6",
            "next_action": "Restart with isocratic optimisation before using gradient changes.",
        }

    if tried_retention and tried_selectivity and tried_efficiency and tried_gradient:
        return {
            "state": "L5",
            "next_action": "Escalate to method redevelopment.",
        }

    if tried_retention and tried_selectivity and tried_efficiency:
        return {
            "state": "L4",
            "next_action": "Try gradient elution: optimise gradient slope or add isocratic holds.",
        }

    if tried_retention and tried_selectivity:
        return {
            "state": "L3",
            "next_action": "Try efficiency: smaller particle size, longer column, or check extra-column volume.",
        }

    if tried_retention:
        return {
            "state": "L2",
            "next_action": "Try selectivity: adjust pH, organic modifier, or column chemistry.",
        }

    return {
        "state": "L1",
        "next_action": "Try retention first: adjust organic solvent percentage.",
    }


# =========================
# UI
# =========================

st.title("🧪 HPLC Method Troubleshooting Decision Tool")
st.caption("Streamlit + Python deterministic decision engine")

with st.expander("How to use this tool", expanded=True):
    st.write(
        """
        1. Enter method specifications.
        2. Enter peak data for uracil and compounds C1–C6.
        3. Tick any optimisation levers already tried.
        4. Click **Run Analysis**.

        The decision logic is calculated in Python. No AI is used to select the recommendation.
        """
    )

st.sidebar.header("Method Specifications")

run_time_spec = st.sidebar.number_input(
    "Run Time Specification (min)",
    min_value=0.01,
    value=20.0,
    step=0.5,
)

rs_spec = st.sidebar.number_input(
    "Resolution Specification Rs",
    min_value=0.01,
    value=1.4,
    step=0.1,
)

observed_peak_count = st.sidebar.number_input(
    "Observed Peak Count",
    min_value=0,
    value=7,
    step=1,
)

total_run_time = st.sidebar.number_input(
    "Total Run Time (min)",
    min_value=0.0,
    value=18.0,
    step=0.5,
)

void_time = st.sidebar.number_input(
    "Void Time t0 (min)",
    min_value=0.0,
    value=1.0,
    step=0.1,
)

column_length = st.sidebar.number_input(
    "Column Length (mm)",
    min_value=0.0,
    value=150.0,
    step=10.0,
)

st.sidebar.header("Lever History")

tried_retention = st.sidebar.checkbox("Retention tried")
tried_selectivity = st.sidebar.checkbox("Selectivity tried")
tried_efficiency = st.sidebar.checkbox("Efficiency tried")
tried_gradient = st.sidebar.checkbox("Gradient tried")

st.subheader("Peak Table Input")

default_data = pd.DataFrame(
    {
        "Peak": ["Uracil", "C1", "C2", "C3", "C4", "C5", "C6"],
        "Retention Time": [1.0, 3.0, 5.2, 7.6, 10.1, 13.0, 16.5],
        "USP Width": [0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
        "Width at Half Height": [0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4],
    }
)

peak_table = st.data_editor(
    default_data,
    num_rows="fixed",
    use_container_width=True,
)

run_button = st.button("Run Analysis", type="primary")

if run_button:
    peaks = []

    for _, row in peak_table.iterrows():
        label = str(row["Peak"])
        tr = to_float(row["Retention Time"])
        usp_width = to_float(row["USP Width"])
        half_width = to_float(row["Width at Half Height"])

        k_value = None if label.lower() == "uracil" else calculate_k(tr, void_time)
        n_value = calculate_n(tr, half_width)
        hetp_value = calculate_hetp(column_length, n_value)

        peaks.append(
            {
                "Peak": label,
                "tR": tr,
                "USP Width": usp_width,
                "Half Width": half_width,
                "k": k_value,
                "k Status": status_k(k_value),
                "N": n_value,
                "N Status": status_n(n_value),
                "HETP": hetp_value,
                "HETP Status": status_hetp(hetp_value),
            }
        )

    rs_rows = []
    for i in range(len(peaks) - 1):
        p1 = peaks[i]
        p2 = peaks[i + 1]
        rs_value = calculate_rs(p1["tR"], p2["tR"], p1["USP Width"], p2["USP Width"])
        rs_rows.append(
            {
                "Pair": f'{p1["Peak"]}-{p2["Peak"]}',
                "Rs": rs_value,
                "Status": status_rs(rs_value, rs_spec),
            }
        )

    alpha_rows = []
    analytes = peaks[1:]
    for i in range(len(analytes) - 1):
        p1 = analytes[i]
        p2 = analytes[i + 1]
        alpha_value = calculate_alpha(p1["k"], p2["k"])
        alpha_rows.append(
            {
                "Pair": f'{p1["Peak"]}-{p2["Peak"]}',
                "Alpha": alpha_value,
                "Status": status_alpha(alpha_value),
            }
        )

    rs_values = [row["Rs"] for row in rs_rows]
    key_data = build_composite_key(
        observed_peak_count=int(observed_peak_count),
        total_run_time=total_run_time,
        rs_values=rs_values,
        run_time_spec=run_time_spec,
        rs_spec=rs_spec,
    )

    rule = fire_master_rule(key_data["composite_key"])

    lever = determine_lever_state(
        tried_retention=tried_retention,
        tried_selectivity=tried_selectivity,
        tried_efficiency=tried_efficiency,
        tried_gradient=tried_gradient,
    )

    st.success("Analysis complete")

    st.subheader("Decision Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Composite Key", key_data["composite_key"])
    col2.metric("Peak Category", key_data["peak_cat"])
    col3.metric("Runtime Category", key_data["runtime_cat"])
    col4.metric("Rs Category", key_data["rs_cat"])

    st.markdown("### Fired Rule")
    st.info(
        f"""
        **Rule ID:** {rule["rule_id"]}  
        **Scenario:** {rule["scenario"]}  
        **Root Cause:** {rule["root_cause"]}  
        **Diagnostic Action:** {rule["diagnostic_action"]}  
        **Recommended Fix:** {rule["recommended_fix"]}  
        **Rationale:** {rule["rationale"]}
        """
    )

    st.markdown("### Lever Tracker")
    st.warning(
        f"""
        **Lever State:** {lever["state"]}  
        **Next Action:** {lever["next_action"]}
        """
    )

    st.subheader("Calculated Parameters")

    peak_df = pd.DataFrame(peaks)
    for col in ["tR", "USP Width", "Half Width", "k", "N", "HETP"]:
        peak_df[col] = peak_df[col].apply(lambda x: round(x, 3) if x is not None else "")

    st.markdown("#### Retention, Efficiency and HETP")
    st.dataframe(peak_df, use_container_width=True)

    rs_df = pd.DataFrame(rs_rows)
    rs_df["Rs"] = rs_df["Rs"].apply(lambda x: round(x, 3) if x is not None else "")
    st.markdown("#### Resolution")
    st.dataframe(rs_df, use_container_width=True)

    alpha_df = pd.DataFrame(alpha_rows)
    alpha_df["Alpha"] = alpha_df["Alpha"].apply(lambda x: round(x, 3) if x is not None else "")
    st.markdown("#### Selectivity")
    st.dataframe(alpha_df, use_container_width=True)

else:
    st.info("Enter your method and peak data, then click **Run Analysis**.")
