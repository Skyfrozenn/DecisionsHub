from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import DecisionModel, DecisionVoteModel, UserModel, DecisionHistoryModel, CommentModel, CommentVoteModel
from fastapi import HTTPException, status, Depends
from app.database import SyncSessionLocal
from celery import shared_task




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
    


@shared_task
def decision_making(decision_id: int):
    db = SyncSessionLocal()
    try:
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

        result = db.execute(stmt)
        row = result.first()

        if row is None:
            # лучше не кидать HTTPException в таске, см. ниже
            return False

        decision, like, dislike = row

        if dislike >= like:
            return False

        decision_history = DecisionHistoryModel(
            title=decision.title,
            description=decision.description,
            image_url=decision.image_url,
            decision_id=decision.id,
        )

        decision.status = "ready"
        db.add(decision_history)
        db.commit()
        return True
    finally:
        db.close()



async def like_comment(user_id, comment_id, db : AsyncSession):
    comment_vote = await db.scalar(
        select(CommentVoteModel)
        .where(CommentVoteModel.comment_id == comment_id, CommentVoteModel.user_id == user_id)
    )
    if comment_vote:
        if comment_vote.is_like:
            await db.delete(comment_vote)
             

        else:
            comment_vote.is_like = True
    else:
        like_comment = CommentVoteModel(
            user_id = user_id,
            comment_id = comment_id,
            is_like = True
        )
        db.add(like_comment)

    await db.commit()
    return {"status" : "ok"}
   
        
async def dislike_comment(user_id, comment_id, db : AsyncSession):
    comment_vote = await db.scalar(
        select(CommentVoteModel)
        .where(CommentVoteModel.comment_id == comment_id, CommentVoteModel.user_id == user_id)
    )
    if comment_vote:
        if comment_vote.is_like == False:
            await db.delete(comment_vote)
        else:
            comment_vote.is_like = False
    else:
        dislike_comment = CommentVoteModel(
            user_id = user_id,
            comment_id = comment_id,
            is_like = False
        )
        db.add(dislike_comment)

    await db.commit()
    return {"status" : "ok"} 
    
       



     