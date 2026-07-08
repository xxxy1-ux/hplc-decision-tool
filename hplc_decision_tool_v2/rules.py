from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


@dataclass(frozen=True)
class MatrixRule:
    rule_id: int
    peak_cat: str
    runtime_cat: str
    rs_cat: str
    composite_key: str
    root_cause_category: str
    diagnostic_action: str
    recommended_fix: str
    fix_rationale: str
    scenario_code: str = ""
    active_lookup: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ResolutionSubRule:
    rule_id: int
    rs_range: str
    k_condition: str
    alpha_condition: str
    n_condition: str
    composite_key: str
    diagnosis: str
    recommended_fix: str
    why_this_fix: str

    def to_dict(self) -> dict:
        return asdict(self)


MASTER_RULES: List[MatrixRule] = [
    MatrixRule(1, "7", "<20", "PASS", "7|<20|PASS", "PASS — all specifications met", "No action required", "None — method is within specification", "All three acceptance criteria are satisfied.", "P1"),
    MatrixRule(2, "7", "<20", "FAIL_SINGLE", "7|<20|FAIL_SINGLE", "Resolution failure on one specific adjacent pair", "Calculate k, α, and N for the worst pair. Identify whether the deficit is retention, selectivity, or efficiency using the Resolution Troubleshooting Matrix", "Apply the fix matching the diagnosis. Follow fix priority order: retention → selectivity → efficiency → gradient", "Targeted fix on the worst pair: other pairs already pass, so a focused adjustment is sufficient.", "RS1"),
    MatrixRule(3, "7", "<20", "FAIL_MULTI", "7|<20|FAIL_MULTI", "Systemic resolution deficit", "Check column age and condition (plate count test). Review mobile phase preparation. Verify flow rate and temperature", "Replace column if N has degraded significantly; re-prepare mobile phase; verify instrument settings", "Multiple failing pairs suggest a global method or system issue rather than one isolated pair.", "RS2"),
    MatrixRule(4, "7", ">20", "PASS", "7|>20|PASS", "Run time exceeded — resolution is adequate", "Identify which peaks are late-eluting. Check gradient slope, flow rate, and column dimensions", "Compress gradient (increase slope of %B ramp); increase flow rate (verify Rs is maintained); use shorter column if plate count permits", "Resolution is already achieved: the goal is to move peaks earlier without losing the separation.", "RT1"),
    MatrixRule(5, "7", ">20", "FAIL", "7|>20|FAIL", "Both run time and resolution fail", "Prioritise resolution first. Calculate k, α, N for the worst pair", "Address resolution first using the Resolution Troubleshooting Matrix. Once Rs ≥ 1.4 is achieved, re-optimise run time", "Fixing run time before resolution may make separation worse; resolve the critical pair first.", "M1"),
    MatrixRule(6, "<7", "<20", "PASS", "<7|<20|PASS", "Peaks missing — merged or absent", "Apply differential diagnosis: check total peak area vs reference, peak shape, void marker, extended blank run, and gradient scouting run", "If merged: adjust selectivity (pH, organic modifier ratio), then efficiency, then column chemistry. If absent: extend run time or increase retention", "Missing peaks require differential diagnosis because merged and absent peaks require opposite fixes.", "M2"),
    MatrixRule(7, "<7", "<20", "FAIL", "<7|<20|FAIL", "Peaks missing AND poor resolution among remaining peaks — likely co-elution", "Strong indicator of co-elution: two or more compounds share a single peak. Confirm with area comparison and gradient scouting", "Apply co-elution fixes: adjust selectivity first (pH, organic modifier, column chemistry), then efficiency", "Missing peaks plus poor remaining resolution strongly suggest co-elution rather than simple late elution.", "M3"),
    MatrixRule(8, "<7", ">20", "PASS", "<7|>20|PASS", "Peaks likely beyond run window — strongly retained compounds not eluting in time", "Run extended blank or gradient scouting run to locate missing peaks. Check k values for eluting peaks", "Extend run time; flatten gradient at end; reduce organic strength at start to allow earlier elution of strongly retained analytes", "Missing peaks with long run time suggests late-eluting compounds are not recovered within the current window.", "M4"),
    MatrixRule(9, "<7", ">20", "FAIL", "<7|>20|FAIL", "Multiple compounding issues — missing peaks, poor resolution, and long run time", "Systematic re-optimisation required. Start with retention assessment (k for all peaks), then selectivity, then efficiency", "Begin fresh from Priority 1 (retention): adjust organic % and pH to optimise k for all analytes. Work through escalation ladder sequentially. If exhausted, escalate to method redevelopment", "Multiple simultaneous failures indicate the current method conditions are far from optimal: incremental single-parameter changes are unlikely to resolve all issues.", "M5"),
    MatrixRule(10, ">7", "<20", "N/A", ">7|<20|N/A", "Unexpected extra peaks — possible impurity, degradation product, or system contaminant", "Run a blank injection (mobile phase only). Run a solvent blank (sample diluent only). Compare with reference chromatogram to identify extra peak(s)", "If blank shows extra peak: clean system, replace contaminated mobile phase or column. If sample-related: review sample preparation, check analyte stability, verify sample diluent compatibility", "Extra peaks must be identified before resolution optimisation because the issue may be contamination rather than separation failure.", "E1"),
    MatrixRule(11, ">7", ">20", "N/A", ">7|>20|N/A", "Extra peaks plus extended run — system or sample contamination with late-eluting interferent", "Run blank and solvent blank. If extra peak is late-eluting, suspect column bleed, mobile phase additive, or sample matrix component", "Clean system. If late-eluting contaminant persists, add a wash step at end of gradient, increase final %B, or add column wash between injections", "Extra late peaks can extend run time and confound method optimisation; eliminate contamination first.", "E2"),
    MatrixRule(12, "<7", "<20", "MARGINAL", "<7|<20|MARGINAL", "Missing peak(s) with marginal resolution on a remaining pair — borderline specification", "Apply differential diagnosis for missing peaks. Monitor the marginal pair: calculate k and α to assess robustness", "Fix missing peak issue first. For the marginal pair, evaluate whether a small selectivity adjustment would provide a safety margin without disrupting other separations", "Borderline resolution may become a failure after the missing peak is recovered; treat the missing peak first, then build robustness.", "M6"),
    MatrixRule(13, "7", "<20", "FAIL_SEVERE", "7|<20|FAIL_SEVERE", "Severe resolution failure — near-complete co-elution of at least one pair", "Confirm the poorly resolved pair is not a single compound with a split peak (check injection volume, column void). Calculate α; if α ≈ 1.0, selectivity change is mandatory", "Do not attempt incremental efficiency fixes. Change selectivity first: switch organic modifier, change pH by ≥ 1 unit, or change column chemistry entirely", "Rs < 0.8 cannot be fixed by efficiency alone: the theoretical maximum Rs achievable with α ≈ 1.0 is too low regardless of plate count.", "RS3"),
    MatrixRule(14, "7", "<20", "N/A", "7|<20|N/A", "Peaks and run time on spec. Enter peak data (retention times and widths) to assess resolution.", "Enter retention time and USP width for all 7 peaks to enable Rs calculation and full diagnosis.", "Enter peak data to complete the assessment.", "No resolution diagnosis is possible until retention times and widths are entered.", "D1"),
    MatrixRule(15, "7", ">20", "N/A", "7|>20|N/A", "Run time exceeded. Enter peak data to assess resolution.", "Enter retention time and USP width for all 7 peaks. Run time already exceeds 20 min specification.", "Enter peak data to complete the assessment.", "Run-time optimisation should be delayed until resolution status is known.", "D2"),
    MatrixRule(16, "<7", "<20", "N/A", "<7|<20|N/A", "Fewer than 7 peaks observed. Enter peak data for differential diagnosis (merged vs absent).", "Enter peak data to determine whether missing peaks are merged (co-elution) or absent (not eluted).", "Enter peak data to complete the assessment.", "The merged-versus-absent pathway requires evidence from retention, area, and peak-shape data.", "D3"),
    MatrixRule(17, "<7", ">20", "N/A", "<7|>20|N/A", "Fewer than 7 peaks AND run time exceeded. Enter peak data for full diagnosis.", "Enter peak data. Multiple issues suspected: missing peaks and extended run time.", "Enter peak data to complete the assessment.", "Missing peaks and extended run time need peak evidence before selecting a corrective lever.", "D4"),
    # Rules 18 and 19 intentionally duplicate the same composite keys as 10 and 11 in the supplied matrix.
    # They are preserved as reference guidance, but not used as active dictionary entries.
    MatrixRule(18, ">7", "<20", "N/A", ">7|<20|N/A", "Extra peaks detected. Run blank and solvent blank to identify contaminants before entering peak data.", "Run blank injection first. Extra peaks may indicate contamination, not a method issue.", "Identify extra peaks before proceeding with resolution assessment.", "This is duplicate guidance for the >7/<20 extra-peak pathway.", "E1b", active_lookup=False),
    MatrixRule(19, ">7", ">20", "N/A", ">7|>20|N/A", "Extra peaks AND run time exceeded. System contamination suspected.", "Run blank and solvent blank. Clean system if contamination confirmed. Address run time after.", "Identify and eliminate extra peaks first, then optimise run time.", "This is duplicate guidance for the >7/>20 extra-peak pathway.", "E2b", active_lookup=False),
]

