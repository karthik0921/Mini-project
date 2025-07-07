from bson import ObjectId
from fastapi import APIRouter,Depends,HTTPException
import models,schemas
from database import connection
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from jose import jwt,JWTError
from datetime import datetime, timedelta,date
import json

SECRET_KEY="TASKSADDEDANDUPDATED"
ALGORITHM="HS256"
TIME=15

route=APIRouter()

pwd=CryptContext(schemes=['bcrypt'],deprecated="auto")

oauth=OAuth2PasswordBearer(tokenUrl="login")

def get_user(name:str):
    return connection.account.find_one({"name":name})

def authenticate(name:str,password:str):
    user=get_user(name)
    if not user or not pwd.verify(password,user["password"]):
        return False
    return user

def get_current_user(token:str=Depends(oauth)):
    exception=HTTPException(status_code=404,detail="Unauthorized")
    try:
        payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        user_name=payload.get("sub")
    except JWTError:
        raise exception
    user=get_user(user_name)
    return user

def read_file(file):
    with open(file,"r") as f:
        data=json.load(f)
    return data

def write_file(file,data):
    with open(file,"w") as f:
        json.dump(data,f)

@route.post("/create_account")
def create_account(user:models.Account):
    is_user=connection.account.find_one({"name":user.name})
    if not is_user:
        user.password=pwd.hash(user.password)
        connection.account.insert_one(dict(user))
        data=read_file("time.json")
        data[user.name]=[]
        write_file("time.json",data)
        datas=read_file("priority.json")
        datas[user.name]={}
        write_file("priority.json",datas)
        return f"{user.name} registered successfully !!!"
    return f"{user.name} account already exists"


@route.post("/update_account")
def update_account(user:models.Account):
    is_user = connection.account.find_one({"name": user.name})
    if not is_user :
        raise HTTPException(status_code=404,detail="User not available !!!")
    if pwd.verify(user.password,is_user["password"]):
        raise HTTPException(status_code=400,detail="Currently given password is same to the current password !!!")
    password=pwd.hash(user.password)
    connection.account.find_one_and_update({"name":user.name},{"$set":{"password":password}})
    return f"{user.name} account updated successfully !!!"

@route.delete("/delete_account")
def delete_account(user:models.Account):
    is_user = connection.account.find_one({"name": user.name})
    if not is_user or not pwd.verify(user.password,is_user["password"]):
        raise HTTPException(status_code=404,detail="Incorrect Username or Password !!!")
    connection.tasks.delete_many({"user_id":ObjectId(is_user["_id"])})
    connection.account.find_one_and_delete({"name":user.name})
    data=read_file("time.json")
    data.pop(user.name)
    write_file("time.json",data)
    data=read_file("priority.json")
    data.pop(user.name)
    write_file("priority.json",data)
    return f"{user.name} account deleted !!!"



@route.post("/login",tags=["ACCOUNT"])
def login(form:OAuth2PasswordRequestForm=Depends()):
    user=authenticate(name=form.username,password=form.password)
    if not user:
        raise HTTPException(status_code=404,detail="Incorrect Username or Password")
    expires_time=datetime.utcnow()+timedelta(minutes=TIME)
    data={"sub":form.username,"exp":expires_time}
    encode=jwt.encode(data,SECRET_KEY,ALGORITHM)
    return {"access_token":encode,"token_type":"Bearer"}

@route.get("/get_user",tags=["ACCOUNT"])
def get_user_account(current_user:dict=Depends(get_current_user)):
    return {"name":current_user["name"]}

def is_available(user,s_t,e_t,priority,count):

    data = read_file("time.json")
    s_t_h, s_t_m = s_t.hour, s_t.minute
    e_t_h, e_t_m = e_t.hour, e_t.minute
    now = datetime.now()
    if now.hour > s_t_h or (now.hour == s_t_h and now.minute > s_t_m):
        return "not create"
    new_start = timedelta(hours=s_t_h, minutes=s_t_m)
    new_end = timedelta(hours=e_t_h, minutes=e_t_m)
    new_entry = [s_t_h, s_t_m, e_t_h, e_t_m, priority, count]
    if user not in data:
        data[user] = [new_entry]
        write_file("time.json", data)
        return True
    for entry in data[user]:
        existing_start = timedelta(hours=entry[0], minutes=entry[1])
        existing_end = timedelta(hours=entry[2], minutes=entry[3])
        if new_start < existing_end and existing_start < new_end:
            return False
    data[user].append(new_entry)
    data[user].sort(key=lambda x: (x[0], x[1]))
    write_file("time.json", data)
    return True

def get_intervals(s_t_h,s_t_m,e_t_h,e_t_m,name):
    data=read_file("time.json")
    start_input = timedelta(hours=s_t_h, minutes=s_t_m)
    end_input = timedelta(hours=e_t_h, minutes=e_t_m)
    result_indices = []
    for entry in data.get(name):
        start_entry = timedelta(hours=entry[0], minutes=entry[1])
        end_entry = timedelta(hours=entry[2], minutes=entry[3])
        if start_input < end_entry and start_entry < end_input:
            result_indices.append(entry)
    return result_indices

