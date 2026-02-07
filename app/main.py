from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager

from app.celery_app import celery_app

from app.routers import users
from app.routers import decisions
from app.routers import decision_history
from app.routers import comments



@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- ЭТО ВЫПОЛНИТСЯ ПРИ СТАРТЕ ---
    print("🚀 Приложение запускается...")
    try:    
        with celery_app.broker_connection() as connection:#открывает соединение с брокером
            connection.ensure_connection(max_retries=3) #проверяет соединение с брокером 3 раза
        print("✅ Связь с Redis для Celery установлена!")
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")

    yield  # --- ПАУЗА: В этот момент FastAPI работает и ждет юзеров --- 
    print("🛑 Приложение останавливается...")



app = FastAPI(
    title="API DecisionsHub",
    description="backend service for app DecisionsHub",
    version="0.0.1",
    lifespan=lifespan
)
 
app.mount("/media",StaticFiles(directory="media"), name="media")

app.include_router(users.router)
app.include_router(decisions.router)
app.include_router(decision_history.router)
app.include_router(comments.router)


@app.get("/")
async def home():
    return {"message" : "Добро пожаловать!"}