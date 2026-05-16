"""
HTTP Trigger 2 — fetch_summary
GET /api/fetch_summary

Reads summary.json (written by the Timer Trigger every 2 hours)
and returns it to the Web App.
"""

import json
import logging
import os

import azure.functions as func

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUMMARY_FILE  = os.path.join(BASE_DIR, "summary.json")

logger = logging.getLogger(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    logger.info("fetch_summary triggered")

    if not os.path.exists(SUMMARY_FILE):
        return func.HttpResponse(
            json.dumps({
                "error": (
                    "No summary available yet. "
                    "The Timer Trigger runs every 2 hours to generate it. "
                    "You can also trigger it manually for testing."
                )
            }),
            status_code=404,
            mimetype="application/json",
        )

    try:
        with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
            summary = json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        logger.error("Failed to read summary.json: %s", exc)
        return func.HttpResponse(
            json.dumps({"error": "Summary file is corrupted. Try again later."}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps(summary),
        status_code=200,
        mimetype="application/json",
    )
