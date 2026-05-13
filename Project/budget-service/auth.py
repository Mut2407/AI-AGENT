import jwt, os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user_id(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub") # Hoặc user_id nếu bạn lưu trong token
        # Trong thực tế, bạn có thể gọi User Service để lấy ID thật từ username
        # Hoặc User Service khi tạo token nên nhúng luôn user_id vào payload.
        return 1 # Giả lập user_id cho mục đích test ban đầu
    except:
        raise HTTPException(status_code=401, detail="Xác thực thất bại")