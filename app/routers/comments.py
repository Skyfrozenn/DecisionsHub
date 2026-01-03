from fastapi import APIRouter, Depends, HTTPException, status, Response

from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload, outerjoin, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CommentModel, CommentVoteModel, UserModel, DecisionModel
from app.schemas.comments import CommentCreateSchema, CommentSchema, CommentUpdateSchema
from app.db_depends import get_async_db
from app.config import jwt_manager
from app.utilits import like_comment, dislike_comment


router = APIRouter(
    prefix="/comments",
    tags=["Comments"]
)


@router.post("/", response_model=CommentSchema, status_code=status.HTTP_201_CREATED)
async def create_comment(
    new_comment : CommentCreateSchema,
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
) -> CommentSchema:
    decision = await db.get(DecisionModel, new_comment.decision_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Решение не найдено или не активно")
    if new_comment.parent_id is not None:
        parrent_comment = await db.scalar(
            select(CommentModel)
            .where(CommentModel.id == new_comment.parent_id, CommentModel.status == True)
        )
        if parrent_comment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Коммент не найден")
    comment = CommentModel(
        text=new_comment.text,
        decision_id=decision.id,
        user_id=current_user.id,  
        parent_id=new_comment.parent_id
    )
    
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    
    return comment
    

@router.get("/decision/{decision_id}", response_model=list[CommentSchema])
async def comment_decision(decision_id: int, last_id : int | None = None, db: AsyncSession = Depends(get_async_db)):

    filters = [CommentModel.decision_id == decision_id, CommentModel.status == True]
    if last_id is not None:
        filters.append(CommentModel.id > last_id)

    result = await db.execute(
        select(
            CommentModel,
            func.count(CommentVoteModel.user_id)
            .filter(CommentVoteModel.is_like.is_(True)).label("likes"),   
            func.count(CommentVoteModel.user_id)
            .filter(CommentVoteModel.is_like.is_(False)).label("dislikes")  
        )
        .outerjoin(CommentVoteModel, CommentModel.id == CommentVoteModel.comment_id)
        .where(*filters)
        .group_by(CommentModel.id)
        .order_by(CommentModel.created_at.asc())   
        .limit(50)
    )
    
    return [
        CommentSchema(
            id=comment.id, text=comment.text, decision_id=comment.decision_id,
            user_id=comment.user_id, parent_id=comment.parent_id,
            created_at=comment.created_at, updated_at=comment.updated_at,
            status=comment.status, like=likes, dislike=dislikes
        )
        for comment, likes, dislikes in result.all()
    ]


@router.post("/{comment_id}/like", status_code=status.HTTP_201_CREATED)
async def liked_comment(
    comment_id : int,
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
):
    result = await like_comment(user_id=current_user.id, comment_id=comment_id, db=db)
    return result



    
@router.post("/{comment_id}/dislike", status_code=status.HTTP_201_CREATED)
async def disliked_comment(
    comment_id : int,
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
):
    result = await dislike_comment(user_id=current_user.id, comment_id=comment_id, db=db)
    return result




@router.get("/{comment_id}/reply", response_model=list[CommentSchema])
async def reply_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_async_db),
    last_id : int | None = None,
    current_user: UserModel = Depends(jwt_manager.get_current_user),
) -> list[CommentSchema]:
    filters = [CommentModel.parent_id == comment_id, CommentModel.status.is_(True)]
    if last_id is not None:
        filters.append(CommentModel.id > last_id)
    result = await db.execute(
        select(
            CommentModel,
            func.count(CommentVoteModel.id)
            .filter(CommentVoteModel.is_like.is_(True)).label("likes"),
            func.count(CommentVoteModel.id)
            .filter(CommentVoteModel.is_like.is_(False)).label("dislikes"),
        )
        .outerjoin(CommentVoteModel, CommentModel.id == CommentVoteModel.comment_id)
        .where(*filters)
        .group_by(CommentModel.id)
        .order_by(CommentModel.created_at.asc())
        .limit(50)
    )

    rows = result.all()

    return [
        CommentSchema(
            id=comment.id,
            text=comment.text,
            decision_id=comment.decision_id,
            user_id=comment.user_id,
            parent_id=comment.parent_id,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            status=comment.status,
            like=likes,
            dislike=dislikes,
        )
        for comment, likes, dislikes in rows
    ]

@router.put("/{comment_id}", response_model=CommentSchema)
async def update_comment(
    comment_id : int,
    new_comment : CommentUpdateSchema,
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
) -> CommentSchema:
    comment = await db.scalar(
        select(CommentModel)
        .where(
            CommentModel.id == comment_id,
            CommentModel.status.is_(True)
        )
    )
    if comment is None:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Комментарий не найден")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Доступ запрещен")
    await db.execute(update(CommentModel).where(CommentModel.id == comment_id).values(**new_comment.model_dump()))
    await db.commit()
    await db.refresh(comment)
    return comment


    
@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
    comment = await db.scalar(
        select(CommentModel)
        .where(CommentModel.id == comment_id, CommentModel.status.is_(True))
        .options(joinedload(CommentModel.user))
    )
    if comment is None:
        raise HTTPException(404, "Комментарий не найден")
    
    target_user_role = comment.user.role
    
     
    if current_user.role == "user":
        if current_user.id != comment.user_id:
            raise HTTPException(403, "Только свои!")
    
    elif current_user.role == "admin":
        if target_user_role in ["admin", "super_admin"]:
            raise HTTPException(403, "Админы удаляют только юзеров!")
    
     
    
    await db.execute(
        update(CommentModel)
        .where(CommentModel.id == comment_id)
        .values(status=False)
    )
    await db.commit()
    
    return Response(status_code=204)

    
@router.delete("/{comment_id}/hard")
async def hard_delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
    comment = await db.scalar(
        select(CommentModel)
        .options(joinedload(CommentModel.user))
        .where(CommentModel.id == comment_id, CommentModel.status == False)
    )
    
    if not comment:
        raise HTTPException(404, "Комментарий не найден")
    
    target_role = comment.user.role
    
    if current_user.role == "user":
        if current_user.id != comment.user_id:
            raise HTTPException(403, "Только свои!")
    
    elif current_user.role == "admin":
        if target_role in ("admin", "super_admin"):
            raise HTTPException(403, "Админы удаляют только юзеров!")
    
     
    await db.execute(
        delete(CommentModel)
        .where(CommentModel.id == comment_id)
        )
    await db.commit()
    
    return {"status": "deleted", "message": "Комментарий удалён"}
