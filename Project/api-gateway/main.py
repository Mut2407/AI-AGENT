from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import os

app = FastAPI(title="ExpenseOwl API Gateway")


# 1. Cấu hình giao diện (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Địa chỉ các service nội bộ (lấy từ biến môi trường Docker)
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8001")
TRANSACTION_SERVICE_URL = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:8002")
BUDGET_SERVICE_URL = os.getenv("BUDGET_SERVICE_URL", "http://budget-service:8003")

# --- ĐIỀU HƯỚNG GIAO DIỆN (FRONTEND) ---
@app.get("/", response_class=HTMLResponse)
def render_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
def render_settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

# --- PROXY LOGIC (ĐIỀU HƯỚNG API) ---
@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_auth(request: Request, path: str):
    return await proxy_request(USER_SERVICE_URL, f"api/auth/{path}", request)

@app.api_route("/api/config/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_config(request: Request, path: str):
    # User Service cũng giữ vai trò quản lý Config
    return await proxy_request(USER_SERVICE_URL, f"api/{path}", request)

async def proxy_request(base_url: str, path: str, request: Request):
    """Hàm trung gian để gửi tiếp yêu cầu đến service nội bộ"""
    url = f"{base_url}/{path}"
    async with httpx.AsyncClient() as client:
        # Lấy method, nội dung và headers từ request gốc
        content = await request.body()
        headers = dict(request.headers)
        # Xóa host cũ để tránh lỗi loop
        headers.pop("host", None)
        
        response = await client.request(
            method=request.method,
            url=url,
            content=content,
            headers=headers,
            params=request.query_params
        )
        return StreamingResponse(
            response.aiter_raw(),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    


# Thêm vào trong api-gateway/main.py
@app.api_route("/api/expenses/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_expenses(request: Request, path: str):
    return await proxy_request(TRANSACTION_SERVICE_URL, f"api/expenses/{path}", request)

@app.api_route("/api/recurring-expenses/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_recurring(request: Request, path: str):
    return await proxy_request(TRANSACTION_SERVICE_URL, f"api/recurring-expenses/{path}", request)
@app.api_route("/api/ai/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_ai(request: Request, path: str):
    return await proxy_request(BUDGET_SERVICE_URL, f"api/ai/{path}", request)