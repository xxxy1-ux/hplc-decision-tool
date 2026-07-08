import streamlit as st
import pandas as pd
from typing import Any

st.set_page_config(
    page_title="HPLC Decision Tool",
    page_icon="🧪",
    layout="wide",
)

def to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

def calculate_k(retention_time, void_time):
    if retention_time is None or void_time in (None, 0):
        return None
    return (retention_time - void_time) / void_time

def calculate_rs(tr1, tr2, w1, w2):
    if None in (tr1, tr2, w1, w2):
        return None
    denominator = w1 + w2
    if denominator == 0:
        return None
    return 2 * (tr2 - tr1) / denominator

def calculate_alpha(k1, k2):
    if k1 is None or k2 is None:
        return None
    small = min(k1, k2)
    large = max(k1, k2)
    if small == 0:
        return None
    return large / small

def calculate_n(retention_time, width_half_height):
    if retention_time is None or width_half_height in (None, 0):
        return None
    return 5.54 * (retention_time / width_half_height) ** 2

def calculate_hetp(column_length, n_value):
    if column_length is None or n_value in (None, 0):
        return None
    return column_length / n_value

def status_k(k):
    if k is None:
        return ""
    if k < 1:
        return "LOW"
    if k <= 20:
        return "OK"
    return "HIGH"

def status_rs(rs, rs_spec=1.4):
    if rs is None:
        return ""
    if rs >= rs_spec:
        return "PASS" if rs >= 1.6 else "MARGINAL"
    return "FAIL"

def status_alpha(alpha):
    if alpha is None:
        return ""
    if alpha >= 1.1:
        return "GOOD"
    if alpha >= 1.05:
        return "MARGINAL"
    return "POOR"

def status_n(n_value):
    if n_value is None:
        return ""
    if n_value >= 10000:
        return "GOOD"
    if n_value >= 5000:
        return "ADEQUATE"
    return "LOW"

def status_hetp(hetp):
    if hetp is None:
        return ""
    if hetp <= 0.02:
        return "EXCELLENT"
    if hetp <= 0.05:
        return "GOOD"
    return "HIGH"

def classify_peak_count(observed_peak_count):
    if observed_peak_count == 7:
        return "7"
    if observed_peak_count < 7:
        return "<7"
    return ">7"

def classify_runtime(total_run_time, run_time_spec=20):
    return "<20" if total_run_time < run_time_spec else ">20"

def classify_rs_overall(rs_values, rs_spec=1.4):
    valid = [v for v in rs_values if v is not None]
    if not valid:
        return "N/A"

    rs_min = min(valid)
    fail_count = sum(1 for v in valid if v < rs_spec)

    if rs_min >= rs_spec:
        if any(rs_spec <= v < 1.6 for v in valid):
            return "MARGINAL"
        return "PASS"

    if rs_min < 0.8:
        return "FAIL_SEVERE"

    if fail_count > 1:
        return "FAIL_MULTI"

    return "FAIL_SINGLE"

