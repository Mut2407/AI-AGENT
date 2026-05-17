def test_get_profile(client, test_user_token):
    """Truy xuất thông tin (GET /me)"""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = client.get("/api/auth/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "global_tester"
    assert data["email"] == "global@example.com"

def test_update_profile(client, test_user_token):
    """Cập nhật hồ sơ (PUT /me/update)"""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    update_data = {
        "full_name": "Global Tester Updated",
        "gender": "Nữ",
        "dob": "1995-05-05"
    }
    
    response = client.put("/api/auth/me/update", json=update_data, headers=headers)
    assert response.status_code == 200
    
    # Verify lại dữ liệu đã thay đổi chưa
    res_me = client.get("/api/auth/me", headers=headers)
    assert res_me.json()["full_name"] == "Global Tester Updated"

def test_change_password(client, test_user_token):
    """Đổi mật khẩu (PUT /change-password)"""
    headers = {"Authorization": f"Bearer {test_user_token}"}
    
    # Nhập sai mật khẩu cũ
    wrong_pwd_data = {"old_password": "wrong_password", "new_password": "new_secure_pwd"}
    res_wrong = client.put("/api/auth/change-password", json=wrong_pwd_data, headers=headers)
    assert res_wrong.status_code == 400
    
    # Nhập đúng mật khẩu cũ
    correct_pwd_data = {"old_password": "securepassword123", "new_password": "new_secure_pwd"}
    res_correct = client.put("/api/auth/change-password", json=correct_pwd_data, headers=headers)
    assert res_correct.status_code == 200