import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

load_dotenv()
async_create_engine = create_async_engine(os.getenv('DATABASE_URL'), echo = True)
async_session_maker = async_sessionmaker(async_create_engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass



