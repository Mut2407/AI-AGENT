from app import auth

def test_password_hashing():
    """UT_01: Test hàm get_password_hash đảm bảo mật khẩu băm đúng."""
    plain_password = "MySuperSecretPassword!"
    hashed = auth.get_password_hash(plain_password)
    assert hashed != plain_password
    assert len(hashed) > 20

def test_verify_password():
    """UT_02: Test hàm verify_password đảm bảo cơ chế so khớp hoạt động chính xác."""
    plain_password = "MySuperSecretPassword!"
    hashed = auth.get_password_hash(plain_password)
    assert auth.verify_password(plain_password, hashed) is True
    assert auth.verify_password("WrongPassword123", hashed) is False

def test_register_and_login_flow(client):
    """INT_01 & SYS_01: Test luồng người dùng (E2E) tạo tài khoản mới và đăng nhập."""
    new_user = {
        "username": "auth_tester",
        "password": "mypassword",
        "email": "auth@example.com",
        "full_name": "Auth Tester",
        "gender": "Nam",           
        "dob": "1995-05-05"
    }
    
    # 1. Đăng ký
    res_register = client.post("/api/auth/register", json=new_user)
    assert res_register.status_code == 200
    assert res_register.json()["username"] == "auth_tester"

    # 2. Đăng nhập (Lưu ý: API login dùng form data chuẩn OAuth2)
    res_login = client.post("/api/auth/login", data={"username": "auth_tester", "password": "mypassword"})
    assert res_login.status_code == 200
    token_data = res_login.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"