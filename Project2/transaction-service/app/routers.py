from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import uuid
import csv
import io
import re
from datetime import datetime
from decimal import Decimal
import requests
import os

# Import nội bộ của Transaction Service
import models, schemas
from database import get_db

# Giả định em đã có file kafka_pro.py như Cú Mèo hướng dẫn ở bước trước
import kafka_pro 

# Giả định hàm get_current_user giờ đây chỉ giải mã JWT để lấy user_id 
# (Không query Database để lấy cả bảng User nữa vì bảng User nằm ở service khác)
from auth import get_current_user 
from pydantic import BaseModel

class N8nWebhookPayload(BaseModel):
    source: str
    sender: str
    receiver: str
    raw_content: str
# # ==========================================
# # HELPER FUNCTIONS: JAR + BUDGET
# # ==========================================

# def distribute_to_jars(db: Session, user_id: str, income_amount: float):
#     """Phân tiền thu nhập vào 6 hũ theo tỷ lệ phần trăm"""
#     user_jars = db.query(models.Jar).filter(models.Jar.user_id == user_id).order_by(models.Jar.id).all()
#     if not user_jars:
#         return

#     for jar in user_jars:
#         if jar.percent > 0:
#             allocated_money = Decimal(str(income_amount)) * (jar.percent / Decimal('100'))
#             jar.balance += allocated_money
#     db.commit()


def update_budget_spent(db: Session, user_id: str, category: str, spent_amount: float):
    """Cập nhật số tiền đã chi tiêu cho từng budget theo category"""
    # Tạm thời chỉ tracking, có thể mở rộng để kiểm tra quá budget
    pass


# def update_budget_spent(db: Session, user_id: str, category: str, spent_amount: float):
#     """Cập nhật số tiền đã chi tiêu cho từng budget theo category"""
#     # Tạm thời chỉ tracking, có thể mở rộng để kiểm tra quá budget
#     pass
router = APIRouter(prefix="/api/expenses", tags=["Expenses"])
recurring_router = APIRouter(prefix="/api/recurring-expenses", tags=["Recurring Expenses"])

# ==========================================
# 1. QUẢN LÝ GIAO DỊCH (TRANSACTIONS)
# ==========================================

@router.get("/", response_model=List[schemas.TransactionResponse])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user), # Đã đổi thành dict chứa user_id
):
    return (
        db.query(models.Transaction)
        .filter(
            models.Transaction.user_id == current_user["id"],
            models.Transaction.amount != 0 
        )
        .order_by(models.Transaction.date.desc())
        .all()
    )

@router.get("/history")
def get_transactions_history(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """API dùng để Budget Service lấy lịch sử giao dịch tính tổng tiền"""
    from sqlalchemy import func
    
    start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
    end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
    
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user["id"],
        func.date(models.Transaction.date) >= start,
        func.date(models.Transaction.date) <= end
    ).all()
    
    return {"transactions": transactions}

