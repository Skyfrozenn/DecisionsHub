from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import DecisionModel, DecisionVoteModel, UserModel



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