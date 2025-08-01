from fastapi import FastAPI
from project.route import route
import uvicorn

app=FastAPI()
app.include_router(route)


if __name__=="__main__":
    uvicorn.run("main:app",host="127.0.0.1",reload=True)