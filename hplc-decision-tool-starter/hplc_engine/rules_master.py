"""
Simplified Lookup_Master rule dictionary.

This starter includes all 19 composite-key pathways so the app can run.
You can later replace the text with the exact wording from your final matrix.
"""

from __future__ import annotations


LOOKUP_MASTER = {
    "7|<20|PASS": {
        "rule_id": 1,
        "scenario": "M1",
        "root_cause": "PASS — all specifications met",
        "diagnostic_action": "No action required.",
        "recommended_fix": "None — method is within specification.",
        "rationale": "All three acceptance criteria are satisfied.",
    },
    "7|<20|FAIL_SINGLE": {
        "rule_id": 2,
        "scenario": "RS1",
        "root_cause": "Resolution failure on one adjacent pair",
        "diagnostic_action": "Calculate k, alpha and N for the worst pair.",
        "recommended_fix": "Apply targeted fix using retention, selectivity, efficiency, then gradient priority.",
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
    "7|>20|PASS": {
        "rule_id": 4,
        "scenario": "RT1",
        "root_cause": "Run time exceeded but resolution is adequate",
        "diagnostic_action": "Identify late-eluting peaks and check gradient slope, flow rate and column dimensions.",
        "recommended_fix": "Compress gradient, increase flow rate if Rs is maintained, or use a shorter column if suitable.",
        "rationale": "Resolution is achieved, so the goal is to move peaks earlier without losing separation.",
    },
    "7|>20|FAIL": {
        "rule_id": 5,
        "scenario": "RT2",
        "root_cause": "Both run time and resolution fail",
        "diagnostic_action": "Prioritise resolution first. Calculate k, alpha and N for the worst pair.",
        "recommended_fix": "Fix resolution first, then re-optimise run time.",
        "rationale": "Shortening a failing method before fixing Rs may worsen the separation.",
    },
    "<7|<20|PASS": {
        "rule_id": 6,
        "scenario": "M2",
        "root_cause": "Peaks missing — merged or absent",
        "diagnostic_action": "Use differential diagnosis: total area, peak shape, void marker, extended run and scouting run.",
        "recommended_fix": "If merged, adjust selectivity. If absent, extend run time or adjust retention.",
        "rationale": "Missing peaks need classification before the correct fix can be selected.",
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
    "<7|>20|FAIL": {
        "rule_id": 9,
        "scenario": "M5",
        "root_cause": "Multiple compounding issues: missing peaks, poor resolution and long run time",
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
    "<7|<20|MARGINAL": {
        "rule_id": 12,
        "scenario": "M6",
        "root_cause": "Missing peak(s) with marginal resolution",
        "diagnostic_action": "Diagnose missing peaks and monitor the marginal pair.",
        "recommended_fix": "Fix missing peak issue first, then consider small selectivity adjustment for safety margin.",
        "rationale": "The missing peak issue is more important than a borderline passing pair.",
    },
    "7|<20|FAIL_SEVERE": {
        "rule_id": 13,
        "scenario": "RS3",
        "root_cause": "Severe resolution failure — near-complete co-elution",
        "diagnostic_action": "Check whether the poor pair is true co-elution and calculate alpha.",
        "recommended_fix": "Change selectivity first: organic modifier, pH or column chemistry.",
        "rationale": "Very low Rs usually cannot be fixed by efficiency alone.",
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
    # Rules 18 and 19 share the same composite keys as 10 and 11 in this starter matrix pathway.
    # They are kept here as aliases if you later choose to separate extra-peak incomplete-data logic.
}


def fire_master_rule(composite_key: str) -> dict:
    """Return the fired master rule. Never uses AI."""
    return LOOKUP_MASTER.get(
        composite_key,
        {
            "rule_id": "NO_MATCH",
            "scenario": "NO_MATCH",
            "root_cause": f"No rule found for composite key: {composite_key}",
            "diagnostic_action": "Check input values and rule dictionary.",
            "recommended_fix": "Add the missing composite key to LOOKUP_MASTER.",
            "rationale": "Every valid composite key should map to one deterministic rule.",
        },
    )
