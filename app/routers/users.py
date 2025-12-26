from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.users import UserCreateSchema, UserSchema
from app.models import UserModel
from app.db_depends import get_async_db
from app.validation.hash_password import hash_password,verify_password
from app.config import jwt_manager

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def new_user(new_user : UserCreateSchema, db : AsyncSession = Depends(get_async_db)) -> UserSchema:
    request_user = await db.scalar(select(UserModel).where(UserModel.email == new_user.email))
    if request_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует")
    user = UserModel(
        name = new_user.name,
        email = new_user.email,
        password = hash_password(new_user.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/token", status_code=status.HTTP_201_CREATED)
async def login(
    form : OAuth2PasswordRequestForm = Depends(),
    db : AsyncSession = Depends(get_async_db)
):
    user = await db.scalar(
        select(UserModel)
        .where(UserModel.email == form.username, UserModel.is_active == True)
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователя не существует или не активен",
            headers={"WWW-Authenticate" : "Bearer"}
        )
    data = {
        "sub" : user.email,
        "role" : user.role,
        "id" : user.id
    }
    access_token = jwt_manager.create_acess_token(data)
    refresh_token = jwt_manager.create_refresh_token(data)
    return {"access_token": access_token,"refresh_token" : refresh_token, "token_type": "bearer"}

@router.post("/acces-token")
async def update_acces_token(user : UserModel = Depends(jwt_manager.verify_refresh_token)):
    return await jwt_manager.new_access_token(user)

@router.post("/refresh-token")
async def update_refresh_token(user : UserModel = Depends(jwt_manager.verify_refresh_token)):
    return await jwt_manager.new_refresh_token(user)
     