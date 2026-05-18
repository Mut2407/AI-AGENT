def test_create_income_transaction(client):
    """INT_02: Ghi giao dịch Thu nhập (Sẽ kích hoạt Kafka chia hũ)"""
    payload = {
        "amount": 10000000,
        "category": "Lương",
        "type": "income",
        "date": "2026-05-18",
        "name": "Lương tháng 5"     
    }
    response = client.post("/api/expenses", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert float(data["amount"]) == 10000000
    assert data["category"] == "Lương"

def test_create_expense_transaction(client):
    """INT_03: Ghi giao dịch Chi tiêu (Sẽ kích hoạt Kafka trừ ngân sách)"""
    payload = {
        "amount": 500000,
        "category": "Ăn uống",
        "type": "expense",
        "date": "2026-05-18",
        "name": "Ăn tối cùng bạn"   
    }
    response = client.post("/api/expenses", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    print("\n[DEBUG JSON TRẢ VỀ]:", data)
    assert float(data["amount"]) == 500000

def test_get_transactions_list(client):
    """INT_01: Xác thực và Truy cập (Lấy danh sách giao dịch)"""
    response = client.get("/api/expenses")
    assert response.status_code == 200
    
    # Vì đã tạo 1 thu nhập, 1 chi tiêu ở 2 hàm test trước, danh sách ít nhất phải có 2 items
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2