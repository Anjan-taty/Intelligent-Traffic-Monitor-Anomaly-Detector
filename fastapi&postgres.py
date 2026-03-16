
#For acessing the sql in terminal paste the below code:
#->psql -U <user_name> -d <database_name>

from fastapi import FastAPI,HTTPException
from fastapi.params import Body
from pydantic import BaseModel
from typing import Optional,Annotated
import psycopg2
from psycopg2.extras import RealDictCursor
import time

app=FastAPI()

class Post(BaseModel):
    username:str
    password:str
    age:Optional[int]=None


# Connecting to DataBase

while True:
    try:
        conn=psycopg2.connect(host='localhost',database='logs',user='anjan',password='1234567890',cursor_factory= RealDictCursor)
        cursor=conn.cursor()
        print("Database Connected Successfully")
        break
        
    except Exception as error:
        print("Connection Failed!\nError was:",error)
        time.sleep(2)



@app.get("/")
async def root():
    return {"message": "Hello World"}


#This does not validate with Base Model and 
#->Here the paylaod is an dictionary, so it is acessible by the [] operator
@app.post("/login")
async def get_login_details(payload: Annotated[dict[str,str],Body(...)]):
    print(payload)
    return{"user1":f"name: {payload['name']}  password: {payload['password']}"}



#This validates with base Model if syntax is different or the values are given irrespective of datatype then error is shown and
#->Here the payload is an object, so it is acessible by the . operator
@app.post("/loginpages")
async def login(payload: Post):
    print(payload.username)
    return {"data":payload}

#
#
#
#
# Here we are making the database queries.
#Get users
@app.get("/users")
async def get_users():
    cursor.execute(""" SELECT * FROM credentials """)
    users=cursor.fetchall()
    return{"users":users}


#Post users
@app.post("/newuser")
async def users(post:Post):
    try:
        cursor.execute(""" INSERT INTO credentials(username, password_) VALUES(%s,%s) RETURNING * """,(post.username,post.password))
        new_user=cursor.fetchone()
        conn.commit()
        return {"data":new_user}
    except Exception as error:
        conn.rollback()
        raise HTTPException(status_code=400,detail=str(error))
#Note: RETURNING is only used for updating statements and not for the get statements

#get user by id
@app.get("/users/{id}")
async def get_user_byID(id:int):
    cursor.execute("""SELECT * FROM credentials WHERE id_=%s""",(str(id),)) #Here , is because it expects tuple
    user=cursor.fetchone()
    return{f"data with id{id}":user}