from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os

# ⚠️ LƯU Ý: SECRET_KEY này PHẢI GIỐNG HỆT với SECRET_KEY bên user-service nhé!
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key_if_env_missing")
ALGORITHM = "HS256"

# Chỉ đường cho file biết cổng đăng nhập ở đâu
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://20.255.59.73:8000/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin (Token không hợp lệ hoặc đã hết hạn)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Giải mã token để lấy user_id (nằm trong trường 'sub')
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
        # Trả về một dictionary chứa ID (khớp với code bên routers.py của em)
        return {"id": user_id}
        
    except JWTError:
        raise credentials_exception