ACTIVE_MASTER_BY_KEY: Dict[str, MatrixRule] = {r.composite_key: r for r in MASTER_RULES if r.active_lookup}
DUPLICATE_GUIDANCE_BY_KEY: Dict[str, List[MatrixRule]] = {}
for rule in MASTER_RULES:
    if not rule.active_lookup:
        DUPLICATE_GUIDANCE_BY_KEY.setdefault(rule.composite_key, []).append(rule)

RESOLUTION_RULES: List[ResolutionSubRule] = [
    ResolutionSubRule(1, "SEVERE", "LOW", "ANY", "ANY", "SEVERE|LOW|ANY", "Poor retention: peaks elute too close to void volume", "Increase k: reduce organic solvent % in mobile phase; adjust pH to increase analyte retention; raise column temperature if retention increases with temperature for these analytes", "Peaks near the void are compressed into a narrow elution window; improving retention spreads them across a wider time range, directly increasing resolution"),
    ResolutionSubRule(2, "SEVERE", "ADEQUATE", "LOW", "ANY", "SEVERE|ADEQUATE|LOW", "Selectivity failure: column chemistry cannot distinguish the two analytes", "Change mobile phase composition: adjust pH, change buffer type, alter organic modifier (methanol to acetonitrile or vice versa), or switch stationary phase chemistry (C18 to phenyl-hexyl, cyano, or HILIC)", "When alpha approaches 1.0, the two analytes behave identically on the column: no amount of efficiency improvement can resolve peaks with identical selectivity"),
    ResolutionSubRule(3, "MODERATE", "ADEQUATE", "ADEQUATE", "ANY", "MODERATE|ADEQUATE|ADEQUATE", "Efficiency problem: sufficient selectivity exists but peaks are too broad", "Reduce flow rate; use a column with smaller particle size (e.g. 5 μm to 3 μm or sub-2 μm); increase column length; check for extra-column dead volume (tubing, fittings, detector cell)", "Selectivity provides the separation; efficiency determines how sharp each peak is. Sharpening peaks at existing spacing pushes Rs above 1.4"),
    ResolutionSubRule(4, "MODERATE", "ADEQUATE", "LOW", "ANY", "MODERATE|ADEQUATE|LOW", "Combined selectivity and efficiency deficit", "Address selectivity first (mobile phase composition change), then optimise efficiency if Rs remains below 1.4 after selectivity improvement", "Priority order: selectivity before efficiency. A small gain in alpha amplifies the benefit of subsequent efficiency improvements, whereas efficiency alone cannot overcome near-identical selectivity"),
    ResolutionSubRule(5, "ANY", "EARLY_LOW", "ANY", "ANY", "ANY|EARLY_LOW|ANY", "Early-eluting peaks crowded near void", "Increase retention of early peaks: lower organic solvent %; adjust pH to retain polar or ionisable analytes; consider adding an ion-pairing reagent", "Early peaks have limited chromatographic space between the void and subsequent peaks; increasing their retention moves them into a region with more separation capacity"),
    ResolutionSubRule(6, "ANY", "LATE_HIGH", "ANY", "ANY", "ANY|LATE_HIGH|ANY", "Late-eluting peaks compressed: gradient too steep or column overloaded", "Flatten gradient slope at end of run; reduce injection volume or concentration; extend total run time to spread late-eluting peaks; add an isocratic hold before the steep gradient region", "Late peaks are compressed because the increasing eluent strength elutes closely-retained compounds simultaneously; a shallower gradient provides more time for differential elution"),
]

