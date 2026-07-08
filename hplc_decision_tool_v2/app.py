from __future__ import annotations
import csv
import io
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, Response, flash, redirect, render_template, request, session, url_for

from hplc_engine import PEAK_LABELS, PeakData, analyse_run, determine_lever_state, to_float, to_int
from models import Chromatogram, ValidationLog, db
from rules import MASTER_RULES, RESOLUTION_RULES


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///hplc_decision_tool.sqlite3"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.context_processor
    def inject_globals() -> dict:
        return {"PEAK_LABELS": PEAK_LABELS, "now": datetime.utcnow()}

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/documentation")
    def documentation():
        return render_template("documentation.html", master_rules=MASTER_RULES, resolution_rules=RESOLUTION_RULES)

    @app.route("/wizard/specs", methods=["GET", "POST"])
    def specs():
        data = session.get("specs", {"method_name": "", "run_time_spec": 20, "rs_spec": 1.4})
        errors: Dict[str, str] = {}
        if request.method == "POST":
            method_name = request.form.get("method_name", "").strip() or "Untitled method"
            run_time_spec = to_float(request.form.get("run_time_spec"))
            rs_spec = to_float(request.form.get("rs_spec"))
            if run_time_spec is None or run_time_spec <= 0:
                errors["run_time_spec"] = "Value must be a positive number."
            if rs_spec is None or rs_spec <= 0:
                errors["rs_spec"] = "Value must be a positive number."
            data = {"method_name": method_name, "run_time_spec": request.form.get("run_time_spec"), "rs_spec": request.form.get("rs_spec")}
            if not errors:
                session["specs"] = {"method_name": method_name, "run_time_spec": run_time_spec, "rs_spec": rs_spec}
                return redirect(url_for("peak_table"))
        return render_template("specs.html", data=data, errors=errors)

    @app.route("/wizard/peak-table", methods=["GET", "POST"])
    def peak_table():
        data = session.get("peak_table", default_peak_table())
        errors: Dict[str, str] = {}
        warnings: List[str] = []
        if request.method == "POST":
            data = collect_peak_table_form(request.form)
            observed_peak_count = to_int(data.get("observed_peak_count"))
            total_run_time = to_float(data.get("total_run_time"))
            void_time = to_float(data.get("void_time"))
            column_length = to_float(data.get("column_length"))
            peaks = [PeakData.from_form(i, request.form) for i in range(len(PEAK_LABELS))]

            if observed_peak_count is None or not (0 <= observed_peak_count <= 15):
                errors["observed_peak_count"] = "Peak count must be an integer between 0 and 15."
            if total_run_time is None or total_run_time <= 0:
                errors["total_run_time"] = "Total run time must be a positive number."
            if void_time is None or void_time <= 0:
                errors["void_time"] = "Void time must be a positive number."
            if column_length is not None and column_length <= 0:
                errors["column_length"] = "Column length must be positive if provided."

            analyte_rts = [p.retention_time for p in peaks[1:] if p.retention_time is not None]
            if void_time is not None and any(rt <= void_time for rt in analyte_rts):
                errors["void_time"] = "Void time must be less than all analyte retention times."

            rts = [p.retention_time for p in peaks if p.retention_time is not None]
            if rts and rts != sorted(rts):
                warnings.append("Retention times are not in ascending order; verify data entry.")

            for i in range(len(peaks) - 1):
                p1, p2 = peaks[i], peaks[i + 1]
                if p1.retention_time is not None and p2.retention_time is not None:
                    spacing = abs(p2.retention_time - p1.retention_time)
                    if (p1.usp_width is not None and p1.usp_width > spacing) or (p2.usp_width is not None and p2.usp_width > spacing):
                        warnings.append(f"USP width exceeds inter-peak spacing around {p1.label}–{p2.label}; possible data entry error.")
                        break

            data["peaks"] = [p.to_dict() for p in peaks]
            if not errors:
                session["peak_table"] = data
                if warnings:
                    session["warnings"] = warnings
                return redirect(url_for("lever_history"))
        return render_template("peak_table.html", data=data, errors=errors, warnings=warnings)

    @app.route("/wizard/lever-history", methods=["GET", "POST"])
    def lever_history():
        data = session.get("lever_history", default_lever_history())
        if request.method == "POST":
            data = {
                "retention_tried": bool(request.form.get("retention_tried")),
                "selectivity_tried": bool(request.form.get("selectivity_tried")),
                "efficiency_tried": bool(request.form.get("efficiency_tried")),
                "gradient_tried": bool(request.form.get("gradient_tried")),
                "retention_notes": request.form.get("retention_notes", ""),
                "selectivity_notes": request.form.get("selectivity_notes", ""),
                "efficiency_notes": request.form.get("efficiency_notes", ""),
                "gradient_notes": request.form.get("gradient_notes", ""),
            }
            session["lever_history"] = data
            return redirect(url_for("run_analysis"))
        lever = determine_lever_state(data.get("retention_tried"), data.get("selectivity_tried"), data.get("efficiency_tried"), data.get("gradient_tried"))
        return render_template("lever_history.html", data=data, lever=lever.to_dict())

    @app.route("/run-analysis")
    def run_analysis():
        payload = build_payload_from_session()
        result = analyse_run(payload)
        lever = determine_lever_state(
            payload["lever_history"].get("retention_tried"),
            payload["lever_history"].get("selectivity_tried"),
            payload["lever_history"].get("efficiency_tried"),
            payload["lever_history"].get("gradient_tried"),
        )
        result["leverState"] = lever.to_dict()
        result["payload"] = payload
        result["plainExplanation"] = build_plain_explanation(result)
        session["last_result"] = result
        return redirect(url_for("results"))

    @app.route("/results")
    def results():
        result = session.get("last_result")
        if not result:
            flash("No analysis result yet. Start from the wizard.", "warning")
            return redirect(url_for("specs"))
        warnings = session.pop("warnings", [])
        return render_template("results.html", result=result, warnings=warnings)

    @app.route("/log-current", methods=["POST"])
    def log_current():
        result = session.get("last_result")
        if not result:
            flash("No current analysis to log.", "warning")
            return redirect(url_for("results"))
        payload = result["payload"]
        rule = result.get("rule") or {}
        calculated = result.get("calculated") or {}
        entry = ValidationLog(
            method_name=payload.get("method_name") or "Untitled method",
            run_time_spec=float(payload.get("run_time_spec") or 20),
            rs_spec=float(payload.get("rs_spec") or 1.4),
            lever_state=result.get("leverState", {}).get("lever_state", "L1"),
            peak_count=payload.get("observed_peak_count"),
            rs_min=calculated.get("rsMin"),
            fired_rule_id=rule.get("rule_id"),
            recommendation_summary=rule.get("recommended_fix"),
            actual_outcome=request.form.get("actual_outcome") or None,
            match=request.form.get("match") or "PENDING",
            notes=request.form.get("notes") or None,
        )
        db.session.add(entry)
        db.session.commit()
        flash("Analysis saved to the validation log.", "success")
        return redirect(url_for("validation_log"))

    @app.route("/validation-log", methods=["GET", "POST"])
    def validation_log():
        if request.method == "POST":
            entry_id = to_int(request.form.get("entry_id"))
            entry = db.session.get(ValidationLog, entry_id) if entry_id else None
            if entry:
                entry.actual_outcome = request.form.get("actual_outcome") or None
                entry.match = request.form.get("match") or "PENDING"
                entry.notes = request.form.get("notes") or None
                db.session.commit()
                flash("Validation log entry updated.", "success")
        entries = ValidationLog.query.order_by(ValidationLog.timestamp.desc()).all()
        return render_template("validation_log.html", entries=entries)

    @app.route("/validation-log/export.csv")
    def export_validation_log():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Log ID", "Timestamp", "Method Name", "Run Time Spec", "Rs Spec", "Lever State", "Peak Count", "Rs_min", "Fired Rule", "Recommendation", "Actual Outcome", "Match", "Notes"])
        for e in ValidationLog.query.order_by(ValidationLog.timestamp.desc()).all():
            writer.writerow([e.id, e.timestamp.isoformat(), e.method_name, e.run_time_spec, e.rs_spec, e.lever_state, e.peak_count, e.rs_min, e.fired_rule_id, e.recommendation_summary, e.actual_outcome, e.match, e.notes])
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=validation_log.csv"})

    @app.route("/chromatograms", methods=["GET", "POST"])
    def chromatograms():
        if request.method == "POST":
            chrom = Chromatogram(
                method_name=request.form.get("method_name") or "Untitled method",
                peak_count=to_int(request.form.get("peak_count")),
                rs_min=to_float(request.form.get("rs_min")),
                fired_rule_id=to_int(request.form.get("fired_rule_id")),
                notes=request.form.get("notes") or None,
            )
            db.session.add(chrom)
            db.session.commit()
            flash("Chromatogram record added.", "success")
            return redirect(url_for("chromatograms"))

        query = Chromatogram.query
        method_name = request.args.get("method_name", "").strip()
        fired_rule = request.args.get("fired_rule", "").strip()
        if method_name:
            query = query.filter(Chromatogram.method_name.ilike(f"%{method_name}%"))
        if fired_rule:
            query = query.filter(Chromatogram.fired_rule_id == to_int(fired_rule))
        records = query.order_by(Chromatogram.created_at.desc()).all()
        return render_template("chromatograms.html", records=records, method_name=method_name, fired_rule=fired_rule)

    return app


