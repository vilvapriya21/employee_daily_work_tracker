"""
Timer Trigger — generate_summary
Schedule: every 2 hours  →  TIMER_SCHEDULE = "0 0 */2 * * *"

Reads employee_logs.json and writes summary.json with:
  • total_employees_submitted  — count of unique employees who submitted
  • total_hours_worked         — sum of all hours
  • average_hours              — total / unique employees
  • employees_less_than_4_hrs  — list of names who worked fewer than 4 h
"""

import json
import logging
import os
from datetime import datetime

import azure.functions as func

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE     = os.path.join(BASE_DIR, "employee_logs.json")
SUMMARY_FILE  = os.path.join(BASE_DIR, "summary.json")

logger = logging.getLogger(__name__)


def _load_logs() -> list:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def main(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logger.warning("Timer is running late!")

    logger.info("generate_summary triggered at %s", datetime.utcnow().isoformat())

    logs = _load_logs()

    if not logs:
        logger.info("No logs found — writing empty summary.")
        summary = {
            "total_employees_submitted": 0,
            "total_hours_worked":        0,
            "average_hours":             0,
            "employees_less_than_4_hrs": [],
            "generated_at":              datetime.utcnow().isoformat() + "Z",
            "note":                      "No work logs have been submitted yet.",
        }
        _write_summary(summary)
        return

    # ── Aggregate per unique employee (by ID) ─────────────────────────────────
    employee_totals: dict[str, dict] = {}

    for log in logs:
        emp_id   = str(log.get("employee_id", ""))
        emp_name = log.get("employee_name", "Unknown")
        hours    = float(log.get("hours_worked", 0))

        if emp_id not in employee_totals:
            employee_totals[emp_id] = {"name": emp_name, "total_hours": 0.0}

        employee_totals[emp_id]["total_hours"] += hours

    # ── Compute metrics ───────────────────────────────────────────────────────
    total_employees = len(employee_totals)
    total_hours     = sum(v["total_hours"] for v in employee_totals.values())
    average_hours   = round(total_hours / total_employees, 2) if total_employees else 0

    low_hours = [
        v["name"]
        for v in employee_totals.values()
        if v["total_hours"] < 4
    ]

    # ── Build and save summary ────────────────────────────────────────────────
    summary = {
        "total_employees_submitted": total_employees,
        "total_hours_worked":        total_hours,
        "average_hours":             average_hours,
        "employees_less_than_4_hrs": low_hours,
        "generated_at":              datetime.utcnow().isoformat() + "Z",
    }

    _write_summary(summary)

    logger.info(
        "Summary generated: %d employees, %.1fh total, %d below 4h",
        total_employees, total_hours, len(low_hours),
    )


def _write_summary(summary: dict) -> None:
    try:
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, default=str)
    except IOError as exc:
        logger.error("Failed to write summary.json: %s", exc)
