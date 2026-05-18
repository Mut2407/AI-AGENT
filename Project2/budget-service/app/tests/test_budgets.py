def test_create_budget(client):
    """Test tạo ngân sách mới cho một danh mục (SYS_06)"""
    payload = {
        "start_date": "2026-05-01",
        "end_date": "2026-05-31",
        "period_type": "month",
        "budgets": [
            {
                "category": "Ăn uống",
                "limit_amount": 5000000
            }
        ]
    }
    response = client.post("/api/planning/budgets/bulk", json=payload)
    
    if response.status_code == 422:
        print("\n[DEBUG LỖI 422 TẠO BUDGET]:", response.json())
        
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Đã cập nhật ngân sách thành công!"

def test_get_budgets_list(client):
    """Test lấy danh sách ngân sách hiện có (INT_03)"""
    response = client.get("/api/planning/budgets/current")
    
    if response.status_code == 422:
        print("\n[DEBUG LỖI 422 GET BUDGETS]:", response.json())
        
    assert response.status_code == 200
    
    data = response.json()
    assert "budgets" in data
    assert isinstance(data["budgets"], list)
    
    # Kiểm tra xem mảng budgets có chứa cái "Ăn uống" vừa tạo ở trên không
    assert len(data["budgets"]) >= 1
    assert data["budgets"][0]["category"] == "Ăn uống"
    assert data["budgets"][0]["limit_amount"] == 5000000.0