def default_peak_table() -> Dict[str, Any]:
    return {
        "observed_peak_count": "7",
        "total_run_time": "20",
        "void_time": "",
        "column_length": "150",
        "reference_total_area": "",
        "reference_peak_area": "",
        "expected_last_elution_time": "",
        "expected_void_time": "",
        "spiking_result": "not_done",
        "peaks": [PeakData(i, PEAK_LABELS[i]).to_dict() for i in range(len(PEAK_LABELS))],
    }


def default_lever_history() -> Dict[str, Any]:
    return {
        "retention_tried": False,
        "selectivity_tried": False,
        "efficiency_tried": False,
        "gradient_tried": False,
        "retention_notes": "",
        "selectivity_notes": "",
        "efficiency_notes": "",
        "gradient_notes": "",
    }


def collect_peak_table_form(form) -> Dict[str, Any]:
    return {
        "observed_peak_count": form.get("observed_peak_count"),
        "total_run_time": form.get("total_run_time"),
        "void_time": form.get("void_time"),
        "column_length": form.get("column_length"),
        "reference_total_area": form.get("reference_total_area"),
        "reference_peak_area": form.get("reference_peak_area"),
        "expected_last_elution_time": form.get("expected_last_elution_time"),
        "expected_void_time": form.get("expected_void_time"),
        "spiking_result": form.get("spiking_result") or "not_done",
    }


