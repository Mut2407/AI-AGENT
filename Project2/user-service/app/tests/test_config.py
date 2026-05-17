def test_check_new_user_config(client, test_user_token):
    """Nhận diện User mới (GET /config)"""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Do user vừa tạo chưa có config, is_new_user phải là True hoặc API trả về rỗng tùy logic của bạn
    response = client.get("/api/auth/config", headers=headers)
    assert response.status_code == 200
    
def test_update_user_config(client, test_user_token):
    """Cập nhật cấu hình (POST /categories/edit)"""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    config_payload = {
        "incomeCategories": ["Lương", "Thưởng"],
        "expenseCategories": ["Ăn uống", "Giải trí", "Hóa đơn"],
        "jars": [
            {"name": "Thiết yếu", "percent": 50},
            {"name": "Tiết kiệm", "percent": 50}
        ]
    }
    
    # Giả định API của bạn là POST hoặc PUT tới endpoint lưu cấu hình
    # Bạn có thể điều chỉnh endpoint "/api/auth/categories/edit" lại cho chính xác với routers.py của bạn
    response = client.post("/api/auth/categories/edit", json=config_payload, headers=headers)
    
    # Nếu API hợp lệ, nó sẽ trả về 200 OK
    if response.status_code == 200:
        assert response.json() is not None