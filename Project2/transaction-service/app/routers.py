from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import uuid
import csv
import io
import re
from datetime import datetime
from decimal import Decimal


# Import nội bộ của Transaction Service
import models, schemas
from database import get_db

# Giả định em đã có file kafka_pro.py như Cú Mèo hướng dẫn ở bước trước
import kafka_pro 

# Giả định hàm get_current_user giờ đây chỉ giải mã JWT để lấy user_id 
# (Không query Database để lấy cả bảng User nữa vì bảng User nằm ở service khác)
from auth import get_current_user 

# ==========================================
# HELPER FUNCTIONS: JAR + BUDGET
# ==========================================

def distribute_to_jars(db: Session, user_id: str, income_amount: float):
    """Phân tiền thu nhập vào 6 hũ theo tỷ lệ phần trăm"""
    user_jars = db.query(models.Jar).filter(models.Jar.user_id == user_id).order_by(models.Jar.id).all()
    if not user_jars:
        return

    for jar in user_jars:
        if jar.percent > 0:
            allocated_money = Decimal(str(income_amount)) * (jar.percent / Decimal('100'))
            jar.balance += allocated_money
    db.commit()


def update_budget_spent(db: Session, user_id: str, category: str, spent_amount: float):
    """Cập nhật số tiền đã chi tiêu cho từng budget theo category"""
    # Tạm thời chỉ tracking, có thể mở rộng để kiểm tra quá budget
    pass


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
    
    # 🚀 JAR + BUDGET LOGIC từ monolith
    if transaction.amount > 0:  # Income
        distribute_to_jars(db, current_user["id"], float(transaction.amount))
    elif transaction.amount < 0:  # Expense
        if transaction.jar_id:
            jar = db.query(models.Jar).filter(
                models.Jar.id == transaction.jar_id,
                models.Jar.user_id == current_user["id"]
            ).first()
            if jar:
                if jar.balance < abs(transaction.amount):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Quỹ '{jar.name}' không đủ tiền! (Hiện chỉ còn {jar.balance:,.0f})"
                    )
                jar.balance -= Decimal(str(abs(transaction.amount)))
                db.add(jar)
        
        update_budget_spent(db, current_user["id"], transaction.category, abs(transaction.amount))
    
    db.commit()
    db.refresh(db_transaction)

    # 🚀 MICROSERVICE MAGIC: Gửi event qua Kafka
    kafka_pro.send_transaction_event("TRANSACTION_CREATED", {
         "id": db_transaction.id,
         "user_id": db_transaction.user_id,
         "jar_id": db_transaction.jar_id,
         "amount": float(db_transaction.amount),
         "category": db_transaction.category,
         "transaction_date": db_transaction.date.isoformat()
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

    # Lưu lại số tiền cũ để gửi Kafka bù trừ (nếu cần)
    old_amount = db_txn.amount

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
    # kafka_pro.send_transaction_event("TRANSACTION_UPDATED", {...})

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

    # 🚀 JAR REFUND LOGIC
    if db_txn.amount < 0 and jar_id:
        # Hoàn tiền vào hũ khi xóa giao dịch chi tiêu
        jar = db.query(models.Jar).filter(
            models.Jar.id == jar_id,
            models.Jar.user_id == current_user["id"]
        ).first()
        if jar:
            jar.balance += Decimal(str(abs(amount_to_refund)))
            db.add(jar)

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
from pydantic import BaseModel

class N8nWebhookPayload(BaseModel):
    source: str
    sender: str
    receiver: str
    raw_content: str

# Hàm này sẽ gọi sang User Service để lấy user_id dựa vào email
def get_user_id_by_email(email: str):
    import requests
    import os
    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
    try:
        # Giả định User Service có API nội bộ để check email
        res = requests.get(f"{USER_SERVICE_URL}/api/users/internal/by-email?email={email}")
        if res.status_code == 200:
            return res.json().get("id")
    except:
        pass
    return None

@router.post("/webhooks/n8n-receipt", tags=["Webhooks"])
def receive_n8n_receipt(
    payload: dict, # Dữ liệu n8n gửi qua sau khi đã làm sạch và ép kiểu JSON
    db: Session = Depends(get_db)
):
    # Trong Microservices, n8n NÊN thực hiện gọi AI ở 1 service trung gian hoặc luồng riêng
    # Đoạn này giả định n8n đã gửi kèm JSON bóc tách sẵn (hoặc em gọi sang AI-Service)
    
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', payload.get("receiver", ""))
    extracted_email = email_match.group(0).lower() if email_match else ""

    # Lấy User ID từ User Service
    user_id_to_save = get_user_id_by_email(extracted_email)
    if not user_id_to_save:
        return {"status": "ignored", "message": "Email người nhận không có trong hệ thống!"}

    # Lưu giao dịch
    new_expense = models.Transaction(
        id=str(uuid.uuid4()),
        name=payload.get("name", "Auto Receipt")[:255],
        category=payload.get("category", "Khác"),
        amount=float(payload.get("amount", 0)),
        date=datetime.now(),
        tags=["Auto-Gmail"],
        user_id=user_id_to_save 
    )
    db.add(new_expense)
    db.commit()

    # 🚀 Bắn Kafka event
    # kafka_pro.send_transaction_event("TRANSACTION_CREATED", {...})

    return {"status": "success", "message": "Biên lai đã được tự động lưu!"}


# ==========================================
# JAR MANAGEMENT
# ==========================================
jar_router = APIRouter(prefix="/api/jars", tags=["Jars"])

@jar_router.get("/", response_model=List[schemas.JarResponse])
def get_jars(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get all jars for current user"""
    jars = db.query(models.Jar).filter(
        models.Jar.user_id == current_user["id"]
    ).order_by(models.Jar.id).all()
    
    if not jars:
        # Auto-create default jars if not exists
        default_jars = [
            models.Jar(name="Tiền Tiêu Vặt", percent=55, user_id=current_user["id"]),
            models.Jar(name="Tiền Đầu Tư", percent=10, user_id=current_user["id"]),
            models.Jar(name="Tiền Tiết Kiệm", percent=10, user_id=current_user["id"]),
            models.Jar(name="Tiền Cho Tặng", percent=5, user_id=current_user["id"]),
            models.Jar(name="Tiền Giáo Dục", percent=10, user_id=current_user["id"]),
            models.Jar(name="Tiền Vui Chơi", percent=10, user_id=current_user["id"]),
        ]
        db.add_all(default_jars)
        db.commit()
        jars = default_jars
    
    return jars

@jar_router.post("/", response_model=schemas.JarResponse)
def create_jar(
    jar: schemas.JarCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new jar"""
    new_jar = models.Jar(
        name=jar.name,
        percent=jar.percent,
        balance=0.0,
        goal_amount=jar.goal_amount,
        color=jar.color,
        icon=jar.icon,
        user_id=current_user["id"],
    )
    db.add(new_jar)
    db.commit()
    db.refresh(new_jar)
    return new_jar

@jar_router.put("/{jar_id}", response_model=schemas.JarResponse)
def update_jar(
    jar_id: int,
    jar_update: schemas.JarUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update jar details"""
    db_jar = db.query(models.Jar).filter(
        models.Jar.id == jar_id,
        models.Jar.user_id == current_user["id"]
    ).first()
    
    if not db_jar:
        raise HTTPException(status_code=404, detail="Không tìm thấy hũ")
    
    if jar_update.name:
        db_jar.name = jar_update.name
    if jar_update.percent is not None:
        db_jar.percent = jar_update.percent
    if jar_update.goal_amount is not None:
        db_jar.goal_amount = jar_update.goal_amount
    if jar_update.color:
        db_jar.color = jar_update.color
    if jar_update.icon:
        db_jar.icon = jar_update.icon
    
    db.commit()
    db.refresh(db_jar)
    return db_jar