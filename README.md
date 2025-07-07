# Mini-project
# Task Management
## Account:
### Account creation:
* User gives username and password to create account
### Account update:
* User can update the password
### Account delete:
* User gives username and password . If it matches , deletes the account
## Login Account:
### Login:
* User provides username and password. If it matches , the user is authencated
### User information:
* After login ,  user details will be displayed
## Tasks:
### Task creation:
* User can able to create the task
* The required fields are title , priority of the task (low/high) , starting time and ending time
### Task confict and new task added :
* If the newly given task timing is being in the time that used by another task and the newly given task priority is less than the priority of already created task , then we can replace the old task to new task
* If the old task is low and new task is high or low , it can be replaced
* If the old task is high and new task is high or low , it can't be replaced
* The conflict task timings will be stored in "Priority.json" file and id will be created in that , throught that id we can replace the new task
### Get all tasks:
* Display all the tasks
### Get percentage:
* Give the task number of the task , it will display how much percantage it has completed
### Update task:
* User can change the timing of the task , if the task is not started and not completed
### Delete task:
* User can delete the task by providing the task number of the task
### Get tasks by intervals:
* User provide start time and end time , then it will display all the task that was allocated in that intervals

## Requirements:
* Python
* Fast API
* MongoDB
* GUI editor like pycharm
  
