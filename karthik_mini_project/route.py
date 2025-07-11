from bson import ObjectId
from fastapi import APIRouter,Depends,HTTPException
import project.models as models,project.schemas as schemas
from project.database import connection
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
        data[user.name]={}
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
    connection.reload_account.insert_one(is_user)
    tasks=connection.tasks.find({"user_id":ObjectId(is_user["_id"])})
    for i in tasks:
        connection.reload_tasks.insert_one(i)
    connection.tasks.delete_many({"user_id":ObjectId(is_user["_id"])})
    connection.account.find_one_and_delete({"name":user.name})
    reload_data=read_file("reload_account.json")
    data=read_file("time.json")
    reload_data[user.name]=[]
    reload_data[user.name].append(data[user.name])
    data.pop(user.name)
    write_file("time.json",data)
    data=read_file("priority.json")
    reload_data[user.name].append(data[user.name])
    data.pop(user.name)
    write_file("priority.json",data)
    write_file("reload_account.json",reload_data)
    return f"{user.name} account deleted !!!"

@route.post("/reload_account")
def reload_account(user:models.Account):
    is_user = connection.reload_account.find_one({"name": user.name})
    if not is_user or not pwd.verify(user.password, is_user["password"]):
        raise HTTPException(status_code=404, detail="Incorrect Username or Password !!!")
    connection.account.insert_one(is_user)
    connection.reload_account.find_one_and_delete({"name":user.name})
    tasks=connection.reload_tasks.find({"user_id":ObjectId(is_user["_id"])})
    for i in tasks:
        connection.tasks.insert_one(i)
    connection.reload_tasks.delete_many({"user_id":ObjectId(is_user["_id"])})
    reload_data=read_file("reload_account.json")
    data_1=read_file("time.json")
    data_2=read_file("priority.json")
    data_1[user.name]=reload_data[user.name][0]
    data_2[user.name]=reload_data[user.name][1]
    reload_data.pop(user.name)
    write_file("reload_account.json",reload_data)
    write_file("time.json",data_1)
    write_file("priority.json",data_2)
    return f"{user.name} account restored successfully !!!"

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

def is_available(data,user,time_list,month,dates,s_t,e_t,priority,count):

    print(data)
    s_t_h, s_t_m = s_t.hour, s_t.minute
    e_t_h, e_t_m = e_t.hour, e_t.minute
    now = datetime.now()
    if now.month==month and now.day==dates:
        if now.hour > s_t_h or (now.hour == s_t_h and now.minute > s_t_m):
            return "not create"
    new_start = timedelta(hours=s_t_h, minutes=s_t_m)
    new_end = timedelta(hours=e_t_h, minutes=e_t_m)
    new_entry = [s_t_h, s_t_m, e_t_h, e_t_m, priority, count,month,dates]
    for entry in time_list:
        existing_start = timedelta(hours=entry[0], minutes=entry[1])
        existing_end = timedelta(hours=entry[2], minutes=entry[3])
        if new_start < existing_end and existing_start < new_end:
            return False
    key=f"{dates}-{month}"
    data[user][key].append(new_entry)
    data[user][key].sort(key=lambda x: (x[0], x[1]))
    write_file("time.json", data)
    return True

def get_intervals(time_list,s_t_h,s_t_m,e_t_h,e_t_m):
    start_input = timedelta(hours=s_t_h, minutes=s_t_m)
    end_input = timedelta(hours=e_t_h, minutes=e_t_m)
    result_indices = []
    for entry in time_list:
        start_entry = timedelta(hours=entry[0], minutes=entry[1])
        end_entry = timedelta(hours=entry[2], minutes=entry[3])
        if start_input < end_entry and start_entry < end_input:
            result_indices.append(entry)
    return result_indices

@route.post("/create_task",tags=["Task"])
def create_task(task:models.Task,dates:int,month:int,start_time_hour:int,start_time_minute:int,end_time_hour:int,end_time_minute:int,current_user:dict=Depends(get_current_user)):
    now=datetime.now()
    if now.month>month or (now.month==month and now.day>dates):
        raise HTTPException(status_code=404,detail="Task cannot be assigned for past time !!!")
    if (now.month==month and now.day==date) and ((start_time_hour>end_time_hour) or (start_time_hour==end_time_hour and start_time_minute>end_time_minute)):
        raise HTTPException(status_code=404,detail="Starting hour is greater than Ending hour !!!")
    count=connection.tasks.find({"user_id":ObjectId(current_user["_id"]),"month":month,"date":dates}).sort("_id",-1).limit(1)
    count=next(count,None)
    start_time=datetime(now.year,month,dates,start_time_hour,start_time_minute)
    end_time=datetime(now.year,month,dates,end_time_hour,end_time_minute)
    if count:
        count1=count["task_number"]+1
    else:
        count1=1
    data=read_file("time.json")
    key=f"{dates}-{month}"
    if key not in data[current_user["name"]].keys():
        data[current_user["name"]][key]=[]
    print(data)
    priority=is_available(data,current_user["name"],data[current_user["name"]][key],month,dates,start_time,end_time,task.priority,count1)
    if priority=="not create":
        raise HTTPException(status_code=404,detail="Task cannot be allocated in the past time !!! ")
    elif priority:
        task_insert={
            "user_id":current_user["_id"],
            "task_number":count1,
            "title":task.title,
            "month":month,
            "date":dates,
            "start_time":start_time,
            "end_time":end_time,
            "status":False,
            "percentage":0,
            "priority":task.priority
        }
        connection.tasks.insert_one(task_insert)
        return f"{task.title} task added !!!"
    else:
        intervals = get_intervals(data[current_user["name"]][key],start_time.hour,start_time.minute, end_time.hour,end_time.minute)
        print(intervals)
        task_count = 0
        for i in intervals:
            if i[4] == "low":
                task_count += 1
            elif i[4] == "high":
                raise HTTPException(status_code=404, detail="Important task taking place in that time !!!")
        if task_count>0:
            datas=read_file("priority.json")
            count=len(datas[current_user["name"]])+1
            datas[current_user["name"]].update({count:[intervals,[intervals[0][5],task.title,start_time.hour,start_time.minute,end_time.hour,end_time.minute,task.priority,month,dates]]})
            write_file("priority.json",datas)
            raise HTTPException(status_code=404,detail=f"{task_count} number of tasks are taking place if you want to replace to the new task given , then change using the id number {count}")


