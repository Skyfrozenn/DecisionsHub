from fastapi import Depends, HTTPException, status
from app.models import UserModel
from app.config import jwt_manager


async def get_admin_user(current_user : UserModel = Depends(jwt_manager.get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Доступ разрешен только админу")
    return current_user
    