def build_composite_key(observed_peak_count, total_run_time, rs_values, run_time_spec=20, rs_spec=1.4):
    peak_cat = classify_peak_count(observed_peak_count)
    runtime_cat = classify_runtime(total_run_time, run_time_spec)

    if peak_cat == ">7":
        rs_cat = "N/A"
    else:
        rs_cat = classify_rs_overall(rs_values, rs_spec)

    lookup_rs_cat = rs_cat

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
        "recommended_fix": "Consider a small selectivity or efficiency improvement.",
        "rationale": "A marginal pair may pass now but fail under small method variation.",
    },
    "7|<20|FAIL_SINGLE": {
        "rule_id": 2,
        "scenario": "RS1",
        "root_cause": "Resolution failure on one adjacent pair.",
        "diagnostic_action": "Calculate k, alpha and N for the worst pair.",
        "recommended_fix": "Apply targeted fix using retention, selectivity, efficiency, then gradient priority.",
        "rationale": "Only one pair fails, so a focused adjustment may be sufficient.",
    },
    "7|<20|FAIL_MULTI": {
        "rule_id": 3,
        "scenario": "RS2",
        "root_cause": "Systemic resolution deficit.",
        "diagnostic_action": "Check column condition, mobile phase preparation, flow rate and temperature.",
        "recommended_fix": "Replace column if N is degraded; re-prepare mobile phase; verify instrument settings.",
        "rationale": "Multiple failing pairs suggest a broader method or system problem.",
    },
    "7|<20|FAIL_SEVERE": {
        "rule_id": 13,
        "scenario": "RS3",
        "root_cause": "Severe resolution failure — near-complete co-elution.",
        "diagnostic_action": "Check the worst pair and calculate alpha.",
        "recommended_fix": "Change selectivity first: organic modifier, pH or column chemistry.",
        "rationale": "Very low Rs usually cannot be fixed by efficiency alone.",
    },
    "7|>20|PASS": {
        "rule_id": 4,
        "scenario": "RT1",
        "root_cause": "Run time exceeded but resolution is adequate.",
        "diagnostic_action": "Identify late-eluting peaks.",
        "recommended_fix": "Compress gradient, increase flow rate if Rs is maintained, or use a shorter column if suitable.",
        "rationale": "Resolution is achieved, so move peaks earlier without losing separation.",
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
        "root_cause": "Both run time and resolution fail.",
        "diagnostic_action": "Prioritise resolution first.",
        "recommended_fix": "Fix resolution first, then re-optimise run time.",
        "rationale": "Shortening a failing method before fixing Rs may worsen separation.",
    },
    "<7|<20|PASS": {
        "rule_id": 6,
        "scenario": "M2",
        "root_cause": "Peaks missing — merged or absent.",
        "diagnostic_action": "Use differential diagnosis.",
        "recommended_fix": "If merged, adjust selectivity. If absent, extend run time or adjust retention.",
        "rationale": "Missing peaks need classification first.",
    },
    "<7|<20|MARGINAL": {
        "rule_id": 12,
        "scenario": "M6",
        "root_cause": "Missing peak(s) with marginal resolution.",
        "diagnostic_action": "Diagnose missing peaks and monitor marginal pair.",
        "recommended_fix": "Fix missing peak issue first, then consider small selectivity adjustment.",
        "rationale": "Missing peak issue is more important than a borderline passing pair.",
    },
    "<7|<20|FAIL": {
        "rule_id": 7,
        "scenario": "M3",
        "root_cause": "Missing peaks and poor resolution — likely co-elution.",
        "diagnostic_action": "Confirm with area comparison and gradient scouting.",
        "recommended_fix": "Apply co-elution fixes: selectivity first, then efficiency.",
        "rationale": "Poor Rs plus missing peaks strongly suggests merged compounds.",
    },
    "<7|>20|PASS": {
        "rule_id": 8,
        "scenario": "M4",
        "root_cause": "Peaks likely beyond run window.",
        "diagnostic_action": "Run extended blank or gradient scouting run.",
        "recommended_fix": "Extend run time and adjust method to elute strongly retained analytes.",
        "rationale": "Long runtime with missing peaks suggests late or strongly retained compounds.",
    },
    "<7|>20|MARGINAL": {
        "rule_id": "M4B",
        "scenario": "M4B",
        "root_cause": "Missing peaks, long run time and marginal separation.",
        "diagnostic_action": "Locate missing peaks first, then review marginal pair.",
        "recommended_fix": "Extend/scout run, then refine selectivity.",
        "rationale": "The method has both elution-window and robustness concerns.",
    },
    "<7|>20|FAIL": {
        "rule_id": 9,
        "scenario": "M5",
        "root_cause": "Multiple issues: missing peaks, poor resolution and long run time.",
        "diagnostic_action": "Start systematic re-optimisation.",
        "recommended_fix": "Begin fresh from retention optimisation and escalate sequentially.",
        "rationale": "Multiple failures mean simple fixes may not be enough.",
    },
    ">7|<20|N/A": {
        "rule_id": 10,
        "scenario": "X1",
        "root_cause": "Unexpected extra peaks.",
        "diagnostic_action": "Run blank injection and solvent blank.",
        "recommended_fix": "Identify contamination or sample-related extra peaks before method troubleshooting.",
        "rationale": "Extra peaks must be identified first.",
    },
    ">7|>20|N/A": {
        "rule_id": 11,
        "scenario": "X2",
        "root_cause": "Extra peaks plus extended run.",
        "diagnostic_action": "Run blank and solvent blank.",
        "recommended_fix": "Clean system or add stronger wash step if needed.",
        "rationale": "Extra late peaks may be contamination or carryover.",
    },
}

def fire_master_rule(composite_key):
    return LOOKUP_MASTER.get(composite_key, {
        "rule_id": "NO_MATCH",
        "scenario": "NO_MATCH",
        "root_cause": f"No rule found for composite key: {composite_key}",
        "diagnostic_action": "Check inputs and rule dictionary.",
        "recommended_fix": "Add or correct this composite key in LOOKUP_MASTER.",
        "rationale": "Every valid input should map to one deterministic rule.",
    })

def determine_lever_state(tried_retention, tried_selectivity, tried_efficiency, tried_gradient):
    if tried_gradient and not (tried_retention or tried_selectivity or tried_efficiency):
        return "L6", "Restart with isocratic optimisation before using gradient changes."
    if tried_retention and tried_selectivity and tried_efficiency and tried_gradient:
        return "L5", "Escalate to method redevelopment."
    if tried_retention and tried_selectivity and tried_efficiency:
        return "L4", "Try gradient elution."
    if tried_retention and tried_selectivity:
        return "L3", "Try efficiency improvements."
    if tried_retention:
        return "L2", "Try selectivity changes."
    return "L1", "Try retention first."

