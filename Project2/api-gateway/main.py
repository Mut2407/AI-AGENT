from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware # Thêm thư viện này
import httpx
import os

app = FastAPI(title="ExpenseOwl API Gateway")

# Cấu hình CORS để cho phép Frontend (cổng 3001) gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"], # Phải khớp với URL web của em
    allow_credentials=True,
    allow_methods=["*"], # Cho phép mọi method GET, POST, PUT, DELETE
    allow_headers=["*"], # Cho phép gửi kèm token xác thực
)

# ... (Giữ nguyên đoạn code cấu hình SERVICES và route bên dưới của em) ...


SERVICES = {
    "users": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
    "expenses": os.getenv("TXN_SERVICE_URL", "http://localhost:8002"),
    "recurring-expenses": os.getenv("TXN_SERVICE_URL", "http://localhost:8002"),
    "planning": os.getenv("BUDGET_SERVICE_URL", "http://localhost:8003"),
    "ai": os.getenv("AI_SERVICE_URL", "http://localhost:8004"),
    "auth": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
    "config": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
    "currency": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
    "startdate": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
    "categories": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
    "email-sync": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
    "profile": os.getenv("USER_SERVICE_URL", "http://localhost:8001"),
}

# Client HTTP bất đồng bộ để chuyển tiếp request
client = httpx.AsyncClient()

@app.api_route("/api/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway_route(service_name: str, path: str, request: Request):
    """
    Hàm này bắt mọi luồng bắt đầu bằng /api/... và chuyển tiếp đi
    Ví dụ: Gọi /api/expenses/history -> Chuyển sang http://localhost:8002/api/expenses/history
    """
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Service không tồn tại trong hệ thống")

    # Xây dựng URL đích
    target_url = f"{SERVICES[service_name]}/api/{service_name}/{path}"
    
    # Chuyển tiếp query parameters (?start_date=...&end_date=...)
    query_params = request.url.query.encode("utf-8")
    if query_params:
        target_url += f"?{query_params.decode('utf-8')}"

    # Đọc body và headers từ Frontend gửi lên
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None) # Bỏ host cũ đi để tránh lỗi

    # Gọi sang Service con
    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            timeout=60.0
        )
        # Trả kết quả từ Service con về lại cho Frontend
        return StreamingResponse(
            response.aiter_bytes(),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Gateway: Không thể kết nối tới {service_name} service.")