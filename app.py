from pydantic import BaseModel,Field
from fastapi import FastAPI,Depends,HTTPException
from pymongo import MongoClient
import json
import os
from dotenv import load_dotenv
import bcrypt
from fastapi.responses import HTMLResponse,FileResponse
from enum import Enum





load_dotenv()

class Days(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4


uri = os.environ["MONGODB_URI"]
client = MongoClient(uri)

db = client["ceng495test"]
users = db["users"]

users.create_index("username" , unique=True)


app = FastAPI()

# Here I thought that hour should be integer means that:
#0 => 8.40 - 9.30
#1 => 9.40 - 10.30
#2 => 10.40 - 11.30
#3 => 11.40 - 12.30
#4 => 12.40 - 13.30
#5 => 13.40 - 14.30
#6 => 14.40 - 15.30
#7 => 15.40 - 16.30
#8 => 16.40 - 17.30
# duration states how many hours is that lecture so hour 0 and duration 1 means that the lecture is 8.49-9.30 lecture.


class slotforclass(BaseModel):
    id : str = Field(min_length=1 , max_length=20)
    name : str = Field(min_length=1 , max_length=20)
    hour : int = Field(ge = 0 , le=8)
    day : Days
    duration : int = Field(ge = 1 , le = 9)


class Users(BaseModel):
    username : str
    password : str
    



    
@app.get("/")
def anasayfa():
    # cevap = client.admin.command("ping")
    # return cevap
    return FileResponse("./public/index.html")
    

@app.post("/register")
def register(user : Users):
    username = user.username
    password_to_bytes = bytes(user.password , encoding="utf-8")
    salt = bcrypt.gensalt()
    tempuser = users.find_one({"username" : user.username})
    if(tempuser):
        check = bcrypt.checkpw(password_to_bytes , tempuser["password"])
        if(check):
            return {"status" : "Succesfully login." , "classes" : tempuser["classes"]}
        else:
            raise HTTPException(status_code = 401 , detail = "Wrong password")
    hashed_password = bcrypt.hashpw(password_to_bytes , salt)
    users.insert_one({"username" : username , "password" : hashed_password , "classes" : []})
    return {"status" : "Succesfully registered to the system." , "classes" : []} # yeni kullanıcı zaten dersi olmadığı için boş liste dönecek

def get_user(user : Users):
    username = user.username
    password = user.password
    temp = users.find_one({"username" : username})
    if(temp):
        is_valid = bcrypt.checkpw(bytes(password , encoding="utf-8") , temp["password"])
        if(is_valid):
            return temp
        else:
            raise HTTPException(status_code = 401 , detail = "Wrong password!")
        
    raise HTTPException(status_code = 401 , detail = "USER NOT FOUND , please first login to the system.")

def checkslot(user : dict , slot : slotforclass):
    rday = slot.day.value
    rhour = slot.hour
    rduration = slot.duration
    ders_programi = [[0]*9 for i in range(0,5)]
    classes = user["classes"]
    #classes bir list ama dictlerden oluşuyor :
    #[
    #   {
    #     "id": "495",
    #     "name": "Cloud",
    #     "hour": 3,
    #     "day": "TUESDAY"
    #   },
    #   {
    #     "id": "453",
    #     "name": "Cloud Computing",
    #     "hour": 0,
    #     "day": 0,
    #     "duration": 1
    #   },
    #   {
    #     "id": "453",
    #     "name": "Cloud Computing",
    #     "hour": 0,
    #     "day": 0,
    #     "duration": 1
    #   },
    #   {
    #     "id": "453",
    #     "name": "Cloud Computing",
    #     "hour": 0,
    #     "day": 0,
    #     "duration": 1
    #   }
    #]
    for i in range(0 , len(classes)):
        tempdict = classes[i] #bu bir dictionary dönüyor
        day = int(tempdict["day"]) # day bir integer ve monday 0dan başlıyor
        hour = int(tempdict["hour"])
        duration = int(tempdict["duration"])
        for j in range(0,duration):
            ders_programi[day][hour+j] = 1
    for i in range(0 , rduration):
        if(ders_programi[rday][rhour+i] == 1):
            return False

    return True

@app.post("/addclass")
def addclass(slot : slotforclass , user : dict = Depends(get_user)):
    if(slot.duration + slot.hour > 9):
        raise HTTPException(status_code=422 , detail="It doesnt seem possibile to have a class like this :) ")
    is_free = checkslot(user , slot)
    if(is_free):
        users.update_one({"username" : user["username"]} , { "$push" : {"classes" : slot.model_dump(mode='json')}})
        return "Class is succesfully added to the schedule!"
    else:
        raise HTTPException(status_code=409 , detail="Requested slots are not available on the schedule.")

@app.post("/getclasses")
def bring(user : dict = Depends(get_user)):
    temp = (users.find_one({"username" : user["username"]}))["classes"]
    return temp

# def checkifvalid(slot : slotforclass , user : Users):
#     to_check = slot.model_dump(mode='json')
#     classes = users.find_one({"username" : user.username})["classes"] # bu bir liste ama dictionarylerden oluşuyor
#     for i in range(0 , len(classes)):
#         curr_class = classes[i]
#         if(curr_class == to_check):
#             return True
#     return False

@app.post("/deleteclass")
def deleteclass(slot : slotforclass , user : dict = Depends(get_user)):
    boom = users.update_one({"username" : user["username"]} , { "$pull" : {"classes" : slot.model_dump(mode='json')}})
    if(boom.modified_count):
        return "Class is succesfully removed from the schedule."
    raise HTTPException(status_code=404 , detail="Something is wrong.")
    


        
    