@route.post("/create_task",tags=["Task"])
def create_task(task:models.Task,start_time_hour:int,start_time_minute:int,end_time_hour:int,end_time_minute:int,current_user:dict=Depends(get_current_user)):
    if (start_time_hour>end_time_hour) or (start_time_hour==end_time_hour and start_time_minute>end_time_minute):
        raise HTTPException(status_code=404,detail="Starting hour is greater than Ending hour !!!")
    count=connection.tasks.find({"user_id":ObjectId(current_user["_id"])}).sort("_id",-1).limit(1)
    count=next(count,None)
    now=datetime.now()
    start_time=datetime(now.year,now.month,now.day,start_time_hour,start_time_minute)
    end_time=datetime(now.year,now.month,now.day,end_time_hour,end_time_minute)
    if count:
        count1=count["task_number"]+1
    else:
        count1=1
    priority=is_available(current_user["name"],start_time,end_time,task.priority,count1)
    if priority=="not create":
        raise HTTPException(status_code=404,detail="Task cannot be allocated in the past time !!! ")
    elif priority:
        task_insert={
            "user_id":current_user["_id"],
            "task_number":count1,
            "title":task.title,
            "start_time":start_time,
            "end_time":end_time,
            "status":False,
            "percentage":0,
            "priority":task.priority
        }
        connection.tasks.insert_one(task_insert)
        return f"{task.title} task added !!!"
    else:
        intervals = get_intervals(start_time.hour,start_time.minute, end_time.hour,end_time.minute, current_user["name"])
        task_count = 0
        for i in intervals:
            if i[4] == "low":
                task_count += 1
            elif i[4] == "high":
                raise HTTPException(status_code=404, detail="Important task taking place in that time !!!")
        if task_count>0:
            data=read_file("priority.json")
            count=len(data[current_user["name"]])+1
            data[current_user["name"]].update({count:[intervals,[intervals[0][5],task.title,start_time.hour,start_time.minute,end_time.hour,end_time.minute,task.priority]]})
            write_file("priority.json",data)
            raise HTTPException(status_code=404,detail=f"{task_count} number of tasks are taking place if you want to replace to the new task given , then change using the id number {count}")


@route.post("/change_time_task",tags=["Task"])
def change_time_task(task_change_id:int,current_user:dict=Depends(get_current_user)):
    data=read_file("priority.json")
    change_data=data[current_user["name"]][str(task_change_id)]
    datas=read_file("time.json")
    for i in range(0,len(datas[current_user["name"]])):
        if datas[current_user["name"]][i][5]==change_data[0][0][5]:
            for j in range(0,len(change_data[0])):
                datas[current_user["name"]].pop(i)
                connection.tasks.find_one_and_delete({"user_id":ObjectId(current_user["_id"]),"task_number":change_data[0][j][5]})
            data[current_user["name"]].pop(str(task_change_id))
            if i>=len(datas[current_user["name"]]):
                datas[current_user["name"]].append([change_data[1][2],change_data[1][3],change_data[1][4],change_data[1][5],change_data[1][6],change_data[1][0]])
            else:
                datas[current_user["name"]].insert(i,[change_data[1][2],change_data[1][3],change_data[1][4],change_data[1][5],change_data[1][6],change_data[1][0]])
            now = date.today()
            start_time = datetime(now.year, now.month, now.day, change_data[1][2], change_data[1][3])
            end_time = datetime(now.year, now.month, now.day, change_data[1][4], change_data[1][5])
            task_insert = {
                "user_id": current_user["_id"],
                "task_number": change_data[1][0],
                "title": change_data[1][1],
                "start_time": start_time,
                "end_time": end_time,
                "status": False,
                "percentage": 0,
                "priority": change_data[1][6]
            }
            connection.tasks.insert_one(task_insert)
            break
    write_file("priority.json",data)
    write_file("time.json",datas)
    return "Tasks replaced successfully !!!"


@route.get("/get_all_task",tags=["Task"])
def get_all_task(current_user:dict=Depends(get_current_user)):
    tasks=connection.tasks.find({"user_id":ObjectId(current_user["_id"])})
    return schemas.get_many(tasks)


def get_percentage_task(task,current_user_id,task_number):
    if task["status"]!=True :
        full_time=(task["end_time"].hour-task["start_time"].hour)*60+(task["end_time"].minute-task["start_time"].minute)
        now=datetime.now()
        now_time=(now.hour-task["start_time"].hour)*60+(now.minute-task["start_time"].minute)
        if now_time<0:
            return "not started"
        elif now_time>=full_time:
            connection.tasks.find_one_and_update({"user_id": ObjectId(current_user_id), "task_number": task_number},{"$set": {"percentage": 100, "status": True}})
            return True
        else:
            percent = int((1-((full_time - now_time) / full_time)) * 100)
            print(percent, full_time, now_time)
            connection.tasks.find_one_and_update({"user_id": ObjectId(current_user_id), "task_number": task_number},{"$set": {"percentage":percent}})
            return percent
    return True

