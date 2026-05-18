def test_setup_jars(client):
    """Test thiết lập các hũ (Jars) tài chính ban đầu với tỷ lệ % (SYS_02)"""
    payload = [
        {"name": "Thiết yếu", "percent": 50},
        {"name": "Tiết kiệm", "percent": 20},
        {"name": "Đầu tư", "percent": 30}
    ]
    
    # Sửa URL thành /api/planning/jars/bulk
    response = client.post("/api/planning/jars/bulk", json=payload)
    
    if response.status_code == 422:
        print("\n[DEBUG LỖI 422 SETUP JARS]:", response.json())
    
    assert response.status_code in [200, 201]

def test_get_jars_list(client):
    """Test lấy danh sách các hũ và kiểm tra số dư ban đầu"""
    # Sửa URL thành /api/planning/jars
    response = client.get("/api/planning/jars")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    if len(data) > 0:
        assert "name" in data[0]
        assert "percent" in data[0]
        if "balance" in data[0]:
            assert float(data[0]["balance"]) == 0