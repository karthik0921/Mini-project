from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base

url="sqlite:///mini_project_2/backend/users_db.db"

engine=create_engine(url)

Base=declarative_base()

SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)