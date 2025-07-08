def get_single(item)->dict:
    return {
        "task_number":item["task_number"],
        "title":item["title"],
        "timings":f"{item["start_time"].hour}:{item["start_time"].minute} to {item["end_time"].hour}:{item["end_time"].minute}",
        "status":item["status"],
        "percentage":f"{item["percentage"]}%",
    }

def get_many(items)->list:
    return [get_single(item) for item in items]

def get_user(item):
    return {"name":item["name"]}



