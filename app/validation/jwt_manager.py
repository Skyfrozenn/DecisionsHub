from fastapi import Depends, status, HTTPException  
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserModel
from app.db_depends import get_async_db
from app.schemas.users import RefreshToken


import jwt

 

from datetime import datetime, timedelta,timezone
 
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")

class JWTManager:
    def __init__(self, algorithm, secret_key, acces_token_expire_minutes, refresh_token_expire_days) :
        self.algorithm = algorithm
        self.__secret_key = secret_key
        self.acces_token_expire_minutes = acces_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
     
    def create_acess_token(self, data : dict):
        to_encody = data.copy() #копируем словарь с данными чтобы не испортить оригинал
        exprire = datetime.now(timezone.utc) + timedelta(minutes=self.acces_token_expire_minutes) #текущее время + 30 минут
        to_encody.update(
            {
            "exp" : exprire,
            "token_types" : "access"
        }
        )
        return jwt.encode(to_encody, self.__secret_key, algorithm = self.algorithm)
    
    def create_refresh_token(self, data : dict):
        to_encody = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days = self.refresh_token_expire_days)
        to_encody.update(
            {
            "exp" : expire,
            "token_types" : "refresh"
            }
        )         
        refresh_token = jwt.encode(to_encody, self.__secret_key, algorithm = self.algorithm)
        return refresh_token
    
    async def get_current_user(self, token : str = Depends(oauth2_scheme), db : AsyncSession = Depends(get_async_db)):
        """
        Функция охранник проверяет акссес токен
        """
        credentals_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось подтвердить учетные данные!",
            headers={"WWW-Authenticate": "Bearer"}
        )
        try:
            payload = jwt.decode(token, self.__secret_key, algorithms=[self.algorithm])   
            email : str | None = payload.get("sub")
            token_types : str | None = payload.get("token_types")
            if email is None or token_types != "access" : #если емейла нет то неверные данные пошел нахуй
                raise credentals_exception
        except jwt.ExpiredSignatureError: #проверка не истекло ли время если да нахуй пошел
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Время токена истекло!",
                headers={"WWW-Authenticate" : "Bearer"}
            )
        except jwt.PyJWTError: #проверка подписи хуедписи всякой хуйни всего джвт 
            raise credentals_exception
        request_user = await db.scalars(
            select(UserModel)
            .where(UserModel.email == email, UserModel.is_active == True)
        )
        user = request_user.first() 
        if user is None: #если юзера нет в бд то тоже идет нахуй
            raise credentals_exception
        return user
    
    async def verify_refresh_token(self, token : RefreshToken, db : AsyncSession = Depends(get_async_db)):  
        credentals_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось подтвердить учетные данные!",
            headers={"WWW-Authenticate": "Bearer"}
        )
        try:
            payload = jwt.decode(token.refresh_token, self.__secret_key, algorithms=[self.algorithm])
            email : str | None = payload.get("sub")
            token_types : str | None = payload.get("token_types")
            if email is None or token_types != "refresh" : # 
                raise credentals_exception
        except jwt.ExpiredSignatureError: 
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Время токена истекло!",
                headers={"WWW-Authenticate" : "Bearer"}
            )
        except jwt.PyJWTError: 
            raise credentals_exception
        request_user = await db.scalars(
            select(UserModel)
            .where(UserModel.email == email, UserModel.is_active == True)
        )
        user = request_user.first()
        if user is None:
            raise credentals_exception
        return user
    
    async def new_access_token(self, user : UserModel ):
        data = {
        "sub" : user.email,
        "role" : user.role,
        "id" : user.id
        }
        return self.create_acess_token(data)
    
    async def new_refresh_token(self, user : UserModel):
        data = {
        "sub" : user.email,
        "role" : user.role,
        "id" : user.id
        }
        return self.create_refresh_token(data)
