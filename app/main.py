from fastapi import FastAPI
from app.routers import users


app = FastAPI(
    title="API DecionsHub",
    description="backend service for app DecionsHub",
    version="0.0.1"
)
app.include_router(users.router)


@app.get("/")
async def home():
    return {"message" : "Добро пожаловать!"}