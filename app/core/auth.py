# тут простая авторизация через HTTP Basic - логин/пароль для админки
import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


# функция-депенденси которая проверяет что пришёл правильный логин и пароль
def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    # берём логин и пароль из переменных окружения
    expected_user = os.getenv("ADMIN_USER", "admin")
    expected_password = os.getenv("ADMIN_PASSWORD", "")
    if not expected_password:
        raise HTTPException(status_code=500, detail="ADMIN_PASSWORD not configured")
    # compare_digest сравнивает безопасно, чтобы нельзя было угадать по времени ответа
    ok_user = secrets.compare_digest(credentials.username.encode(), expected_user.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), expected_password.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
