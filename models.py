from __future__ import annotations
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class ValidationLog(db.Model):
    __tablename__ = "validation_log"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    method_name = db.Column(db.String(160), nullable=False, default="Untitled method")
    run_time_spec = db.Column(db.Float, nullable=False, default=20.0)
    rs_spec = db.Column(db.Float, nullable=False, default=1.4)
    lever_state = db.Column(db.String(8), nullable=False, default="L1")
    peak_count = db.Column(db.Integer, nullable=True)
    rs_min = db.Column(db.Float, nullable=True)
    fired_rule_id = db.Column(db.Integer, nullable=True)
    recommendation_summary = db.Column(db.Text, nullable=True)
    actual_outcome = db.Column(db.Text, nullable=True)
    match = db.Column(db.String(16), nullable=False, default="PENDING")
    notes = db.Column(db.Text, nullable=True)


class Chromatogram(db.Model):
    __tablename__ = "chromatogram"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    method_name = db.Column(db.String(160), nullable=False, default="Untitled method")
    peak_count = db.Column(db.Integer, nullable=True)
    rs_min = db.Column(db.Float, nullable=True)
    fired_rule_id = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    validation_log_id = db.Column(db.Integer, db.ForeignKey("validation_log.id"), nullable=True)
    validation_log = db.relationship("ValidationLog", backref="chromatograms")