st.title("🧪 HPLC Method Troubleshooting Decision Tool")
st.caption("Streamlit website version — deterministic Python calculation engine")

with st.expander("How to use", expanded=True):
    st.write("""
    Enter method specifications, edit the peak table, choose the levers already tried,
    then click **Run Analysis**.
    """)

st.sidebar.header("Method Specifications")

run_time_spec = st.sidebar.number_input("Run Time Specification (min)", min_value=0.01, value=20.0, step=0.5)
rs_spec = st.sidebar.number_input("Resolution Specification Rs", min_value=0.01, value=1.4, step=0.1)
observed_peak_count = st.sidebar.number_input("Observed Peak Count", min_value=0, value=7, step=1)
total_run_time = st.sidebar.number_input("Total Run Time (min)", min_value=0.0, value=18.0, step=0.5)
void_time = st.sidebar.number_input("Void Time t0 (min)", min_value=0.0, value=1.0, step=0.1)
column_length = st.sidebar.number_input("Column Length (mm)", min_value=0.0, value=150.0, step=10.0)

st.sidebar.header("Lever History")
tried_retention = st.sidebar.checkbox("Retention tried")
tried_selectivity = st.sidebar.checkbox("Selectivity tried")
tried_efficiency = st.sidebar.checkbox("Efficiency tried")
tried_gradient = st.sidebar.checkbox("Gradient tried")

st.subheader("Peak Table Input")

default_data = pd.DataFrame({
    "Peak": ["Uracil", "C1", "C2", "C3", "C4", "C5", "C6"],
    "Retention Time": [1.0, 3.0, 5.2, 7.6, 10.1, 13.0, 16.5],
    "USP Width": [0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
    "Width at Half Height": [0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4],
})

peak_table = st.data_editor(default_data, num_rows="fixed", use_container_width=True)

if st.button("Run Analysis", type="primary"):
    peaks = []

    for _, row in peak_table.iterrows():
        label = str(row["Peak"])
        tr = to_float(row["Retention Time"])
        usp_width = to_float(row["USP Width"])
        half_width = to_float(row["Width at Half Height"])

        k_value = None if label.lower() == "uracil" else calculate_k(tr, void_time)
        n_value = calculate_n(tr, half_width)
        hetp_value = calculate_hetp(column_length, n_value)

        peaks.append({
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
        })

    rs_rows = []
    for i in range(len(peaks) - 1):
        p1, p2 = peaks[i], peaks[i + 1]
        rs_value = calculate_rs(p1["tR"], p2["tR"], p1["USP Width"], p2["USP Width"])
        rs_rows.append({
            "Pair": f'{p1["Peak"]}-{p2["Peak"]}',
            "Rs": rs_value,
            "Status": status_rs(rs_value, rs_spec),
        })

    alpha_rows = []
    analytes = peaks[1:]
    for i in range(len(analytes) - 1):
        p1, p2 = analytes[i], analytes[i + 1]
        alpha_value = calculate_alpha(p1["k"], p2["k"])
        alpha_rows.append({
            "Pair": f'{p1["Peak"]}-{p2["Peak"]}',
            "Alpha": alpha_value,
            "Status": status_alpha(alpha_value),
        })

    rs_values = [r["Rs"] for r in rs_rows]
    key_data = build_composite_key(int(observed_peak_count), total_run_time, rs_values, run_time_spec, rs_spec)
    rule = fire_master_rule(key_data["composite_key"])
    lever_state, lever_action = determine_lever_state(tried_retention, tried_selectivity, tried_efficiency, tried_gradient)

    st.success("Analysis complete")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Composite Key", key_data["composite_key"])
    col2.metric("Peak Category", key_data["peak_cat"])
    col3.metric("Runtime Category", key_data["runtime_cat"])
    col4.metric("Rs Category", key_data["rs_cat"])

    st.subheader("Fired Rule")
    st.info(f"""
    **Rule ID:** {rule["rule_id"]}  
    **Scenario:** {rule["scenario"]}  
    **Root Cause:** {rule["root_cause"]}  
    **Diagnostic Action:** {rule["diagnostic_action"]}  
    **Recommended Fix:** {rule["recommended_fix"]}  
    **Rationale:** {rule["rationale"]}
    """)

    st.subheader("Lever Tracker")
    st.warning(f"""
    **Lever State:** {lever_state}  
    **Next Action:** {lever_action}
    """)

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
    st.info("Enter data, then click **Run Analysis**.")
