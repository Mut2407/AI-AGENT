def test_transaction_amount_zero(client):
    """UT_03: Validation Số tiền - Bắt lỗi số tiền bằng 0"""
    payload = {
        "amount": 0, 
        "category": "Ăn uống", 
        "type": "expense", 
        "date": "2026-05-18",
        "note": "Test lỗi bằng 0"
    }
    response = client.post("/api/expenses", json=payload)
    
    # Do Pydantic Schema chặn lại hoặc logic chặn lại, mã lỗi thường là 422 hoặc 400
    assert response.status_code in [400, 422]

def test_transaction_amount_too_large(client):
    """UT_04: Giới hạn số tiền cực đại (2 Nghìn Tỷ)"""
    payload = {
        "amount": 2000000000000, 
        "category": "Lương", 
        "type": "income", 
        "date": "2026-05-18",
        "note": "Test số tiền quá lớn"
    }
    response = client.post("/api/expenses", json=payload)
    assert response.status_code in [400, 422]