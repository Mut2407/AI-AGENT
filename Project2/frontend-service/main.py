from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="ExpenseOwl Frontend")

# Phục vụ file tĩnh (JS, CSS, Hình ảnh)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Cấu hình thư mục chứa giao diện HTML
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/register")
def register_page(request: Request):
    # Dùng đích danh request=... và name=... để Python không gán nhầm
    return templates.TemplateResponse(request=request, name="register.html")

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/planning", response_class=HTMLResponse)
async def serve_planning(request: Request):
    return templates.TemplateResponse(request=request, name="planning.html")

@app.get("/history", response_class=HTMLResponse)
async def serve_history(request: Request):
    return templates.TemplateResponse(request=request, name="history.html")

@app.get("/profile", response_class=HTMLResponse)
async def serve_profile(request: Request):
    return templates.TemplateResponse(request=request, name="profile.html")

@app.get("/trends", response_class=HTMLResponse)
async def serve_trends(request: Request):
    return templates.TemplateResponse(request=request, name="trends.html")