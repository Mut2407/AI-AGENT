import jwt
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user_id(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise credentials_exception

    # Prefer explicit user_id in token payload (recommended)
    user_id = payload.get("user_id")
    if user_id:
        try:
            return int(user_id)
        except Exception:
            raise credentials_exception

    # Fallback to 'sub' claim. If numeric, return as id.
    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception

    try:
        return int(sub)
    except Exception:
        # If sub is username (string), we expect user_id to be present.
        # Integrating with user-service would be ideal; for now require user_id.
        raise HTTPException(
            status_code=401,
            detail="Token không chứa user_id. Vui lòng cấu hình user-service để nhúng user_id vào token.",
        )