from pydantic import BaseModel, Field, PositiveInt, ConfigDict
from fastapi import Form

from typing import Optional, Annotated
from datetime import datetime




class DecisionCreateSchema(BaseModel):
    title : str = Field(..., min_length=4, max_length=20, description="Название решения от 4-20 символов")
    description : Optional[str] = Field(None, description="Описание решения от 4-20 символов")
    
    
    @classmethod
    def as_form(
        cls,
        title : Annotated[str, Form(...)],
        description : Annotated[Optional[str], Form()] = None,
    ):
        return cls(title=title, description=description)
        
class DecisitionSchema(BaseModel):
    id : PositiveInt
    title : str
    description : Optional[str]
    image_url : Optional[str]
    user_id : PositiveInt
    created_at : datetime
    updated_at : datetime
    status : str
    is_active : bool
    like : int = Field(default=0, ge=0, description="Количество лайков")
    dislike : int = Field(default=0,ge=0,  description="Количество дизлайков")

    model_config = ConfigDict(from_attributes=True)



class DecisionSearchSchema(BaseModel):
    page : int  = Field(ge=1, description="Страница записи, больше или равно одному")
    page_size : int  = Field(ge=1, description="Количество решений")
    items : list[DecisitionSchema] = Field(default_factory=list, description="Список решений")
    total_size : int = Field(ge=0)
    

    model_config = ConfigDict(from_attributes=True)
 


    