@router.post("/", response_model=schemas.TransactionResponse)
def create_transaction(
    transaction: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    new_id = str(uuid.uuid4())
    db_transaction = models.Transaction(
        id=new_id,
        name=transaction.name,
        amount=transaction.amount,
        category=transaction.category,
        date=transaction.date,
        tags=transaction.tags if transaction.tags else ["Manual"],
        note=transaction.note,
        recurring_interval=transaction.recurring_interval,
        jar_id=transaction.jar_id,
        user_id=current_user["id"],
    )
    db.add(db_transaction)
    
    # # 🚀 JAR + BUDGET LOGIC từ monolith
    # if transaction.amount > 0:  # Income
    #     distribute_to_jars(db, current_user["id"], float(transaction.amount))
    # elif transaction.amount < 0:  # Expense
    #     if transaction.jar_id:
    #         jar = db.query(models.Jar).filter(
    #             models.Jar.id == transaction.jar_id,
    #             models.Jar.user_id == current_user["id"]
    #         ).first()
    #         if jar:
    #             if jar.balance < abs(transaction.amount):
    #                 raise HTTPException(
    #                     status_code=400,
    #                     detail=f"Quỹ '{jar.name}' không đủ tiền! (Hiện chỉ còn {jar.balance:,.0f})"
    #                 )
    #             jar.balance -= Decimal(str(abs(transaction.amount)))
    #             db.add(jar)
        
    #     update_budget_spent(db, current_user["id"], transaction.category, abs(transaction.amount))
    
    db.commit()
    db.refresh(db_transaction)

    # 🚀 MICROSERVICE MAGIC: Gửi event qua Kafka
    kafka_pro.send_transaction_event("TRANSACTION_CREATED", {
         "id": db_transaction.id,
         "user_id": db_transaction.user_id,
         "jar_id": db_transaction.jar_id,
         "amount": float(db_transaction.amount),
         "category": db_transaction.category,
         "transaction_date": db_transaction.date.isoformat() if db_transaction.date else datetime.now().isoformat()
    })

    return db_transaction

@router.put("/{transaction_id}", response_model=schemas.TransactionResponse)
def update_transaction(
    transaction_id: str,
    transaction_update: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    db_txn = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == current_user["id"]
    ).first()
    
    if not db_txn:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")

    old_amount = float(db_txn.amount)
    old_category = db_txn.category
    old_jar_id = db_txn.jar_id

    db_txn.name = transaction_update.name
    db_txn.amount = transaction_update.amount
    db_txn.category = transaction_update.category
    db_txn.date = transaction_update.date
    db_txn.tags = transaction_update.tags
    db_txn.note = transaction_update.note
    db_txn.recurring_interval = transaction_update.recurring_interval

    db.commit()
    db.refresh(db_txn)

    # 🚀 Bắn Kafka event thông báo cập nhật
    try:
        kafka_pro.send_transaction_event("TRANSACTION_UPDATED", {
            "id": db_txn.id,
            "user_id": db_txn.user_id,
            "transaction_date": db_txn.date.isoformat() if db_txn.date else None,
            
            # Dữ liệu mới để cộng vào
            "amount": float(db_txn.amount),
            "category": db_txn.category,
            "jar_id": db_txn.jar_id,
            
            # Dữ liệu cũ để trừ đi (RẤT QUAN TRỌNG)
            "old_amount": old_amount,
            "old_category": old_category,
            "old_jar_id": old_jar_id
        })
    except Exception as e:
        print(f"Lỗi gửi Kafka: {e}")

    return db_txn

@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    db_txn = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.user_id == current_user["id"]
    ).first()
    
    if not db_txn:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")

    amount_to_refund = float(db_txn.amount)
    category = db_txn.category
    jar_id = db_txn.jar_id
    txn_date = db_txn.date.isoformat() if db_txn.date else datetime.now().isoformat()

    # # 🚀 JAR REFUND LOGIC
    # if db_txn.amount < 0 and jar_id:
    #     # Hoàn tiền vào hũ khi xóa giao dịch chi tiêu
    #     jar = db.query(models.Jar).filter(
    #         models.Jar.id == jar_id,
    #         models.Jar.user_id == current_user["id"]
    #     ).first()
    #     if jar:
    #         jar.balance += Decimal(str(abs(amount_to_refund)))
    #         db.add(jar)

    db.delete(db_txn)
    db.commit()

    # 🚀 Bắn Kafka event thông báo xóa để Budget Service hoàn tiền
    kafka_pro.send_transaction_event("TRANSACTION_DELETED", {
        "id": transaction_id,
        "user_id": current_user["id"],
        "jar_id": jar_id,
        "amount": amount_to_refund,
        "category": category,
        "transaction_date": txn_date
    })

    return {"message": "Đã xóa thành công"}

# ==========================================
# 2. XUẤT/NHẬP CSV
# ==========================================

@router.get("/export/csv")
def export_csv(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user["id"]
    ).order_by(models.Transaction.date.desc()).all()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["Date", "Name", "Category", "Amount", "Tags"])

    for t in transactions:
        tags_str = ",".join(t.tags) if t.tags else ""
        date_str = t.date.strftime("%Y-%m-%d") if t.date else ""
        writer.writerow([date_str, t.name, t.category, t.amount, tags_str])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ExpenseOwl_Data.csv"},
    )

