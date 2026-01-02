import uuid

from fastapi import APIRouter, Depends, status, HTTPException,UploadFile, File, Query

from sqlalchemy import select, or_,  func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.decisions import DecisionCreateSchema, DecisionSchema, DecisionSearchSchema, DecisionUpdateSchema
from app.models import DecisionModel, UserModel, DecisionVoteModel, DecisionHistoryModel
from app.config import jwt_manager
from app.db_depends import get_async_db
from app.utilits import like, dislike, decision_making
from app.validation.depends_role import get_admin_user

from pathlib import Path


router = APIRouter(
    prefix="/decisions",
    tags=["Decisions"]
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media" / "decisions"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"image/png", "image/jpg", "image/jpeg"}
MAX_SIZE = 2 * 1024 * 1024

async def save_image(file : UploadFile):
    if file.content_type not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неподходящий формат файла")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл слишком большой")
    extension = Path(file.filename or "").suffix.lower() or "jpg"
    filename = f"{uuid.uuid4()}{extension}"
    file_path = MEDIA_ROOT / filename
    file_path.write_bytes(content)
    return f"/media/decisions/{filename}"







@router.post("/",response_model=DecisionSchema, status_code=status.HTTP_201_CREATED)
async def add_decision(
    decision : DecisionCreateSchema = Depends(DecisionCreateSchema.as_form),
    image : UploadFile | None = File(None),
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user),
):
    new_decision = DecisionModel(
        **decision.model_dump(),
        user_id = current_user.id,        
    )
    if image:
        image_url = await save_image(image)
        new_decision.image_url = image_url
    db.add(new_decision)
    await db.commit()
    await db.refresh(new_decision)
    return new_decision
    





@router.get("/", response_model=DecisionSearchSchema)
async def search_decisions(
    page: int = Query(1, ge=1),
    search: str | None = Query(None),
    status: str | None = Query(
        None,
        pattern=r"^(in_processing|ready)$",
        description="Статус [in_processing|ready]"
    ),
    db: AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
) -> DecisionSearchSchema:
    
    PAGE_SIZE = 20

    filters = [DecisionModel.is_active.is_(True)]

    if status:
        filters.append(DecisionModel.status == status)

    rank = None

    if search:
        search_value = search.strip()
        if search_value:
            ts_query_ru = func.websearch_to_tsquery("russian", search_value)
            ts_query_en = func.websearch_to_tsquery("english", search_value)

            fst_search = or_(
                DecisionModel.tsv.op("@@")(ts_query_ru),
                DecisionModel.tsv.op("@@")(ts_query_en),
            )

            trigram_search = or_(
                DecisionModel.title.op("%")(search_value),
                func.similarity(DecisionModel.title, search_value) > 0.15,
            )

            filters.append(or_(fst_search, trigram_search))

            rank = func.greatest(
                func.ts_rank_cd(DecisionModel.tsv, ts_query_ru),
                func.ts_rank_cd(DecisionModel.tsv, ts_query_en),
                func.similarity(DecisionModel.title, search_value) * 0.5,
            )

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
        .where(*filters)
        .group_by(DecisionModel.id)
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    )

    if rank is not None:
        stmt = stmt.order_by(rank.desc())
    else:
        stmt = stmt.order_by(DecisionModel.created_at.desc())

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        DecisionSchema(
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
        )
        for decision, like, dislike in rows
    ]

    return DecisionSearchSchema(
        page=page,
        page_size=PAGE_SIZE,
        total_size=len(items),
        items=items,
    )






@router.put("/{decision_id}", response_model=DecisionSchema)
async def update_decision(
    decision_id : int,
    new_decision : DecisionCreateSchema = Depends(DecisionUpdateSchema.as_form),
    image : UploadFile | None = File(None),
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
) -> DecisionSchema:
    request_decision = await db.scalars(
        select(DecisionModel)
        .where(DecisionModel.id == decision_id, DecisionModel.is_active == True)
    )
    decision = request_decision.first()
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена или не активна")
    if decision.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Доступ запрещен")
    if image:
        decision.image_url = await save_image(image)
     
    await db.execute(update(DecisionModel).where(DecisionModel.id == decision_id).values(**new_decision.model_dump()))
    await db.commit()
    await db.refresh(decision)
    if decision.status == "ready":
        await decision_making(db=db, decision_id=decision.id)
    return decision
    


