from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import users
from app.routers import decisions
from app.routers import decision_history


app = FastAPI(
    title="API DecionsHub",
    description="backend service for app DecionsHub",
    version="0.0.1"
)
app.mount("/media",StaticFiles(directory="media"), name="media")

app.include_router(users.router)
app.include_router(decisions.router)
app.include_router(decision_history.router)


@app.get("/")
async def home():
    return {"message" : "Добро пожаловать!"}