from pydantic import BaseModel

class Account(BaseModel):
    name:str
    password:str

class Task(BaseModel):
    title:str="home work"
    priority:str="low"



