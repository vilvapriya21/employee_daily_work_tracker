"""
Employee Daily Work Tracker - Web App (FastAPI)

Reads FUNCTION_APP_URL directly from environment variables.
"""

import os
import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Employee Daily Work Tracker")
templates = Jinja2Templates(directory="templates")

FUNCTION_APP_URL="https://vilvafunctionapp-d8gkefhxgrfsaue9.centralus-01.azurewebsites.net"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/submit", response_class=JSONResponse)
async def submit_log(
    employee_name:  str = Form(...),
    employee_id:    str = Form(...),
    task_completed: str = Form(...),
    hours_worked:   str = Form(...),
):
    payload = {
        "employee_name":  employee_name,
        "employee_id":    employee_id,
        "task_completed": task_completed,
        "hours_worked":   hours_worked,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{FUNCTION_APP_URL}/api/submit_log", json=payload)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except httpx.ConnectError:
            return JSONResponse(content={"error": "Cannot reach Function App."}, status_code=503)


@app.get("/summary", response_class=JSONResponse)
async def get_summary():
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(f"{FUNCTION_APP_URL}/api/fetch_summary")
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        except httpx.ConnectError:
            return JSONResponse(content={"error": "Cannot reach Function App."}, status_code=503)