@route.post("/change_time_task",tags=["Task"])
def change_time_task(task_change_id:int,current_user:dict=Depends(get_current_user)):
    data=read_file("priority.json")
    change_data=data[current_user["name"]][str(task_change_id)]
    key=f"{change_data[0][0][7]}-{change_data[0][0][6]}"
    datas=read_file("time.json")
    for i in range(0,len(datas[current_user["name"]][key])):
        if datas[current_user["name"]][key][i][5]==change_data[0][0][5]:
            for j in range(0,len(change_data[0])):
                datas[current_user["name"]][key].pop(i)
                connection.tasks.find_one_and_delete({"user_id":ObjectId(current_user["_id"]),"task_number":change_data[0][j][5]})
            data[current_user["name"]].pop(str(task_change_id))
            if i>=len(datas[current_user["name"]]):
                datas[current_user["name"]][key].append([change_data[1][2],change_data[1][3],change_data[1][4],change_data[1][5],change_data[1][6],change_data[1][0],change_data[1][7],change_data[1][6]])
            else:
                datas[current_user["name"]][key].insert(i,[change_data[1][2],change_data[1][3],change_data[1][4],change_data[1][5],change_data[1][6],change_data[1][0],change_data[1][7],change_data[1][6]])
            now = date.today()
            start_time = datetime(now.year, now.month, now.day, change_data[1][2], change_data[1][3])
            end_time = datetime(now.year, now.month, now.day, change_data[1][4], change_data[1][5])
            task_insert = {
                "user_id": current_user["_id"],
                "task_number": change_data[1][0],
                "title": change_data[1][1],
                "month":change_data[1][7],
                "date":change_data[1][8],
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

@route.get("/get_all_task",tags=["Task"])
def get_all_task(dates:int,month:int,current_user:dict=Depends(get_current_user)):
    tasks=connection.tasks.find({"user_id":ObjectId(current_user["_id"]),"month":month,"date":dates})
    for i in tasks:
        get_percentage_task(i,current_user["_id"],i["task_number"])
    tasks=connection.tasks.find({"user_id":ObjectId(current_user["_id"]),"month":month,"date":dates})
    return schemas.get_many(tasks)


@route.get("/get_percentage",tags=["Task"])
def get_percentage(*,dates:str="today",month:str="present_month",task_id:int,current_user:dict=Depends(get_current_user)):
    now=datetime.now()
    dates=now.day if dates=="today" else int(dates)
    month=now.month if month=="present_month" else int(month)
    if now.month<month or (now.month==month and now.day<dates):
        raise HTTPException(status_code=404,detail="Task not yet started !!!")
    task=connection.tasks.find_one({"user_id":ObjectId(current_user["_id"]),"task_number":task_id,"month":month,"date":dates})
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
def update_task(*,dates:str="today",month:str="present_month",task_id:int,start_time_hour:int|None=None,start_time_minute:int|None=None,end_time_hour:int|None=None,end_time_minute:int|None=None,current_user:dict=Depends(get_current_user)):
    now = datetime.now()
    dates = now.day if dates == "today" else int(dates)
    month = now.month if month == "present_month" else int(month)
    tasks=connection.tasks.find_one({"user_id":ObjectId(current_user["_id"]),"task_number":task_id,"month":month,"date":dates})
    if not tasks:
        raise HTTPException(status_code=404, detail=f"Task id {task_id} doesn't exists !!!")
    if now.month < month or (now.month == month and now.day < dates):
        task_details="not started"
    else:
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
            key=f"{dates}-{month}"
            datas=data[current_user["name"]][key]
            for i in range(0,len(datas)):
                if datas[i][5]==task_id and ((i+1)==len(datas) or (datas[i+1][0]>end_time_hour or (datas[i+1][0]==end_time_hour and datas[i+1][1]>=end_time_minute))) and (before_hour<start_time_hour or (before_hour==start_time_hour and before_minute<=start_time_minute)):
                    count=1
                    datas[i][0]=start_time_hour
                    datas[i][1]=start_time_minute
                    datas[i][2]=end_time_hour
                    datas[i][3]=end_time_minute
                    connection.tasks.find_one_and_update({"user_id": ObjectId(current_user["_id"]), "task_number": task_id,"month":month,"date":dates},{"$set": {"start_time":start_time,"end_time": end_time}})
                    data[current_user["name"]][key]=datas
                    write_file("time.json",data)
                    break
                before_hour=datas[i][2]
                before_minute=datas[i][3]
            if count==0:
                raise HTTPException(status_code=404,detail="Can't update because another task will taken place in that time !!!")
        return f"{tasks["title"] } task updated successfully !!! "


@route.delete("/delete_task",tags=["Task"])
def delete_task(*,dates:str="today",month:str="present_month",task_id:int,current_user:dict=Depends(get_current_user)):
    now = datetime.now()
    dates = now.day if dates == "today" else int(dates)
    month = now.month if month == "present_month" else int(month)
    task = connection.tasks.find_one({"user_id": ObjectId(current_user["_id"]), "task_number": task_id, "month": month, "date": dates})
    if task["status"]==True:
        raise HTTPException(status_code=404,detail=f"{task["title"]} task already completed !!!")
    elif task["percentage"]>0:
        raise HTTPException(status_code=404,detail=f"{task["title"]} task already started !!!")
    data=read_file("time.json")
    key=f"{dates}-{month}"
    datas = data[current_user["name"]][key]
    for i in range(0, len(datas)):
        if datas[i][5]==task_id:
            datas.pop(i)
            break
    data[current_user["name"]][key]=datas
    write_file("time.json",data)
    connection.reload_tasks.insert_one(task)
    connection.tasks.find_one_and_delete({"user_id":ObjectId(current_user["_id"]),"task_number":task_id,"month":month,"date":dates})
    return f"{task["title"]} task deleted !!!"


@route.post("/reload_task",tags=["task"])
def reload_task(task_id:int,current_user:dict=Depends(get_current_user)):
    task=connection.reload_tasks.find_one({"user_id":ObjectId(current_user["_id"]),"task_number":task_id})
    if not task:
        raise HTTPException(status_code=404,detail=f"No task exists with the given id {task_id}")
    data=read_file("time.json")
    key=f"{task["date"]}-{task["month"]}"
    intervals=get_intervals(data[current_user["name"]][key],task["start_time"].hour,task["start_time"].minute,task["end_time"].hour,task["end_time"].minute)
    if not intervals:
        add=connection.tasks.find_one({"user_id":ObjectId(current_user["_id"]),"task_number":task["task_number"],"month":task["month"],"date":task["date"]})
        if not add:
            connection.tasks.insert_one(task)
            add_list=[task["start_time"].hour,task["start_time"].minute,task["end_time"].hour,task["end_time"].minute,task["priority"],task["task_number"],task["month"],task["date"]]
            data[current_user["name"]][key].append(add_list)
            data[current_user["name"]][key].sort(key=lambda x: (x[0], x[1]))
            write_file("time.json", data)
            connection.reload_tasks.delete_one({"user_id": ObjectId(current_user["_id"]), "task_number": task_id})
            return "task restored successfully !!!"
        else:
            count = connection.tasks.find({"user_id": ObjectId(current_user["_id"]),"month":task["month"],"date":task["date"]}).sort("_id", -1).limit(1)
            count = next(count, None)
            task["task_number"]=count["task_number"]+1
            add_list = [task["start_time"].hour, task["start_time"].minute, task["end_time"].hour,task["end_time"].minute, task["priority"], count["task_number"]+1,task["month"], task["date"]]
            data[current_user["name"]][key].append(add_list)
            data[current_user["name"]][key].sort(key=lambda x: (x[0], x[1]))
            write_file("time.json", data)
            connection.tasks.insert_one(task)
            connection.reload_tasks.delete_one({"user_id": ObjectId(current_user["_id"]), "task_number": task_id})
            return f"task restored successfully but the task number changed to {count["task_number"]+1}"
    connection.reload_tasks.delete_one({"_id": ObjectId(current_user["_id"]), "task_number": task_id})
    return f"Can't able to restored because another task is allocated !!!"


@route.post("/change_intervals",tags=["Task"])
def get_intervals_priority(*,dates:str="today",month:str="present_month",start_time_hour:int,start_time_minute:int,end_time_hour:int,end_time_minute:int,current_user:dict=Depends(get_current_user)):
    now = datetime.now()
    dates = now.day if dates == "today" else int(dates)
    month = now.month if month == "present_month" else int(month)
    data=read_file("time.json")
    key=f"{dates}-{month}"
    time_list=data[current_user["name"]][key]
    intervals=get_intervals(time_list,start_time_hour,start_time_minute,end_time_hour,end_time_minute)
    show=[]
    for i in intervals:
        show.append({"task number":i[5],"start time":f"{i[0]}:{i[1]}","end time":f"{i[2]}:{i[3]}","priority":i[4]})
    return show







