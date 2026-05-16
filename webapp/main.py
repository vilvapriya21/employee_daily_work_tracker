"""
Employee Daily Work Tracker - Web App (FastAPI)

LOCAL:  reads FUNCTION_APP_URL from environment variable
AZURE:  fetches the Function App URL from Azure Key Vault at startup
"""

import os
import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Employee Daily Work Tracker")
templates = Jinja2Templates(directory="templates")

FUNCTION_APP_URL: str = ""


@app.on_event("startup")
async def load_function_url():
    global FUNCTION_APP_URL

    keyvault_url = os.getenv("KEYVAULT_URL")

    if keyvault_url:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            secret_name  = os.getenv("SECRET_NAME", "FunctionAppUrl")
            credential   = DefaultAzureCredential()
            client       = SecretClient(vault_url=keyvault_url, credential=credential)
            secret       = client.get_secret(secret_name)
            FUNCTION_APP_URL = secret.value.rstrip("/")
            print(f"[startup] Loaded Function URL from Key Vault -> {FUNCTION_APP_URL}")
        except Exception as e:
            print(f"[startup] Key Vault error: {e}")
            FUNCTION_APP_URL = os.getenv("FUNCTION_APP_URL", "http://localhost:7071")
    else:
        FUNCTION_APP_URL = os.getenv("FUNCTION_APP_URL", "http://localhost:7071")
        print(f"[startup] Local mode - Function App URL -> {FUNCTION_APP_URL}")


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