@router.get("/{decision_id}", response_model=DecisionSchema)
async def get_decision_info(
    decision_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
) -> DecisionSchema:

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена или не активна",
        )

    decision, like, dislike = row

    return DecisionSchema(
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
    )


@router.delete("/{decision_id}", status_code=status.HTTP_200_OK)
async def in_active_decision(
    decision_id : int,
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
):
    decision = await db.scalar(
        select(DecisionModel)
        .where(DecisionModel.id == decision_id, DecisionModel.is_active == True)
        .options(selectinload(DecisionModel.decision_history))
    )
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена или не активна")
    if current_user.role != "admin":
        if decision.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Удалять чужие данные может только админ")
        
    await db.execute(update(DecisionHistoryModel).where(DecisionHistoryModel.decision_id == decision.id).values(is_active = False))
    await db.execute(update(DecisionModel).where(DecisionModel.id == decision_id).values(is_active = False))
    await db.commit()
    return {"status": "success", "message": "Decision marked as inactive"}




@router.post("/like/{decision_id}")
async def like_decision(
    decision_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
    decision = await db.scalar(
        select(DecisionModel).where(
            DecisionModel.id == decision_id,
            DecisionModel.is_active == True
        )
    )
    
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена"
        )
    
    result = await like(current_user.id, decision_id, db)
    return {"status": "success", "is_like" : result}


@router.post("/dislike/{decision_id}")
async def dislike_decision(
    decision_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(jwt_manager.get_current_user)
):
    decision = await db.scalar(
        select(DecisionModel).where(
            DecisionModel.id == decision_id,
            DecisionModel.is_active == True
        )
    )
    
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена"
        )
    
    result = await dislike(current_user.id, decision_id, db)
    return {"status": "success", "is_like" : result}


    
    
@router.post("/{decision_id}/accept")
async def accept_decision(
    decision_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user=Depends(get_admin_user)
):
    await decision_making(decision_id, db)
    return {"status": "success","message" : "the decision has been made"}


@router.put("/{decision_id}/rolback/{decision_history_id}", response_model=DecisionSchema)
async def rolback_decision(
    decision_id : int,
    decision_history_id : int,
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
):
    decision = await db.scalar(
        select(DecisionModel)
        .where(DecisionModel.id == decision_id, DecisionModel.is_active == True)
    )
    decision_hisory = await db.scalar(
        select(DecisionHistoryModel)
        .where(DecisionHistoryModel.id == decision_history_id, DecisionHistoryModel.is_active == True)
    )
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Решение не найдено")
    if decision_hisory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="История обновления не найдено")
    if current_user.role != "admin":
        if decision.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Доступ запрещен! только админ или создатель решения может его изменять")



    decision.title = decision_hisory.title
    decision.description = decision_hisory.description
    decision.image_url = decision_hisory.image_url

    await db.commit()
    await db.refresh(decision)
    return decision


@router.get("/ready/{user_id}/user", response_model=list[DecisionSchema])
async def get_user_decisions(
    user_id : int,
    last_id : int | None = None,
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
)-> list[DecisionSchema]:
    user = await db.scalar(select(UserModel).where(
        UserModel.is_active == True,
        UserModel.id == user_id
    ))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    filters = [DecisionModel.is_active == True, DecisionModel.user_id == user_id, DecisionModel.status == "ready"]
    if last_id is not None:
        filters.append(DecisionModel.id > last_id)
    request_decision = await db.execute(
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
        .where(*filters)
        .group_by(DecisionModel.id)
        .order_by(DecisionModel.created_at.asc())
        .limit(30)
      
    )
    rows = request_decision.all()
    return [
        DecisionSchema(
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
        )
        for decision, like, dislike in rows
    ]


@router.get("/unaccepted_decisions0/{user_id}/user", response_model=list[DecisionSchema])
async def get_user_decisions(
    user_id : int,
    last_id : int | None = None,
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user)
)-> list[DecisionSchema]:
    user = await db.scalar(select(UserModel).where(
        UserModel.is_active == True,
        UserModel.id == user_id
    ))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    filters = [DecisionModel.is_active == True, DecisionModel.user_id == user_id, DecisionModel.status == "in_processing"]
    if last_id is not None:
        filters.append(DecisionModel.id > last_id)
    request_decision = await db.execute(
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
        .where(*filters)
        .group_by(DecisionModel.id)
        .order_by(DecisionModel.created_at.asc())
        .limit(30)
      
    )
    rows = request_decision.all()
    return [
        DecisionSchema(
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
        )
        for decision, like, dislike in rows
    ]
    
    
    