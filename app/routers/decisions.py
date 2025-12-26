import uuid

from fastapi import APIRouter, Depends, status, HTTPException,UploadFile, File, Query

from sqlalchemy import select, or_,  func
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.decisions import DecisionCreateSchema, DecisitionSchema, DecisionSearchSchema
from app.models import DecisionModel, UserModel
from app.config import jwt_manager
from app.db_depends import get_async_db

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


def remove_image(url : str):
    if not url:
        return
    relative_path = url.lstrip("/")
    file_path = MEDIA_ROOT / relative_path
    if file_path.exists():
        file_path.unlink()





@router.post("/",response_model=DecisitionSchema, status_code=status.HTTP_201_CREATED)
async def add_decision(
    decision : DecisionCreateSchema = Depends(DecisionCreateSchema.as_form),
    image : UploadFile | None = File(None),
    db : AsyncSession = Depends(get_async_db),
    current_user : UserModel = Depends(jwt_manager.get_current_user),
):
    if image:
        image_url = await save_image(image)
    new_decision = DecisionModel(
        **decision.model_dump(),
        user_id = current_user.id,
        image_url = image_url
    )
    db.add(new_decision)
    await db.commit()
    await db.refresh(new_decision)
    return new_decision
    


@router.get("/", response_model=DecisionSearchSchema)
async def search_decisions(
    page : int =  Query(1, ge=1),
    page_size : int  = Query(10, ge=1),
    search : str | None = Query(None),
    status : str | None = Query(None, pattern=r"^(in_processing|ready)$",description="Cтутус [in_processing|ready]"),
    db : AsyncSession = Depends(get_async_db)    
)-> DecisionSearchSchema:
    filters = [DecisionModel.is_active == True]
    if status is not None:
        filters.append(DecisionModel.status == status)
    if search:
        search_value = search.strip(" ")
        if search_value:
            ts_query_ru = func.websearch_to_tsquery("russian", search_value)
            ts_query_en = func.websearch_to_tsquery("english", search_value)
            fst_search = (
                 or_(
                     DecisionModel.tsv.op('@@')(ts_query_ru),
                     DecisionModel.tsv.op('@@')(ts_query_en)
                 )
            )
            trigram_search = or_(
                DecisionModel.title.op('%')(search_value),
                func.similarity(DecisionModel.title, search_value) > 0.15
            )
            filters.append(
                or_(
                    fst_search, trigram_search
                )
            )
            rank = func.greatest(
            func.ts_rank_cd(DecisionModel.tsv, ts_query_ru),
            func.ts_rank_cd(DecisionModel.tsv, ts_query_en),
            func.similarity(DecisionModel.title, search_value) * 0.5
            )

        
            decision_request = await db.scalars(
                select(DecisionModel)
                .where(*filters)
                .offset((page - 1) * page_size)
                .limit(page_size)
                .order_by(rank.desc())
            )
            items = decision_request.all()
            return DecisionSearchSchema(
                page=page,
                page_size=page_size,
                items=items,
                total_size=len(items)
            )
            
    else :
        request_decision = await db.scalars(
            select(DecisionModel)
            .where(*filters)
            .offset((page-1) * page_size)
            .limit(page_size)
            .order_by(DecisionModel.created_at.desc())
        )
        items = request_decision.all()
        return DecisionSearchSchema(
                    page=page,
                    page_size=page_size,
                    items=items,
                    total_size=len(items)
                )

