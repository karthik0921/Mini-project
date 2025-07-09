from .database import Base
from sqlalchemy import Column,Integer,String

class Users(Base):
    __tablename__="users"

    id=Column(Integer,primary_key=True,autoincrement=True,index=True)
    name=Column(String(50))
    email=Column(String(50))