RESOLUTION_RULES_BY_KEY: Dict[str, ResolutionSubRule] = {r.composite_key: r for r in RESOLUTION_RULES}


def lookup_master_rule(peak_cat: str, runtime_cat: str, rs_cat: str) -> tuple[Optional[MatrixRule], str, List[MatrixRule]]:
    """Return active matrix rule, the lookup key used, and preserved duplicate guidance."""
    if peak_cat == ">7":
        # The supplied matrix routes all extra-peak scenarios through the contamination path first.
        key = f"{peak_cat}|{runtime_cat}|N/A"
        return ACTIVE_MASTER_BY_KEY.get(key), key, DUPLICATE_GUIDANCE_BY_KEY.get(key, [])

    exact_key = f"{peak_cat}|{runtime_cat}|{rs_cat}"
    if exact_key in ACTIVE_MASTER_BY_KEY:
        return ACTIVE_MASTER_BY_KEY[exact_key], exact_key, DUPLICATE_GUIDANCE_BY_KEY.get(exact_key, [])

    if rs_cat.startswith("FAIL"):
        generic_key = f"{peak_cat}|{runtime_cat}|FAIL"
        if generic_key in ACTIVE_MASTER_BY_KEY:
            return ACTIVE_MASTER_BY_KEY[generic_key], generic_key, DUPLICATE_GUIDANCE_BY_KEY.get(generic_key, [])

    return None, exact_key, []


def lookup_resolution_rule(rs_range: str, k_condition: str, alpha_condition: str) -> Optional[ResolutionSubRule]:
    candidates = [
        f"{rs_range}|{k_condition}|{alpha_condition}",
        f"{rs_range}|{k_condition}|ANY",
        f"{rs_range}|ANY|{alpha_condition}",
        f"ANY|{k_condition}|{alpha_condition}",
        f"ANY|{k_condition}|ANY",
        f"{rs_range}|ANY|ANY",
    ]
    for key in candidates:
        if key in RESOLUTION_RULES_BY_KEY:
            return RESOLUTION_RULES_BY_KEY[key]
    return None
