from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload, outerjoin
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.users import UserCreateSchema, UserSchema, UserDetailSchema, ChangePasswordSchema, ChangeEmailSchema, RoleUpdateSchema
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


@router.put("/change-password", status_code=200)
async def update_password(
    change_password : ChangePasswordSchema,
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
):
    user = await db.scalar(
        select(UserModel)
        .where(UserModel.id == current_user.id, UserModel.is_active == True)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    
    if not verify_password(change_password.old_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный пароль!")
    if verify_password(change_password.new_password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пароль должен отличаться от предыдушего")
    new_hash_password = hash_password(change_password.new_password)
    await db.execute(update(UserModel).where(UserModel.id == user.id).values(password = new_hash_password))
    await db.refresh(user)
    await db.commit()
    data = {
        "sub" : user.email,
        "role" : user.role,
        "id" : user.id
    }
    access_token = jwt_manager.create_acess_token(data)
    refresh_token = jwt_manager.create_refresh_token(data)
    response = JSONResponse(
        content={"access_token": access_token, "refresh_token": refresh_token},
        headers={"WWW-Authenticate": "Bearer logout"}   
    )
    return response



@router.put("/change-email")
async def update_email(
    change_email : ChangeEmailSchema,  
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
):
    user = await db.scalar(
        select(UserModel)
        .where(UserModel.id == current_user.id, UserModel.is_active == True)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    
    if not verify_password(change_email.password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный пароль!")
    if change_email.new_email == user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Емейл должен отличаться от предыдущего")
    await db.execute(update(UserModel).where(UserModel.id == user.id).values(email = change_email.new_email))
    await db.refresh(user)
    await db.commit()
    data = {
        "sub" : user.email,
        "role" : user.role,
        "id" : user.id
    }
    access_token = jwt_manager.create_acess_token(data)
    refresh_token = jwt_manager.create_refresh_token(data)
    response = JSONResponse(
        content={"access_token": access_token, "refresh_token": refresh_token},
        headers={"WWW-Authenticate": "Bearer logout"}   
    )
    return response

  
@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
    target_user = await db.scalar(
        select(UserModel)
        .where(UserModel.id == user_id, UserModel.is_active.is_(True))
    )
    if target_user is None:
        raise HTTPException(404, "Пользователь не найден")
    
     
    if current_user.role == "user":
        raise HTTPException(403, "Юзеры никого не удаляют!")
    
    elif current_user.role == "admin":
        if target_user.role in ["admin", "super_admin"]:
            raise HTTPException(403, "Админы удаляют только юзеров!")
    
    
    
    await db.execute(
        update(UserModel)
        .where(UserModel.id == user_id)
        .values(is_active=False)
    )
    await db.commit()
    
    return {"status": "success", "message": f"Пользователь {target_user.name} деактивирован"}


@router.delete("/account/self", status_code=200)
async def deactivate_own_account(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
    if not current_user.is_active:
        raise HTTPException(400, "Аккаунт уже неактивен")
    
    await db.execute(
        update(UserModel)
        .where(UserModel.id == current_user.id)
        .values(is_active=False)
    )
    await db.commit()
    
    return {
        "status": "success",
        "message": "✅ Аккаунт деактивирован.",
        "action": "logout"
    }



@router.put("/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_data: RoleUpdateSchema,   
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
     
    if current_user.role != "super_admin":
        raise HTTPException(403, "🚫 Только супер-админы!")
    
    target_user = await db.scalar(
        select(UserModel)
        .where(UserModel.id == user_id, UserModel.is_active.is_(True))
    )
    if not target_user:
        raise HTTPException(404, "Пользователь не найден")
    
     
    target_user.role = role_data.role
    await db.commit()
    
    return {
        "status": "success",
        "message": f"✅ Роль изменена на '{role_data.role}'",
        "user_id": user_id,
        "username": target_user.name
    }


@router.delete("/{user_id}/hard")
async def hard_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
    target_user = await db.scalar(
        select(UserModel)
        .where(UserModel.id == user_id, UserModel.is_active == False)
    )
    
    if not target_user:
        raise HTTPException(404, "Пользователь не найден")
    
    target_role = target_user.role
    
    if current_user.role == "user":
        raise HTTPException(403, "Юзеры никого не удаляют!")
    
    elif current_user.role == "admin":
        if target_role in ("admin", "super_admin"):
            raise HTTPException(403, "Админы удаляют только юзеров!")
    
    if target_user.id == current_user.id:
        raise HTTPException(403, "Нельзя удалить себя!")
    
    await db.delete(target_user)
    await db.commit()
    
    return {"status": "deleted", "message": "Пользователь удалён"}


@router.delete("/me/hard")
async def hard_delete_own_account(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
    if current_user.is_active == True:
        raise HTTPException(400, "Ошибка, аккаунт еще действует")
    
    await db.delete(current_user)
    await db.commit()
    
    return {"status": "deleted", "message": "Собственный аккаунт удалён"}


 




