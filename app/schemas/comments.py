from pydantic import BaseModel, Field, PositiveInt, ConfigDict
from typing import Optional
from datetime import datetime


class CommentCreateSchema(BaseModel):
    text : str = Field(..., min_length=1, description="Текст комментария не меньше 1 символа")
    decision_id : PositiveInt = Field(..., description="ID решения")
    parent_id : PositiveInt | None = Field(None, description="Ответ на комментарий")

     
    



class CommentSchema(BaseModel):
    id : PositiveInt
    text : str  
    decision_id : PositiveInt  
    user_id : PositiveInt  
    parent_id : PositiveInt | None  
    created_at : datetime
    updated_at : datetime
    status : bool
    like : int = Field(default=0,ge=0,  description="Колличество лайков")
    dislike : int = Field(default=0,ge=0,  description="Колличество дизлайков")

    model_config = ConfigDict(from_attributes=True)

class CommentUpdateSchema(BaseModel):
    text : str = Field(..., min_length=1, description="Текст комментария")






