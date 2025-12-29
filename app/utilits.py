from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import DecisionModel, DecisionVoteModel, UserModel, DecisionHistoryModel
from fastapi import HTTPException, status



async def like(
    user_id: int,
    decision_id: int,
    db: AsyncSession,
):
    
    vote = await db.scalar(
        select(DecisionVoteModel).where(
            DecisionVoteModel.user_id == user_id,
            DecisionVoteModel.decision_id == decision_id,
        )
    )
    
    if vote:
        if vote.is_like:
            await db.delete(vote)
            await db.commit()
            return None  
        else:    
            vote.is_like = True
            await db.commit()
            await db.refresh(vote)
            return True
    else:
        
        vote = DecisionVoteModel(
            user_id=user_id,
            decision_id=decision_id,
            is_like=True
        )
        db.add(vote)  
        await db.commit()
        await db.refresh(vote)
        return True


async def dislike(
    user_id: int,
    decision_id: int,
    db: AsyncSession,
):
   
    vote = await db.scalar(
        select(DecisionVoteModel).where(
            DecisionVoteModel.user_id == user_id,
            DecisionVoteModel.decision_id == decision_id,
        )
    )
    
    if vote:
        if not vote.is_like:
            # Уже дизлайк → убираем
            await db.delete(vote)
            await db.commit()
            return None  
        else:
            # Лайк → меняем на дизлайк
            vote.is_like = False
            await db.commit()
            await db.refresh(vote)
            return False
    else:
        # Нет голоса → создаём дизлайк
        vote = DecisionVoteModel(
            user_id=user_id,
            decision_id=decision_id,
            is_like=False
        )
        db.add(vote)  
        await db.commit()
        await db.refresh(vote)
        return False
    

async def decision_making(decision_id, db : AsyncSession):
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
    )

    result = await db.execute(stmt)
    row = result.first()
     

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Решение не найдено")
    
    decision, like, dislike = row #распаковка данных

    if dislike >= like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Решение не может быть принято из количества дизлайков")
    
    decision_history = DecisionHistoryModel(
        title=decision.title,
        description=decision.description,
        image_url=decision.image_url,
        decision_id=decision.id  
    )
    
    decision.status = "ready"
    db.add(decision_history)
    await db.commit()  
    
    return True
    
    
       



     