@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if not file.filename.endswith(".csv"):
        return {"error": "Vui lòng tải lên file định dạng .csv"}

    content = await file.read()
    decoded_content = content.decode("utf-8-sig").splitlines()
    reader = csv.DictReader(decoded_content)

    total_processed, imported, skipped = 0, 0, 0

    for row in reader:
        total_processed += 1
        try:
            date_obj = datetime.strptime(row.get("Date", "").strip(), "%Y-%m-%d")
            name = row.get("Name", "-").strip()
            category = row.get("Category", "Khác").strip()
            amount = float(row.get("Amount", 0))
            raw_tags = row.get("Tags", "")
            tags = [t.strip() for t in raw_tags.split(",")] if raw_tags else []

            new_tx = models.Transaction(
                id=str(uuid.uuid4()),
                name=name,
                amount=amount,
                category=category,
                date=date_obj,
                tags=tags,
                user_id=current_user["id"],
            )
            db.add(new_tx)
            imported += 1
        except Exception:
            skipped += 1

    db.commit()
    # 🚀 Trong Microservices, sau khi import xong có thể bắn 1 event "BULK_TRANSACTION_CREATED" qua Kafka

    return {
        "total_processed": total_processed,
        "imported": imported,
        "skipped": skipped
    }

# ==========================================
# CÁC API NỘI BỘ (DÀNH RIÊNG CHO AI SERVICE)
# ==========================================

@router.get("/internal/user/{user_id}", response_model=List[schemas.TransactionResponse])
def get_internal_user_transactions(user_id: str, db: Session = Depends(get_db)):
    # 🚀 BÍ KÍP Ở ĐÂY: Bọc thêm str(user_id) để ép cứng nó thành chuỗi chữ
    return db.query(models.Transaction).filter(models.Transaction.user_id == str(user_id)).all()

@router.post("/internal/create", response_model=schemas.TransactionResponse)
def create_internal_transaction(request: Request, data: dict, db: Session = Depends(get_db)):
    user_id_str = request.headers.get("X-Internal-User-Id")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Thiếu thẻ thông hành nội bộ")
    
    new_id = str(uuid.uuid4())
    db_txn = models.Transaction(
        id=new_id,
        name=data.get("name", "Giao dịch AI"),
        amount=data.get("amount", 0.0),
        category=data.get("category", "Khác"),
        date=data.get("date", datetime.now()),
        tags=data.get("tags", ["AI Chatbot"]),
        user_id=str(user_id_str) # Ép kiểu String
    )
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)

    # 🚀 AI BẮN SỰ KIỆN KAFKA CHO HỆ THỐNG
    try:
        kafka_pro.send_transaction_event("TRANSACTION_CREATED", {
            "id": db_txn.id,
            "user_id": db_txn.user_id,
            "jar_id": db_txn.jar_id,
            "amount": float(db_txn.amount),
            "category": db_txn.category
        })
    except Exception as e:
        print("Lỗi Kafka:", e)

    return db_txn

@router.put("/internal/update/{transaction_id}", response_model=schemas.TransactionResponse)
def update_internal_transaction(transaction_id: str, request: Request, data: dict, db: Session = Depends(get_db)):
    user_id_str = request.headers.get("X-Internal-User-Id")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Thiếu thẻ thông hành nội bộ")

    db_txn = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id, 
        models.Transaction.user_id == str(user_id_str)
    ).first()
    
    if db_txn:
        if "name" in data: db_txn.name = data["name"]
        if "amount" in data: db_txn.amount = data["amount"]
        if "category" in data: db_txn.category = data["category"]
        if "date" in data: db_txn.date = data["date"]
        db.commit()
        db.refresh(db_txn)

        # 🚀 BẮN SỰ KIỆN CẬP NHẬT KAFKA
        try:
            kafka_pro.send_transaction_event("TRANSACTION_UPDATED", {
                "id": db_txn.id,
                "user_id": db_txn.user_id,
                "jar_id": db_txn.jar_id,
                "amount": float(db_txn.amount),
                "category": db_txn.category,
                "transaction_date": db_txn.date.isoformat() if db_txn.date else datetime.now().isoformat(),
                "old_amount": old_amount,
                "old_category": old_category,
                "old_jar_id": old_jar_id
            })
        except Exception as e:
            print("Lỗi Kafka:", e)

        return db_txn
    raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")

# ==========================================
# 3. GIAO DỊCH ĐỊNH KỲ (RECURRING)
# ==========================================

@recurring_router.get("/", response_model=List[schemas.RecurringTransactionResponse])
def get_recurring_transactions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.user_id == current_user["id"]
    ).all()