@route.get("/get_percentage",tags=["Task"])
def get_percentage(task_id:int,current_user:dict=Depends(get_current_user)):
    task=connection.tasks.find_one({"user_id":ObjectId(current_user["_id"]),"task_number":task_id})
    if not task:
        raise HTTPException(status_code=404,detail=f"Task id {task_id} doesn't exists !!!")
    task_details=get_percentage_task(task,current_user["_id"],task_id)
    if task_details==True:
        return f"{task["title"]} has completed 100% "
    elif task_details=="not started":
        raise HTTPException(status_code=404, detail="The task is not yet started !!!")
    else:
        return f"{task["title"]} has completed {task_details}% "


@route.post("/update_task",tags=["Task"])
def update_task(task_id:int,start_time_hour:int|None=None,start_time_minute:int|None=None,end_time_hour:int|None=None,end_time_minute:int|None=None,current_user:dict=Depends(get_current_user)):
    tasks=connection.tasks.find_one({"user_id":ObjectId(current_user["_id"]),"task_number":task_id})
    if not tasks:
        raise HTTPException(status_code=404, detail=f"Task id {task_id} doesn't exists !!!")
    task_details=get_percentage_task(tasks,current_user["_id"],task_id)
    if task_details==True:
        raise HTTPException(status_code=404,detail=f"{tasks["title"]} already completed so you can't reallocate the task !!!")
    elif task_details!="not started":
        raise HTTPException(status_code=404,detail=f"{tasks["title"]} already started so you can't change the timing of the task !!!")
    else:
        if tasks["start_time"].hour==start_time_hour and tasks["start_time"].minute==start_time_minute and tasks["end_time"].hour==end_time_hour and tasks["end_time"].minute==end_time_minute:
            raise HTTPException(status_code=404,detail="Newly given time and old timings are same !!!")
        else:
            now = date.today()
            if start_time_hour==None:
                start_time_hour=tasks["start_time"].hour
            if start_time_minute==None:
                start_time_minute=tasks["start_time"].minute
            if end_time_hour==None:
                end_time_hour=tasks["end_time"].hour
            if end_time_minute==None:
                end_time_minute=tasks["end_time"].minute
            start_time = datetime(now.year, now.month, now.day, start_time_hour, start_time_minute)
            end_time = datetime(now.year, now.month, now.day, end_time_hour, end_time_minute)
            data=read_file("time.json")
            before_hour=-1
            before_minute=-1
            count=0
            datas=data[current_user["name"]]
            for i in range(0,len(datas)):
                if datas[i][5]==task_id and ((i+1)==len(datas) or (datas[i+1][0]>end_time_hour or (datas[i+1][0]==end_time_hour and datas[i+1][1]>=end_time_minute))) and (before_hour<start_time_hour or (before_hour==start_time_hour and before_minute<=start_time_minute)):
                    count=1
                    datas[i][0]=start_time_hour
                    datas[i][1]=start_time_minute
                    datas[i][2]=end_time_hour
                    datas[i][3]=end_time_minute
                    connection.tasks.find_one_and_update({"user_id": ObjectId(current_user["_id"]), "task_number": task_id},{"$set": {"start_time":start_time,"end_time": end_time}})
                    data[current_user["name"]]=datas
                    write_file("time.json",data)
                    break
                before_hour=datas[i][2]
                before_minute=datas[i][3]
            if count==0:
                raise HTTPException(status_code=404,detail="Can't update because another task will taken place in that time !!!")
        return f"{tasks["title"] } task updated successfully !!! "


@route.delete("/delete_task",tags=["Task"])
def delete_task(task_id:int,current_user:dict=Depends(get_current_user)):
    task=connection.tasks.find_one({"user_id":ObjectId(current_user["_id"]),"task_number":task_id})
    if task["status"]==True:
        raise HTTPException(status_code=404,detail=f"{task["title"]} task already completed !!!")
    elif task["percentage"]>0:
        raise HTTPException(status_code=404,detail=f"{task["title"]} task already started !!!")
    data=read_file("time.json")
    datas = data[current_user["name"]]
    for i in range(0, len(datas)):
        if datas[i][5]==task_id:
            datas.pop(i)
            break
    data[current_user["name"]]=datas
    write_file("time.json",data)
    connection.tasks.find_one_and_delete({"user_id":ObjectId(current_user["_id"]),"task_number":task_id})
    return f"{task["title"]} task deleted !!!"

@route.post("/change_intervals",tags=["Task"])
def get_intervals_priority(start_time_hour:int,start_time_minute:int,end_time_hour:int,end_time_minute:int,current_user:dict=Depends(get_current_user)):
    intervals=get_intervals(start_time_hour,start_time_minute,end_time_hour,end_time_minute,current_user["name"])
    show=[]
    for i in intervals:
        show.append({"task number":i[5],"start time":f"{i[0]}:{i[1]}","end time":f"{i[2]}:{i[3]}","priority":i[4]})
    return show







