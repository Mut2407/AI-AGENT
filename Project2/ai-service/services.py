import os
import requests
from fastapi import HTTPException

# Cấu hình URL của các Service khác
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
TXN_SERVICE_URL = os.getenv("TXN_SERVICE_URL", "http://transaction-service:8000")
BUDGET_SERVICE_URL = os.getenv("BUDGET_SERVICE_URL", "http://budget-service:8000")

def get_headers(user_id: int):
    # 🚀 Đây là "Thẻ thông hành" để AI Service được các service khác tin tưởng
    return {"X-Internal-User-Id": str(user_id), "Content-Type": "application/json"}

def get_user_config(user_id: int):
    try:
        # Nhớ mang thẻ khi đi xin dữ liệu
        res = requests.get(f"{USER_SERVICE_URL}/api/users/internal/config/{user_id}", headers=get_headers(user_id))
        if res.status_code == 200:
            return res.json()
    except requests.exceptions.RequestException:
        pass
    return {}

def get_user_transactions(user_id: int):
    try:
        # 🚀 Gắn thẻ vào đây để Transaction Service mở cửa!
        res = requests.get(f"{TXN_SERVICE_URL}/api/expenses/internal/user/{user_id}", headers=get_headers(user_id))
        if res.status_code == 200:
            data = res.json()
            # Đề phòng trường hợp API trả về {"expenses": [...]} thay vì mảng trực tiếp
            if isinstance(data, dict) and "expenses" in data:
                return data["expenses"]
            elif isinstance(data, list):
                return data
    except requests.exceptions.RequestException as e:
        print("Lỗi khi lấy giao dịch:", e)
    return []

def get_jars(user_id: int):
    try:
        res = requests.get(f"{BUDGET_SERVICE_URL}/api/planning/internal/jars/{user_id}", headers=get_headers(user_id))
        if res.status_code == 200:
            return res.json()
    except requests.exceptions.RequestException:
        pass
    return []

def get_active_budgets(user_id: int, start_date: str, end_date: str, period_type: str = "month"):
    try:
        url = f"{BUDGET_SERVICE_URL}/api/planning/internal/budgets/{user_id}?start_date={start_date}&end_date={end_date}&period_type={period_type}"
        res = requests.get(url, headers=get_headers(user_id))
        if res.status_code == 200:
            return res.json()
    except requests.exceptions.RequestException:
        pass
    return []

def save_transaction(user_id: int, tx_data: dict):
    try:
        res = requests.post(
            f"{TXN_SERVICE_URL}/api/expenses/internal/create",
            json=tx_data,
            headers=get_headers(user_id)
        )
        if res.status_code in (200, 201):
            return res.json()
        raise HTTPException(status_code=400, detail=f"Lỗi lưu giao dịch: {res.text}")
    except requests.exceptions.RequestException:
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

def transfer_jars(user_id: str, transfer_data: dict):
    try:
        res = requests.post(
            f"{BUDGET_SERVICE_URL}/api/planning/internal/jars/transfer",
            json=transfer_data,
            headers=get_headers(user_id)
        )
        if res.status_code == 200:
            return res.json()
        
        error_detail = res.text
        try:
            error_detail = res.json().get("detail", res.text)
        except:
            pass
            
        raise HTTPException(status_code=res.status_code, detail=str(error_detail))
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Budget Service không phản hồi: {str(e)}")

def create_jar(user_id: int, jar_data: dict):
    try:
        payload = {
            "name": jar_data.get("name", "Hũ mới"),
            "goal_amount": float(jar_data.get("goal_amount", 0)),
            "percent": 0 
        }
        res = requests.post(
            f"{BUDGET_SERVICE_URL}/api/planning/internal/jars",
            json=payload,
            headers=get_headers(user_id)
        )
        if res.status_code in (200, 201):
            return res.json()
    except Exception as e:
        print("Lỗi tạo hũ:", e)
    return None

def delete_jar_by_name(user_id: int, jar_name: str):
    try:
        jars = get_jars(user_id)
        target_jar = next((j for j in jars if j["name"].lower() == jar_name.lower()), None)
        
        if target_jar:
            requests.delete(
                f"{BUDGET_SERVICE_URL}/api/planning/internal/jars/{target_jar['id']}",
                headers=get_headers(user_id)
            )
            return True
    except Exception as e:
        print("Lỗi xóa hũ:", e)
    return False

def set_budget(user_id: str, budget_data: dict):
    try:
        payload = {
            "category": budget_data.get("category", "Khác"),
            "limit_amount": float(budget_data.get("limit_amount", 0)),
            "period_type": "month"
        }
        res = requests.post(
            f"{BUDGET_SERVICE_URL}/api/planning/internal/budgets",
            json=payload,
            headers=get_headers(user_id)
        )
        if res.status_code in (200, 201):
            return True
        
        error_detail = res.text
        try:
            error_detail = res.json().get("detail", res.text)
        except:
            pass
        raise HTTPException(status_code=res.status_code, detail=str(error_detail))
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Budget Service không phản hồi: {str(e)}")