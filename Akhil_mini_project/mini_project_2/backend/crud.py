from . import database,models
import re

models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db=database.SessionLocal()
    return db


def insert_user(name:str,email:str):
    created_user=models.Users(name=name,email=email)
    db=get_db()
    db.add(created_user)
    db.commit()
    db.refresh(created_user)
    db.close()
    return created_user

def update_user(user_id:int,new_name:str,new_email:str):
    db=get_db()
    existing_user=db.query(models.Users).filter(models.Users.id==user_id).first()
    existing_user.name=new_name
    existing_user.email=new_email
    db.commit()
    db.close()

def delete_user(user_id:int):
    db=get_db()
    existing_user=db.query(models.Users).filter(models.Users.id==user_id).first()
    db.delete(existing_user)
    db.commit()
    db.close()

def get_all_users():
    db=get_db()
    users=db.query(models.Users).all()
    return users

def check_dup_email(email:str):
    db=get_db()
    users=db.query(models.Users).all()
    for user in users:
        if email==user.email:
            return True

def check_invalid_email(email):
    pattern=r'^[\w\.-]+@[\w\.-]+\.[\w]{2,}$'
    return re.fullmatch(pattern,email) is None

