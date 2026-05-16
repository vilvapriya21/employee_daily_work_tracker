"""
HTTP Trigger 1 — submit_log
POST /api/submit_log

Receives employee work log data, validates it, and appends it to
employee_logs.json on the Function App's local file system.

Validation rules:
  • employee_id   → must be a valid integer
  • hours_worked  → must not exceed 8 hours per employee per day
"""

import json
import logging
import os
from datetime import date, datetime

import azure.functions as func

# ── Storage path ─────────────────────────────────────────────────────────────
# On Azure the Function App's writable home is /home (Linux plan) or
# D:\home (Windows plan). Locally it resolves to the folder this file lives in.
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "employee_logs.json")

logger = logging.getLogger(__name__)


def _load_logs() -> list:
    """Load existing logs from JSON file; return empty list if not found."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_logs(logs: list) -> None:
    """Write logs back to the JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, default=str)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("submit_log triggered")

    # ── Parse request body ────────────────────────────────────────────────────
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Request body must be valid JSON."}),
            status_code=400,
            mimetype="application/json",
        )

    employee_name  = str(body.get("employee_name",  "")).strip()
    employee_id    = str(body.get("employee_id",    "")).strip()
    task_completed = str(body.get("task_completed", "")).strip()
    hours_raw      = str(body.get("hours_worked",   "0")).strip()

    # ── Required-field check ──────────────────────────────────────────────────
    missing = [f for f, v in {
        "employee_name":  employee_name,
        "employee_id":    employee_id,
        "task_completed": task_completed,
    }.items() if not v]

    if missing:
        return func.HttpResponse(
            json.dumps({"error": f"Missing required fields: {', '.join(missing)}"}),
            status_code=400,
            mimetype="application/json",
        )

    # ── Validate employee_id (must be integer) ────────────────────────────────
    try:
        emp_id_int = int(employee_id)
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Employee ID must be a valid integer (e.g. 1042)."}),
            status_code=400,
            mimetype="application/json",
        )

    # ── Validate hours_worked ─────────────────────────────────────────────────
    try:
        hours = float(hours_raw)
        if hours < 0:
            raise ValueError("negative")
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Hours Worked must be a non-negative number."}),
            status_code=400,
            mimetype="application/json",
        )

    # ── Enforce 8-hour daily limit per employee ───────────────────────────────
    today = date.today().isoformat()
    logs  = _load_logs()

    hours_today = sum(
        float(log.get("hours_worked", 0))
        for log in logs
        if str(log.get("employee_id")) == str(emp_id_int)
        and log.get("date") == today
    )

    if hours_today + hours > 8:
        remaining = max(0, 8 - hours_today)
        return func.HttpResponse(
            json.dumps({
                "error": (
                    f"Employee {emp_id_int} has already logged {hours_today}h today. "
                    f"Adding {hours}h would exceed the 8-hour daily limit. "
                    f"You may log at most {remaining:.1f} more hours today."
                )
            }),
            status_code=400,
            mimetype="application/json",
        )

    # ── Save the log entry ────────────────────────────────────────────────────
    entry = {
        "employee_name":  employee_name,
        "employee_id":    emp_id_int,
        "task_completed": task_completed,
        "hours_worked":   hours,
        "date":           today,
        "submitted_at":   datetime.utcnow().isoformat() + "Z",
    }

    logs.append(entry)
    _save_logs(logs)

    logger.info("Saved log for employee %s (%s h)", emp_id_int, hours)

    return func.HttpResponse(
        json.dumps({"message": f"Work log saved successfully for {employee_name}!"}),
        status_code=200,
        mimetype="application/json",
    )
