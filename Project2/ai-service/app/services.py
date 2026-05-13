import os
import requests
from fastapi import HTTPException

# Cấu hình URL của các Service khác (Lấy từ biến môi trường của Docker)
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
TXN_SERVICE_URL = os.getenv("TXN_SERVICE_URL", "http://transaction-service:8000")
BUDGET_SERVICE_URL = os.getenv("BUDGET_SERVICE_URL", "http://budget-service:8000")

def get_headers(user_id: int):
    # Tạo header giả lập định danh nội bộ để các service khác tin tưởng
    return {"X-Internal-User-Id": str(user_id)}

def get_user_config(user_id: int):
    try:
        res = requests.get(f"{USER_SERVICE_URL}/api/users/internal/config/{user_id}")
        if res.status_code == 200:
            return res.json()
    except requests.exceptions.RequestException:
        pass
    return None

def get_user_transactions(user_id: int):
    try:
        res = requests.get(f"{TXN_SERVICE_URL}/api/expenses/internal/user/{user_id}")
        if res.status_code == 200:
            return res.json()
    except requests.exceptions.RequestException:
        pass
    return []

def get_jars(user_id: int):
    try:
        res = requests.get(f"{BUDGET_SERVICE_URL}/api/planning/internal/jars/{user_id}")
        if res.status_code == 200:
            return res.json()
    except requests.exceptions.RequestException:
        pass
    return []

def get_active_budgets(user_id: int, start_date: str, end_date: str, period_type: str = "month"):
    try:
        url = f"{BUDGET_SERVICE_URL}/api/planning/internal/budgets/{user_id}?start_date={start_date}&end_date={end_date}&period_type={period_type}"
        res = requests.get(url)
        if res.status_code == 200:
            return res.json()
    except requests.exceptions.RequestException:
        pass
    return []

def save_transaction(user_id: int, tx_data: dict):
    # Bắn HTTP POST sang Transaction Service để lưu
    try:
        res = requests.post(
            f"{TXN_SERVICE_URL}/api/expenses/internal/create",
            json=tx_data,
            headers=get_headers(user_id)
        )
        if res.status_code in (200, 201):
            return res.json()
        raise HTTPException(status_code=400, detail=f"Lỗi lưu giao dịch: {res.text}")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail="Transaction Service không phản hồi.")

def update_user_profile(user_id: int, goal: str, risk: str):
    try:
        requests.put(
            f"{USER_SERVICE_URL}/api/users/internal/config/update-profile",
            json={"goal": goal, "risk": risk},
            headers=get_headers(user_id)
        )
    except Exception:
        pass

def transfer_jars(user_id: int, transfer_data: dict):
    try:
        res = requests.post(
            f"{BUDGET_SERVICE_URL}/api/planning/internal/jars/transfer",
            json=transfer_data,
            headers=get_headers(user_id)
        )
        if res.status_code == 200:
            return res.json()
        raise HTTPException(status_code=400, detail=res.json().get("detail", "Lỗi chuyển quỹ"))
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="Budget Service không phản hồi.")