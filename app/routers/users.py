from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload, outerjoin
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.users import UserCreateSchema, UserSchema, UserDetailSchema
from app.models import UserModel, DecisionModel
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
    if not verify_password(form.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный пароль",
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
     


@router.get("/", response_model=list[UserDetailSchema])
async def get_users(
    db : AsyncSession = Depends(get_async_db),
    last_id : int | None = None,
    current_user : UserModel = Depends(jwt_manager.get_current_user)
) -> list[UserDetailSchema]:
    filters = [UserModel.is_active == True]
    if last_id is not None:
        filters.append(UserModel.id > last_id)
    request_user = await db.execute(
        select(
            UserModel,
            func.count(DecisionModel.id).filter(DecisionModel.is_active.is_(True), DecisionModel.status == "ready").label("decisions_taken"),
            func.count(DecisionModel.id).filter(DecisionModel.is_active.is_(True), DecisionModel.status == "in_processing").label("unaccepted_decisions")
 
        )
        .where(*filters)
        .outerjoin(UserModel.decisions)
        .group_by(UserModel.id)
        .order_by(UserModel.created_at.desc())
        .limit(30)
    )
    results = request_user.all()
    return [
        UserDetailSchema(
            id = user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
            is_active = user.is_active,
            decisions_taken = decisions_taken,
            unaccepted_decisions = unaccepted_decisions
        )
         
        for user,decisions_taken,unaccepted_decisions in results
    ]



  
