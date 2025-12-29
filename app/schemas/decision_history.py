from pydantic import BaseModel, ConfigDict


class DecisionHistorySchema(BaseModel):
    id : int
    title : str
    description : str | None
    image_url : str | None
    decision_id : int
    is_active : bool

    model_config = ConfigDict(from_attributes=True)