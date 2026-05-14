from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import uuid
import csv
import io
from fastapi.responses import StreamingResponse
import models, schemas, auth
from database import get_db

router = APIRouter(prefix="/api/expenses", tags=["Expenses"])

@router.get("/", response_model=List[schemas.TransactionResponse])
def get_transactions(db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    return (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == current_user_id)
        .order_by(models.Transaction.date.desc())
        .all()
    )

@router.post("/", response_model=schemas.TransactionResponse)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
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
        user_id=current_user_id,
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@router.put("/{transaction_id}", response_model=schemas.TransactionResponse)
def update_transaction(transaction_id: str, transaction_update: schemas.TransactionCreate, db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    db_txn = (
        db.query(models.Transaction)
        .filter(models.Transaction.id == transaction_id, models.Transaction.user_id == current_user_id)
        .first()
    )
    if not db_txn:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")

    db_txn.name = transaction_update.name
    db_txn.amount = transaction_update.amount
    db_txn.category = transaction_update.category
    db_txn.date = transaction_update.date
    db_txn.tags = transaction_update.tags
    db_txn.note = transaction_update.note
    db_txn.recurring_interval = transaction_update.recurring_interval

    db.commit()
    db.refresh(db_txn)
    return db_txn

@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: str, db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    db_txn = (
        db.query(models.Transaction)
        .filter(models.Transaction.id == transaction_id, models.Transaction.user_id == current_user_id)
        .first()
    )
    if not db_txn:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")

    db.delete(db_txn)
    db.commit()
    return {"message": "Đã xóa thành công"}

@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    transactions = (
        db.query(models.Transaction)
        .filter(models.Transaction.user_id == current_user_id)
        .order_by(models.Transaction.date.desc())
        .all()
    )

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(["Date", "Name", "Category", "Amount", "Tags"])    

    for t in transactions:
        tags_str = ",".join(t.tags) if t.tags else ""
        date_str = t.date.strftime("%Y-%m-%d") if t.date else ""
        writer.writerow([date_str, t.name, t.category, t.amount, tags_str])

    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=ExpenseOwl_Data.csv"})


@router.post("/import/csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    if not file.filename.endswith(".csv"):
        return {"error": "Vui lòng tải lên file định dạng .csv"}

    content = await file.read()
    decoded_content = content.decode("utf-8-sig").splitlines()
    reader = csv.DictReader(decoded_content)

    total_processed = 0
    imported = 0
    skipped = 0

    for row in reader:
        total_processed += 1
        try:
            date_str = row.get("Date", "").strip()
            date_value = None
            if date_str:
                from datetime import datetime
                date_value = datetime.strptime(date_str, "%Y-%m-%d")
            else:
                from datetime import datetime
                date_value = datetime.utcnow()

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
                date=date_value,
                tags=tags,
                user_id=current_user_id,
            )
            db.add(new_tx)
            imported += 1
        except Exception:
            skipped += 1

    db.commit()

    return {
        "total_processed": total_processed,
        "imported": imported,
        "skipped": skipped,
    }


recurring_router = APIRouter(prefix="/api/recurring-expenses", tags=["Recurring Expenses"])


@recurring_router.get("", response_model=List[schemas.RecurringTransactionResponse])
@recurring_router.get("/", response_model=List[schemas.RecurringTransactionResponse])
def get_recurring_transactions(db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    return (
        db.query(models.RecurringTransaction)
        .filter(models.RecurringTransaction.user_id == current_user_id)
        .all()
    )


@recurring_router.post("/", response_model=schemas.RecurringTransactionResponse)
def create_recurring_transaction(transaction: schemas.RecurringTransactionCreate, db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
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
        user_id=current_user_id,
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction


@recurring_router.delete("/delete")
def delete_recurring_transaction(id: str, removeAll: str, db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    db_txn = (
        db.query(models.RecurringTransaction)
        .filter(models.RecurringTransaction.id == id, models.RecurringTransaction.user_id == current_user_id)
        .first()
    )
    if not db_txn:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch định kỳ")

    db.delete(db_txn)
    db.commit()
    return {"message": "Đã xóa thành công"}


@recurring_router.put("/edit", response_model=schemas.RecurringTransactionResponse)
def update_recurring_transaction(id: str, updateAll: str, transaction: schemas.RecurringTransactionCreate, db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    db_txn = (
        db.query(models.RecurringTransaction)
        .filter(models.RecurringTransaction.id == id, models.RecurringTransaction.user_id == current_user_id)
        .first()
    )
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
