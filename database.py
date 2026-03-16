import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from typing import Optional
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL:Optional[str]=os.getenv("DATABASE_URL")
if DATABASE_URL==None:
    raise ValueError("DATABASE_URL is not set in environmnet variables")

engine=create_engine(DATABASE_URL)

Base=declarative_base()


SessionLocal=sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db=SessionLocal()
    try:
        yield db              # yield splits execution into two phases:before request and after request. unlike return it waits untill endpoint executes
    finally:
        db.close()
        
        