from pydantic import Field, field_validator, EmailStr, BaseModel, PositiveInt, ConfigDict
from datetime import datetime



class UserCreateSchema(BaseModel):
    name : str = Field(..., min_length=4, max_length=20, description="Имя пользователя от 4-20 символов")
    email : EmailStr 
    password : str = Field(..., description="Пароль не менее 8 символов!")

    @field_validator("password")
    @classmethod
    def validation_password(cls, value):
        if len(value) < 8:
            raise ValueError("Пароль должен быть не менее 8 символов!")
        if not any(item.isupper() for item in value):
            raise ValueError("В пароле должен быть хоть один большой символ!")
        special_characters = "!@#$%^&*()_+/,.?[]"
        if not any(item  in special_characters for item in value):
            raise ValueError(f" В пароде должен быть хоть один спецсимвол {special_characters}")
        return value


class UserSchema(BaseModel):
    id : PositiveInt
    name : str
    email : str
    role :  str
    created_at : datetime
    is_active : bool

    model_config = ConfigDict(from_attributes=True)


class RefreshToken(BaseModel):
    refresh_token : str


class UserDetailSchema(UserSchema):
    decisions_taken : int = Field(0, ge=0 , description="Принятые решения пользователя")
    unaccepted_decisions : int = Field(0, ge=0 , description="решения пользователя в обработке ")

    model_config = ConfigDict(from_attributes=True)
     