@recurring_router.post("/", response_model=schemas.RecurringTransactionResponse)
def create_recurring_transaction(
    transaction: schemas.RecurringTransactionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    new_id = str(uuid.uuid4())
    db_transaction = models.RecurringTransaction(
        id=new_id,
        name=transaction.name,
        amount=transaction.amount,
        category=transaction.category,
        tags=transaction.tags,
        interval=transaction.interval,
        startDate=transaction.startDate,
        occurrences=transaction.occurrences,
        user_id=current_user["id"],   
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@recurring_router.put("/edit", response_model=schemas.RecurringTransactionResponse)
def update_recurring_transaction(
    id: str,
    updateAll: str,
    transaction: schemas.RecurringTransactionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    db_txn = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.id == id,
        models.RecurringTransaction.user_id == current_user["id"],
    ).first()
    if not db_txn:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch định kỳ")

    db_txn.name = transaction.name
    db_txn.amount = transaction.amount
    db_txn.category = transaction.category
    db_txn.tags = transaction.tags
    db_txn.interval = transaction.interval
    db_txn.startDate = transaction.startDate
    db_txn.occurrences = transaction.occurrences

    db.commit()
    db.refresh(db_txn)
    return db_txn

@recurring_router.delete("/delete")
def delete_recurring_transaction(
    id: str,
    removeAll: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    db_txn = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.id == id,
        models.RecurringTransaction.user_id == current_user["id"],
    ).first()
    if not db_txn:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch định kỳ")

    db.delete(db_txn)
    db.commit()
    return {"message": "Đã xóa thành công"}

# ==========================================
# 4. WEBHOOK TỪ n8n
# ==========================================
def get_user_info_by_email(email: str):
    import requests
    import os
    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8000") 
    try:
        res = requests.get(f"{USER_SERVICE_URL}/api/users/internal/by-email?email={email}")
        if res.status_code == 200:
            return res.json()  # 🚀 Trả về nguyên cục dict {"username": "a", "is_email_sync_enabled": True}
    except Exception as e:
        print("Lỗi khi gọi User Service:", e)
    return None

@router.post("/webhooks/n8n-receipt", tags=["Webhooks"])
def receive_n8n_receipt(
    payload: N8nWebhookPayload,
    x_api_key: str = Header(None),
    db: Session = Depends(get_db)
):
    # 1. KIỂM TRA BẢO MẬT
    if x_api_key != "expenseowl-secret-key-12345":
        raise HTTPException(status_code=401, detail="Sai API Key! Từ chối truy cập.")

    # 2. XÁC ĐỊNH NGƯỜI DÙNG TỪ EMAIL
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', payload.receiver) 
    extracted_email = email_match.group(0).lower() if email_match else ""

    user_info = get_user_info_by_email(extracted_email)
    
    if not user_info or not user_info.get("username"):
        return {"status": "ignored", "message": f"Email {extracted_email} không có trong hệ thống!"}

    if not user_info.get("is_email_sync_enabled"):
        return {"status": "ignored", "message": f"Tài khoản {extracted_email} đang TẮT tính năng tự động hóa Email!"}

    user_id_to_save = user_info.get("username")

    # 3. GỌI AI SERVICE ĐỂ BÓC TÁCH NỘI DUNG THÔ
    raw_text = payload.raw_content
    AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai-service:8000")
    
    try:
        # Thêm timeout để tránh kẹt request
        ai_response = requests.post(f"{AI_SERVICE_URL}/api/ai/extract", json={"text": raw_text}, timeout=15)
        
        if ai_response.status_code == 200:
            ai_data = ai_response.json()
            expense_name = ai_data.get("name", "Auto Receipt")
            
            raw_amount = float(ai_data.get("amount", 0))
            txn_type = ai_data.get("type", "chi")
            
            if txn_type == "chi":
                expense_amount = -abs(raw_amount)
            else:
                expense_amount = abs(raw_amount)
                
            expense_category = ai_data.get("category", "Khác")
            ai_date_str = ai_data.get("date")
            
            try:
                expense_date = datetime.strptime(ai_date_str[:10], "%Y-%m-%d") if ai_date_str else datetime.now()
            except:
                expense_date = datetime.now()
        else:
            # SỬA LỖI: Trả về HTTP 400 để n8n báo lỗi, không tự ý tạo giao dịch 0 đồng
            raise HTTPException(status_code=400, detail=f"AI Service xử lý thất bại! Code: {ai_response.status_code}")
            
    except Exception as e:
        print("Lỗi khi gọi AI:", e)
        # SỬA LỖI: Trả về HTTP 400 để dừng tiến trình
        raise HTTPException(status_code=400, detail=f"Lỗi kết nối AI Service: {str(e)}")

    # 4. LƯU GIAO DỊCH VÀO DATABASE
    new_expense = models.Transaction(
        id=str(uuid.uuid4()),
        name=expense_name[:255],
        category=expense_category,
        amount=expense_amount,
        date=expense_date,
        tags=["Auto-Gmail"],
        user_id=user_id_to_save 
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)

    # 5. SỬA LỖI: BẮN SỰ KIỆN KAFKA ĐỂ BUDGET SERVICE CẬP NHẬT
    try:
        kafka_pro.send_transaction_event("TRANSACTION_CREATED", {
            "id": new_expense.id,
            "user_id": new_expense.user_id,
            "jar_id": None, # Webhook mặc định không vào hũ nào, sẽ trừ ở Số dư khả dụng
            "amount": float(new_expense.amount),
            "category": new_expense.category,
            "transaction_date": new_expense.date.isoformat() if new_expense.date else datetime.now().isoformat()
        })
    except Exception as e:
        print(f"Lỗi gửi Kafka trong Webhook: {e}")

    return {"status": "success", "message": "Biên lai đã được tự động lưu!"}


# # ==========================================
# # JAR MANAGEMENT
# # ==========================================
# jar_router = APIRouter(prefix="/api/jars", tags=["Jars"])

# @jar_router.get("/", response_model=List[schemas.JarResponse])
# def get_jars(
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user),
# ):
#     """Get all jars for current user"""
#     jars = db.query(models.Jar).filter(
#         models.Jar.user_id == current_user["id"]
#     ).order_by(models.Jar.id).all()
    
#     if not jars:
#         # Auto-create default jars if not exists
#         default_jars = [
#             models.Jar(name="Tiền Tiêu Vặt", percent=55, user_id=current_user["id"]),
#             models.Jar(name="Tiền Đầu Tư", percent=10, user_id=current_user["id"]),
#             models.Jar(name="Tiền Tiết Kiệm", percent=10, user_id=current_user["id"]),
#             models.Jar(name="Tiền Cho Tặng", percent=5, user_id=current_user["id"]),
#             models.Jar(name="Tiền Giáo Dục", percent=10, user_id=current_user["id"]),
#             models.Jar(name="Tiền Vui Chơi", percent=10, user_id=current_user["id"]),
#         ]
#         db.add_all(default_jars)
#         db.commit()
#         jars = default_jars
    
#     return jars

# @jar_router.post("/", response_model=schemas.JarResponse)
# def create_jar(
#     jar: schemas.JarCreate,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user),
# ):
#     """Create a new jar"""
#     new_jar = models.Jar(
#         name=jar.name,
#         percent=jar.percent,
#         balance=0.0,
#         goal_amount=jar.goal_amount,
#         color=jar.color,
#         icon=jar.icon,
#         user_id=current_user["id"],
#     )
#     db.add(new_jar)
#     db.commit()
#     db.refresh(new_jar)
#     return new_jar

# @jar_router.put("/{jar_id}", response_model=schemas.JarResponse)
# def update_jar(
#     jar_id: int,
#     jar_update: schemas.JarUpdate,
#     db: Session = Depends(get_db),
#     current_user: dict = Depends(get_current_user),
# ):
#     """Update jar details"""
#     db_jar = db.query(models.Jar).filter(
#         models.Jar.id == jar_id,
#         models.Jar.user_id == current_user["id"]
#     ).first()
    
#     if not db_jar:
#         raise HTTPException(status_code=404, detail="Không tìm thấy hũ")
    
#     if jar_update.name:
#         db_jar.name = jar_update.name
#     if jar_update.percent is not None:
#         db_jar.percent = jar_update.percent
#     if jar_update.goal_amount is not None:
#         db_jar.goal_amount = jar_update.goal_amount
#     if jar_update.color:
#         db_jar.color = jar_update.color
#     if jar_update.icon:
#         db_jar.icon = jar_update.icon
    
#     db.commit()
#     db.refresh(db_jar)
#     return db_jar
