from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal
import models, schemas
from database import get_db

# Giả định auth.py chứa hàm giải mã JWT thành dictionary current_user
from auth import get_current_user 

router = APIRouter(prefix="/api/planning", tags=["Planning"])

# ==========================================
# 1. QUẢN LÝ HŨ TÀI CHÍNH (JARS)
# ==========================================

@router.get("/jars")
def get_jars(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return db.query(models.Jar).filter(models.Jar.user_id == current_user["id"]).order_by(models.Jar.id).all()

@router.post("/jars/bulk")
def setup_jars_bulk(jars_data: list = Body(...), db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Code này giữ nguyên logic của em, chỉ đổi current_user.id thành current_user["id"]
    existing_jars = db.query(models.Jar).filter(models.Jar.user_id == current_user["id"]).all()
    existing_map = {j.id: j for j in existing_jars}
    
    new_jar_ids = []
    for j in jars_data:
        j_id = j.get("id")
        name = j.get("name", "Hũ mới")
        percent = Decimal(str(j.get("percent", 0)))
        goal = Decimal(str(j.get("goal_amount", 0)))
        
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
            "limit_amount": float(b.limit_amount),
            "spent_amount": float(b.spent_amount),
            "period_type": b.period_type,
            "start_date": b.start_date.isoformat(),
            "end_date": b.end_date.isoformat()
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
            "spent_amount": float(b.spent_amount), # Đọc trực tiếp từ DB của Budget 
            "period_type": b.period_type,
            "start_date": b.start_date.isoformat(),
            "end_date": b.end_date.isoformat()
        })
    return result

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
            limit = float(item.get("limit_amount", 0))

            if not cat: continue

            existing_list = budget_map.get(cat, [])

            if limit == 0:
                # Nếu Frontend gửi số 0 -> Đòi xóa -> Xóa sạch!
                for ex in existing_list:
                    db.delete(ex)
                continue

            if existing_list:
                # Giữ lại cái đầu tiên để bảo toàn số tiền đã tiêu, xóa các bản sao lỗi
                existing_list[0].limit_amount = limit
                for ex in existing_list[1:]:
                    db.delete(ex)
            else:
                # Tạo mới hoàn toàn
                new_budget = models.Budget(
                    category=cat,
                    limit_amount=limit,
                    spent_amount=0.0,
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
    # 1. Tính tổng số dư hiện có trong tất cả các hũ
    total_balance_query = db.query(func.sum(models.Jar.balance)).filter(
        models.Jar.user_id == current_user["id"]
    ).scalar()
    
    total_balance = float(total_balance_query) if total_balance_query else 0.0

    # 2. Tính tổng số tiền đã chi tiêu trong tháng này
    # (Vì bảng Budget lưu spent_amount nên ta cộng tổng cái đó lại)
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    total_spent_query = db.query(func.sum(models.Budget.spent_amount)).filter(
        models.Budget.user_id == current_user["id"],
        func.extract('month', models.Budget.start_date) == current_month,
        func.extract('year', models.Budget.start_date) == current_year
    ).scalar()
    
    total_spent = float(total_spent_query) if total_spent_query else 0.0

    # Trả về kết quả cho Frontend
    return {
        "total_balance": total_balance,
        "total_spent": total_spent,
        "active_jars_count": db.query(models.Jar).filter(models.Jar.user_id == current_user["id"]).count(),
        "active_budgets_count": db.query(models.Budget).filter(
            models.Budget.user_id == current_user["id"],
            func.extract('month', models.Budget.start_date) == current_month,
            func.extract('year', models.Budget.start_date) == current_year
        ).count()
    }