def build_payload_from_session() -> Dict[str, Any]:
    specs = session.get("specs", {"method_name": "Untitled method", "run_time_spec": 20, "rs_spec": 1.4})
    peak_table = session.get("peak_table", default_peak_table())
    lever_history = session.get("lever_history", default_lever_history())
    return {
        "method_name": specs.get("method_name") or "Untitled method",
        "run_time_spec": specs.get("run_time_spec") or 20,
        "rs_spec": specs.get("rs_spec") or 1.4,
        "observed_peak_count": to_int(peak_table.get("observed_peak_count")),
        "total_run_time": to_float(peak_table.get("total_run_time")),
        "void_time": to_float(peak_table.get("void_time")),
        "column_length": to_float(peak_table.get("column_length")),
        "reference_total_area": peak_table.get("reference_total_area"),
        "reference_peak_area": peak_table.get("reference_peak_area"),
        "expected_last_elution_time": peak_table.get("expected_last_elution_time"),
        "expected_void_time": peak_table.get("expected_void_time"),
        "spiking_result": peak_table.get("spiking_result"),
        "peaks": peak_table.get("peaks") or [],
        "lever_history": lever_history,
    }


def build_plain_explanation(result: Dict[str, Any]) -> str:
    rule = result.get("rule")
    if not rule:
        return "No matrix rule fired yet. Please complete the required input fields."
    resolution = result.get("resolutionRule")
    parts = [
        f"The deterministic engine fired Rule {rule['rule_id']} using composite key {result.get('lookupKey')}.",
        f"Root cause: {rule['root_cause_category']}",
        f"Recommended fix: {rule['recommended_fix']}",
        f"Lever tracker adjustment: {result.get('leverState', {}).get('next_action', 'No lever adjustment available')}",
    ]
    if resolution:
        parts.append(f"The resolution sub-matrix also fired Rule {resolution['rule_id']}: {resolution['diagnosis']}. Recommended action: {resolution['recommended_fix']}")
    return "\n".join(parts)


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
