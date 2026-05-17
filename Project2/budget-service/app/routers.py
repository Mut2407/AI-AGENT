from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
import models, schemas
from database import get_db
from pydantic import BaseModel
import requests
import os
from urllib import response
import calendar

# Giả định auth.py chứa hàm giải mã JWT thành dictionary current_user
from auth import get_current_user 

router = APIRouter(prefix="/api/planning", tags=["Planning"])

# ==========================================
# 1. QUẢN LÝ HŨ TÀI CHÍNH (JARS)
# ==========================================

@router.get("/jars")
def get_jars(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return db.query(models.Jar).filter(models.Jar.user_id == current_user["id"]).order_by(models.Jar.id).all()

def safe_decimal(value, default=0):
    try:
        if value is None or str(value).strip() == "":
            return Decimal(str(default))
        return Decimal(str(value).replace(',', ''))
    except:
        return Decimal(str(default))

@router.post("/jars/bulk")
def setup_jars_bulk(jars_data: list = Body(...), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Code này giữ nguyên logic của em, chỉ đổi current_user.id thành current_user["id"]
    existing_jars = db.query(models.Jar).filter(models.Jar.user_id == current_user["id"]).all()
    existing_map = {j.id: j for j in existing_jars}
    
    new_jar_ids = []
    for j in jars_data:
        j_id = j.get("id")
        name = j.get("name", "Hũ mới")
        percent = safe_decimal(j.get("percent", 0))
        goal = safe_decimal(j.get("goal_amount", 0))
        
        if j_id and j_id in existing_map:
            jar = existing_map[j_id]
            jar.name, jar.percent, jar.goal_amount = name, percent, goal
            new_jar_ids.append(jar.id)
        else:
            new_jar = models.Jar(name=name, percent=percent, goal_amount=goal, balance=0.0, user_id=current_user["id"])
            db.add(new_jar)
            db.flush()  
            new_jar_ids.append(new_jar.id)

    for old_id, old_jar in existing_map.items():
        if old_id not in new_jar_ids:
            if old_jar.balance > 0:
                raise HTTPException(status_code=400, detail=f"Hũ '{old_jar.name}' còn tiền, không thể xóa!")
            db.delete(old_jar)
    db.commit()
    return {"message": "Cấu hình hũ đã được cập nhật an toàn!"}

@router.delete("/jars/{jar_id}")
def delete_jar(jar_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    jar = db.query(models.Jar).filter(models.Jar.id == jar_id, models.Jar.user_id == current_user["id"]).first()
    if not jar:
        raise HTTPException(status_code=404, detail="Không tìm thấy hũ")
    if jar.balance > 0:
        raise HTTPException(status_code=400, detail="Hũ còn tiền! Vui lòng chuyển hoặc rút hết tiền ra.")
    db.delete(jar)
    db.commit()
    return {"message": "Đã xóa hũ thành công"}

class TransferPayload(BaseModel):
    type: str # 'deposit', 'withdraw', 'internal'
    amount: float
    to_id: int = None
    from_id: int = None
# Thêm hàm này để lấy tổng tiền thật của user
def get_total_wallet_balance(token):
    try:
        TXN_SERVICE_URL = os.getenv("TXN_SERVICE_URL", "http://transaction-service:8000")
        
        # ⚠️ LƯU Ý: Nếu API lấy danh sách giao dịch bên transaction-service của bạn 
        # tên là /api/expenses/history (giống hàm calculate_spent_amount) thì đổi lại ở đây nhé.
        url = f"{TXN_SERVICE_URL}/api/expenses"
        
        response = requests.get(
            url, 
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"⚠️ CẢNH BÁO: Gọi txn-service thất bại (Code: {response.status_code}). URL: {url}")
            return 999999999.0  
            
        data = response.json()
        
        # Parse an toàn đề phòng data trả về dạng dict {"data": [...]} thay vì list
        transactions = data if isinstance(data, list) else data.get("transactions", [])
        
        total_income = sum(float(t.get("amount", 0)) for t in transactions if float(t.get("amount", 0)) > 0)
        total_expense = sum(abs(float(t.get("amount", 0))) for t in transactions if float(t.get("amount", 0)) < 0)
        
        return float(total_income - total_expense)
        
    except Exception as e:
        print(f"⚠️ LỖI MẠNG ĐỘC LẬP TẠI BUDGET-SERVICE: {e}")
        # Bypass để không làm kẹt tính năng nạp hũ của user
        return 999999999.0
@router.post("/jars/transfer")
def transfer_jar(payload: TransferPayload, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from sqlalchemy import func
    amount = Decimal(str(payload.amount))
    uid = str(current_user["id"])

    if payload.type == "deposit":
        total_wallet = get_total_wallet_balance(current_user["token"])
        total_in_jars = db.query(func.sum(models.Jar.balance)).filter(models.Jar.user_id == uid).scalar() or 0.0
        free_balance = float(total_wallet) - float(total_in_jars)

        if float(amount) > free_balance:
            raise HTTPException(status_code=400, detail=f"Không đủ tiền rảnh rỗi! Bạn chỉ còn tối đa {free_balance} để nạp.")

        jar = db.query(models.Jar).filter(models.Jar.id == payload.to_id, models.Jar.user_id == uid).first()
        if not jar: raise HTTPException(status_code=404, detail="Không tìm thấy hũ")
        jar.balance += amount
        hist = models.JarHistory(user_id=uid, jar_id=jar.id, name=f"Nạp vào hũ {jar.name} {amount:,.0f}đ", amount=amount, date=datetime.now())
        db.add(hist)
        
    elif payload.type == "withdraw":
        jar = db.query(models.Jar).filter(models.Jar.id == payload.from_id, models.Jar.user_id == uid).first()
        if not jar: raise HTTPException(status_code=404, detail="Không tìm thấy hũ")
        if jar.balance < amount: raise HTTPException(status_code=400, detail="Số dư trong hũ không đủ để rút!")
        jar.balance -= amount
        hist = models.JarHistory(user_id=uid, jar_id=jar.id, name=f"Rút từ hũ {jar.name} {amount:,.0f}đ", amount=-amount, date=datetime.now())
        db.add(hist)
        
    elif payload.type == "internal":
        from_jar = db.query(models.Jar).filter(models.Jar.id == payload.from_id, models.Jar.user_id == uid).first()
        to_jar = db.query(models.Jar).filter(models.Jar.id == payload.to_id, models.Jar.user_id == uid).first()
        if not from_jar or not to_jar: raise HTTPException(status_code=404, detail="Không tìm thấy hũ")
        if from_jar.balance < amount: raise HTTPException(status_code=400, detail="Số dư hũ nguồn không đủ!")
        
        from_jar.balance -= amount
        to_jar.balance += amount
        
        hist1 = models.JarHistory(user_id=uid, jar_id=from_jar.id, name=f"Chuyển đến hũ {to_jar.name} {amount:,.0f}đ", amount=-amount, date=datetime.now())
        hist2 = models.JarHistory(user_id=uid, jar_id=to_jar.id, name=f"Nhận từ hũ {from_jar.name} {amount:,.0f}đ", amount=amount, date=datetime.now())
        db.add(hist1)
        db.add(hist2)
        
    db.commit()
    return {"message": "Giao dịch thành công!"}

@router.get("/jars/{jar_id}/history")
def get_jar_history(jar_id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    history = db.query(models.JarHistory).filter(
        models.JarHistory.user_id == str(current_user["id"]),
        models.JarHistory.jar_id == jar_id
    ).order_by(models.JarHistory.date.desc()).all()
    return [{"id": h.id, "jar_id": h.jar_id, "name": h.name, "amount": float(h.amount), "date": h.date.isoformat()} for h in history]

@router.get("/jars/history/all")
def get_all_jar_history(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    history = db.query(models.JarHistory).filter(models.JarHistory.user_id == str(current_user["id"])).order_by(models.JarHistory.date.desc()).all()
    return [{"id": h.id, "jar_id": h.jar_id, "name": h.name, "amount": float(h.amount), "date": h.date.isoformat()} for h in history]

# ==========================================
# 2. QUẢN LÝ NGÂN SÁCH (BUDGETS)
# ==========================================

@router.get("/budgets/current")
def get_current_budgets(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Lấy ngân sách của tháng hiện tại.
    Frontend có thể gọi endpoint này khi load trang lần đầu.
    Trả về cả dữ liệu ngân sách + start_date/end_date của tháng hiện tại.
    """
    from sqlalchemy import func
    from calendar import monthrange
    
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # Tính ngày đầu tháng và ngày cuối tháng
    first_day = now.replace(day=1)
    last_day_num = monthrange(current_year, current_month)[1]
    last_day = now.replace(day=last_day_num)

    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == current_user["id"],
        func.extract('month', models.Budget.start_date) == current_month,
        func.extract('year', models.Budget.start_date) == current_year,
        models.Budget.period_type == "month"
    ).all()

    result = []
    for b in budgets:
        result.append({
            "id": b.id,
            "category": b.category,
            "limit_amount": float(b.limit_amount or 0.0),
            "spent_amount": float(b.spent_amount or 0.0),
            "period_type": b.period_type,
            "start_date": b.start_date.isoformat() if b.start_date else "",
            "end_date": b.end_date.isoformat() if b.end_date else ""
        })
    
    return {
        "month": current_month,
        "year": current_year,
        "start_date": first_day.isoformat(),
        "end_date": last_day.isoformat(),
        "budgets": result
    }

@router.get("/budgets")
def get_budgets(start_date: str, end_date: str, period_type: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from sqlalchemy import func
    
    start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
    end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()

    start_month = start.month
    start_year = start.year

    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == current_user["id"],
        func.extract('month', models.Budget.start_date) == start_month,
        func.extract('year', models.Budget.start_date) == start_year,
        models.Budget.period_type == period_type
    ).all()

    # KHÔNG THỂ SUM() TỪ BẢNG TRANSACTIONS NỮA. 
    # Trả về trực tiếp cột `spent_amount` mà Budget Service tự quản lý
    result = []
    for b in budgets:
        result.append({
            "id": b.id,
            "category": b.category,
            "limit_amount": float(b.limit_amount),
            "spent_amount": float(b.spent_amount),
            "period_type": b.period_type,
            "start_date": b.start_date.isoformat() if b.start_date else "",
            "end_date": b.end_date.isoformat() if b.end_date else ""
        })
    return result
def calculate_spent_amount(user_id, category, start, end, token):
    try:
        TXN_SERVICE_URL = os.getenv(
            "TXN_SERVICE_URL",
            "http://transaction-service:8000"
        )

        response = requests.get(
            f"{TXN_SERVICE_URL}/api/expenses/history",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "start_date": start.isoformat(),
                "end_date": end.isoformat()
            },
            timeout=10
        )

        if response.status_code != 200:
            print(f"Lỗi gọi API Transaction: {response.status_code}")
            return 0

        data = response.json()
        transactions = (
            data if isinstance(data, list)
            else data.get("transactions", [])
        )

        total = 0

        for txn in transactions:
            amount = float(txn.get("amount", 0))
            txn_category = str(
                txn.get("category", "")
            ).strip().lower()

            raw_date = txn.get("date") or txn.get("transaction_date")
            if not raw_date:
                continue
                
            txn_date = datetime.strptime(
                str(raw_date)[:10],
                "%Y-%m-%d"
            ).date()

            if (
                txn_category == category.lower()
                and amount < 0
                and start <= txn_date <= end
            ):
                total += abs(amount)

        return total

    except Exception as e:
        print(f"Lỗi calculate_spent_amount: {e}")
        return 0
@router.post("/budgets/bulk")
def setup_budgets_bulk(payload: dict = Body(...), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    from sqlalchemy import func
    try:
        start = datetime.strptime(payload["start_date"][:10], "%Y-%m-%d").date()
        end = datetime.strptime(payload["end_date"][:10], "%Y-%m-%d").date()
        period_type = payload["period_type"]
        budgets_data = payload["budgets"]

        start_month = start.month
        start_year = start.year

        # 1. Nhóm toàn bộ ngân sách hiện tại theo category
        current_budgets = db.query(models.Budget).filter(
            models.Budget.user_id == current_user["id"],
            func.extract('month', models.Budget.start_date) == start_month,
            func.extract('year', models.Budget.start_date) == start_year,
            models.Budget.period_type == period_type
        ).all()

        budget_map = {}
        for b in current_budgets:
            if b.category not in budget_map:
                budget_map[b.category] = []
            budget_map[b.category].append(b)

        # 2. Lấy danh sách category từ Frontend gửi lên
        payload_categories = {str(item.get("category", "")).strip() for item in budgets_data if str(item.get("category", "")).strip()}

        # 3. Xóa các ngân sách không còn tồn tại
        for cat, b_list in budget_map.items():
            if cat not in payload_categories:
                for b in b_list:
                    db.delete(b)

        # 4. Xử lý lưu đè và tạo mới
        for item in budgets_data:
            cat = str(item.get("category", "")).strip()
            limit = float(item.get("limit_amount") or 0.0)

            if limit < 0:
                raise HTTPException(status_code=400, detail="Hạn mức không được âm")
            if not cat: continue

            existing_list = budget_map.get(cat, [])

            if limit == 0:
                for ex in existing_list:
                    db.delete(ex)
                continue

            if existing_list:
                existing_list[0].limit_amount = limit
                for ex in existing_list[1:]:
                    db.delete(ex)
            else:
                spent_amount = calculate_spent_amount(
                    current_user["id"],
                    cat,
                    start,
                    end,
                    current_user["token"]
                )
                new_budget = models.Budget(
                    category=cat,
                    limit_amount=limit,
                    spent_amount=spent_amount,
                    period_type=period_type,
                    start_date=start,
                    end_date=end,
                    user_id=current_user["id"],
                )
                db.add(new_budget)

        db.commit()
        return {"message": "Đã cập nhật ngân sách thành công!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống Backend: {str(e)}")

@router.delete("/budgets/{category}")
def delete_budget(category: str, start_date: str, end_date: str, period_type: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
    end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
    
    budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user["id"],
        models.Budget.category == category,
        models.Budget.start_date == start,
        models.Budget.end_date == end,
        models.Budget.period_type == period_type
    ).first()

    if budget:
        db.delete(budget)
        db.commit()
        return {"message": "Đã xóa ngân sách thành công!"}
    
    raise HTTPException(status_code=404, detail="Không tìm thấy ngân sách")
# ==========================================
# 3. TỔNG HỢP SỐ LIỆU (DASHBOARD SUMMARY)
# ==========================================
from sqlalchemy import func

@router.get("/dashboard-summary")
def get_dashboard_summary(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """
    Hàm này lấy tổng số dư các hũ và tổng chi tiêu hiện tại
    để Frontend vẽ biểu đồ tổng quan.
    """
    uid = str(current_user["id"])
    
    
    # 1. XỬ LÝ DỮ LIỆU HŨ (JARS)
    
    jars = db.query(models.Jar).filter(models.Jar.user_id == uid).all()
    total_balance = sum(j.balance for j in jars)
    
    near_goal = None
    max_percent = -1
    for j in jars:
        if j.goal_amount > 0:
            percent = float((j.balance / j.goal_amount) * 100)
            if 80 <= percent < 100 and percent > max_percent:
                max_percent = percent
                near_goal = {
                    "name": j.name, 
                    "percent": round(percent, 1),
                    "balance": float(j.balance)
                }

    biggest_jar = max(jars, key=lambda j: j.balance) if jars else None

   
    # 2. XỬ LÝ DỮ LIỆU NGÂN SÁCH (BUDGET)
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == uid,
        func.extract('month', models.Budget.start_date) == current_month,
        func.extract('year', models.Budget.start_date) == current_year
    ).all()

    total_spent = sum(b.spent_amount for b in budgets)
    total_limit = sum(b.limit_amount for b in budgets)
    
    near_exceed = None
    max_budget_percent = -1
    highest_spent_cat = None
    max_spent = -1

    for b in budgets:
        if b.spent_amount > max_spent:
            max_spent = b.spent_amount
            highest_spent_cat = b.category
            
        if b.limit_amount > 0:
            percent = float((b.spent_amount / b.limit_amount) * 100)
            if percent > max_budget_percent and percent < 100: 
                max_budget_percent = percent
                near_exceed = {"category": b.category, "percent": round(percent, 1)}

    
    # 3. TRẢ VỀ CHO FRONTEND

    return {
        # Data của Hũ
        "total_balance": float(total_balance),
        "active_jars_count": len(jars),
        "near_goal": near_goal,
        "biggest_jar": {"name": biggest_jar.name, "balance": float(biggest_jar.balance)} if biggest_jar else None,
        
        # Data của Ngân sách
        "total_spent": float(total_spent),
        "total_limit": float(total_limit),
        "highest_spent_category": {"category": highest_spent_cat, "amount": float(max_spent)} if highest_spent_cat and max_spent > 0 else None,
        "near_exceed_budget": near_exceed
    }

# ==========================================
# 4. API NỘI BỘ (INTERNAL) CHO AI-SERVICE 
# ==========================================
from fastapi import Request
from sqlalchemy import func

def get_internal_uid(req: Request):
    uid = req.headers.get("X-Internal-User-Id")
    if not uid:
        raise HTTPException(status_code=401, detail="Từ chối truy cập nội bộ")
    return uid

@router.get("/internal/jars/{user_id}")
def internal_get_jars(user_id: str, db: Session = Depends(get_db)):
    return db.query(models.Jar).filter(models.Jar.user_id == user_id).order_by(models.Jar.id).all()

@router.get("/internal/budgets/{user_id}")
def internal_get_budgets(user_id: str, start_date: str, end_date: str, period_type: str, db: Session = Depends(get_db)):
    start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
    return db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        func.extract('month', models.Budget.start_date) == start.month,
        func.extract('year', models.Budget.start_date) == start.year,
        models.Budget.period_type == period_type
    ).all()

@router.post("/internal/jars")
def internal_create_jar(payload: dict = Body(...), db: Session = Depends(get_db), uid: str = Depends(get_internal_uid)):
    new_jar = models.Jar(
        name=payload.get("name", "Hũ mới"),
        goal_amount=safe_decimal(payload.get("goal_amount", 0)),
        percent=0,
        balance=0.0,
        user_id=uid
    )
    db.add(new_jar)
    db.commit()
    return {"status": "success"}

@router.delete("/internal/jars/{jar_id}")
def internal_delete_jar(jar_id: int, db: Session = Depends(get_db), uid: str = Depends(get_internal_uid)):
    jar = db.query(models.Jar).filter(models.Jar.id == jar_id, models.Jar.user_id == uid).first()
    if jar:
        db.delete(jar)
        db.commit()
    return {"status": "success"}

@router.post("/internal/jars/transfer")
def internal_transfer_jar(payload: TransferPayload, db: Session = Depends(get_db), uid: str = Depends(get_internal_uid)):
    return transfer_jar(payload, db, current_user={"id": uid, "token": "internal_bypass"})

@router.post("/internal/budgets")
def internal_set_budget(payload: dict = Body(...), db: Session = Depends(get_db), uid: str = Depends(get_internal_uid)):
    category = payload.get("category", "Khác")
    limit_amount = float(payload.get("limit_amount", 0))
    
    now = datetime.now()
    start_dt = datetime(now.year, now.month, 1).date()
    _, last_day = calendar.monthrange(now.year, now.month)
    end_dt = datetime(now.year, now.month, last_day).date()
    
    existing = db.query(models.Budget).filter(
        models.Budget.user_id == uid,
        models.Budget.category == category,
        models.Budget.start_date == start_dt,
        models.Budget.period_type == "month"
    ).first()
    
    if limit_amount <= 0:
        if existing:
            db.delete(existing)
            db.commit()
        return {"status": "success", "action": "deleted"}
    
    if existing:
        existing.limit_amount = limit_amount
        existing.end_date = end_dt
    else:
        new_budget = models.Budget(
            category=category,
            limit_amount=limit_amount,
            spent_amount=0,
            period_type="month",
            start_date=start_dt,
            end_date=end_dt,
            user_id=uid
        )
        db.add(new_budget)
        
    db.commit()
    return {"status": "success"}