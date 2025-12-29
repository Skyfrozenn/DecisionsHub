from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db

from app.models import DecisionModel, UserModel, DecisionVoteModel, DecisionHistoryModel

from app.config import jwt_manager
from app.schemas.decision_history import DecisionHistorySchema
from app.schemas.decisions import DecisionDetailSchema

router = APIRouter(
    prefix="/decisions_history",
    tags=["DECISIONS-HISTORY"]
)

@router.get("/{decision_id}", response_model=DecisionDetailSchema)
async def get_decision(
    decision_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
) -> DecisionDetailSchema:
    stmt = (
        select(
            DecisionModel,
            func.count(DecisionVoteModel.user_id)
            .filter(DecisionVoteModel.is_like.is_(True))
            .label("like"),
            func.count(DecisionVoteModel.user_id)
            .filter(DecisionVoteModel.is_like.is_(False))
            .label("dislike"),
        )
        .outerjoin(DecisionModel.votes)
         
        .where(
            DecisionModel.id == decision_id,
            DecisionModel.is_active.is_(True),
        )
        .group_by(DecisionModel.id)
        .options(
            selectinload(DecisionModel.decision_history.and_(DecisionHistoryModel.is_active == True))  
        )
    )

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена или не активна",
        )

    decision, like, dislike = row

    return DecisionDetailSchema(
        id=decision.id,
        title=decision.title,
        description=decision.description,
        image_url=decision.image_url,
        user_id=decision.user_id,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
        status=decision.status,
        is_active=decision.is_active,
        like=like,
        dislike=dislike,
        decision_history=decision.decision_history   
    )


@router.get("/{decision_history_id}", response_model=DecisionHistorySchema)
async def get_decision_history(
    decision_history_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
) -> DecisionHistorySchema:
    decision_history = await db.scalar(
        select(DecisionHistoryModel)
        .where(
            DecisionHistoryModel.id == decision_history_id,
            DecisionHistoryModel.is_active == True
        )
    )
    
    if decision_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="История обновления не найдена или не активна"
        )
    
    return decision_history


@router.delete("/{decision_history_id}", status_code=status.HTTP_200_OK)
async def delete_decision_history(
    decision_history_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
    decision_history = await db.scalar(
        select(DecisionHistoryModel)
        .where(
            DecisionHistoryModel.id == decision_history_id,
            DecisionHistoryModel.is_active == True
        )
        .options(joinedload(DecisionHistoryModel.decision))
    )
    
    if decision_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="История обновления не найдена или не активна"
        )
    user_id = decision_history.decision.user_id
    if  current_user.role != "admin":
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Доступ запрещен")
    
    await db.execute(
        update(DecisionHistoryModel)
        .where(DecisionHistoryModel.id == decision_history_id)
        .values(is_active=False)
    )
    await db.commit()
    
    return {"status": "success", "message": "История помечена как неактивная"}
