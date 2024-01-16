import datetime
from typing import List
from typing import Optional, Any, Dict
from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status, websockets , APIRouter
from pydantic import BaseModel, Field
from pymongo import MongoClient, ReturnDocument
from passlib.context import CryptContext
import os
from fastapi.middleware.cors import CORSMiddleware 
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from routers.group import group
from routers.timer import timer
import requests
import socketio

# sio = socketio.AsyncServer(async_mode='asgi')
app = FastAPI()

# app.mount('/timer', timer_socket_app)
# socket_app = socketio.ASGIApp(sio)


# app.mount('/',socket_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

app.include_router(group)
app.include_router(timer)
# app.include_router(
#     timer,
#     prefix="/timer",
#     tags=["timer"],
#     responses={404: {"description": "Not found"}},
# )
# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB client initialization

CLIENT = os.environ.get("CLIENT")
print("Connecting to MongoDB with URI:", CLIENT)  # Add this line to debug

client = MongoClient(CLIENT)
db = client['MadCampWeek3']
collection_User = db['User']
collection_Info = db['Info']
collection_Group = db['Group']
collection_Timer = db['Timer']


# Models
class LoginModel(BaseModel):
    id: str
    password: str

class SignupModel(BaseModel):
    id: str
    bj_id: str
    nickname: str
    password: str

class CheckIdModel(BaseModel):
    id: str

class SuccessModel(BaseModel):
    success: bool
    message: Optional[str] = None

class ExistModel(BaseModel):
    exist: bool

class BJIDModel(BaseModel):
    bj_id: str

class ExistResponseModel(BaseModel):
    exist: bool

class TestModel(BaseModel):
    test : str

@app.post('/test', response_model=ExistResponseModel)
async def test(str: TestModel):
    CLIENT = os.environ.get("CLIENT")
    print("Connecting to MongoDB with URI:", CLIENT) 

@app.post('/signup_bj_id', response_model=ExistResponseModel)
async def check_bj_id(bj_id_data: BJIDModel):
    response = requests.get(f'https://solved.ac/api/v3/user/show?handle={bj_id_data.bj_id}')
    
    # If the request to the external API is successful and user data is found
    if response.status_code == 200:
        # Depending on the API you're using, you may need to check the content of the response
        # to make sure the user actually exists. For example:
        # user_data = response.json()
        # exist = 'id' in user_data  # or any other key that indicates user existence
        exist = True  # Assuming a 200 OK status means the user exists
    else:
        # If the status code is not 200, we assume the user doesn't exist
        exist = False

    return ExistResponseModel(exist=exist)

@app.post('/signup_id', response_model=ExistModel)
async def check_id(check_id_data: CheckIdModel):
    exist = collection_User.find_one({"id": check_id_data.id}) is not None
    return ExistModel(exist=exist)





@app.post('/signup', response_model=SuccessModel)
async def signup(signup_data: SignupModel):
    # Check if the user ID already exists
    if collection_User.find_one({"id": signup_data.id}):
        return SuccessModel(success=False, message="ID already exists.")

    # Hash the password
    hashed_password = pwd_context.hash(signup_data.password)

    # User data for collection_User
    user_data = {
        "id": signup_data.id,
        "bj_id": signup_data.bj_id,
        "nickname": signup_data.nickname,
        "password": hashed_password
    }

    # Insert user data into User collection
    collection_User.insert_one(user_data)

    timer_data = {
    "id": signup_data.id,
    "isStudy" : False,
    "recent" : None,
    "total" : 0,
    "dates": []  
    }
    collection_Timer.insert_one(timer_data)

    # Fetch additional user information from the external API
    response = requests.get(f'https://solved.ac/api/v3/user/show?handle={signup_data.bj_id}')
    if response.status_code == 200:
        additional_user_data = response.json()

        # Combine the fetched data with bj_id and nickname
        info_data = {
            **additional_user_data,
            "id" : signup_data.id,
            "bj_id": signup_data.bj_id,
            "nickname": signup_data.nickname,
            "group": ["default"],  # Initialize with "default" group
            "problems": [],  # Initialize with an empty list of problems
            "todo_problems": [] 
            
        }

        # Insert or update the additional user data in Info collection
        collection_Info.find_one_and_update(
            {"id": signup_data.id},
            {"$set": info_data},
            upsert=True
        )
        updated_group = collection_Group.find_one_and_update(
        {"group_name": "default"},
        {"$addToSet": {"members": signup_data.id}},  # Use $addToSet to add unique value to array
        return_document=ReturnDocument.AFTER
        )
        if updated_group:
            return SuccessModel(success=True, message="User created successfully and added to the default group.")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update group information"
            )
    else:
        # If the external API call fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch additional user data from solved.ac"
        )
    # Check if the group update was successful
    # if updated_group:
    #     return SuccessModel(success=True, message="User created successfully and added to the default group.")
    # else:
    #     # If the external API call fails
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="Failed to fetch additional user data from solved.ac"
    #     )
    
    
class LoginSuccessModel(SuccessModel):
    userinfo: Optional[Any] = None

    class Config:
        arbitrary_types_allowed = True

@app.post('/login', response_model=LoginSuccessModel)
async def login(login_data: LoginModel):
    user = collection_User.find_one({"id": login_data.id})
    if user and pwd_context.verify(login_data.password, user['password']):
        # Fetch user information from solved.ac API
        response = requests.get(f'https://solved.ac/api/v3/user/show?handle={user.get("bj_id")}')
        if response.status_code == 200:
            additional_user_data = response.json()

            # Prepare the updated info data
            info_data = {
                **additional_user_data
            }

            # Update the additional user data in Info collection
            collection_Info.find_one_and_update(
                {"id": login_data.id},
                {"$set": info_data},
                upsert=True
            )

            # Fetch updated user information from collection_Info
            user_info = collection_Info.find_one({"id": login_data.id})
            if user_info:
                # Optionally remove the MongoDB '_id' field
                user_info.pop('_id', None)
                return LoginSuccessModel(success=True, message="Login successful.", userinfo=user_info)
            else:
                return LoginSuccessModel(success=False, message="User info not found after update.")
        else:
            # If the external API call fails
            return LoginSuccessModel(success=False, message="Failed to fetch additional user data from solved.ac.")
    else:
        return LoginSuccessModel(success=False, message="Incorrect ID or password.")

class GroupRequestModel(BaseModel):
    group_name: str

class MemberInfoModel(BaseModel):
    nickname: str
    bj_id: str
    profileImageUrl: str
    solvedCount: str
    rank: int
    rating: int

class GroupResponseModel(BaseModel):
    members: List[MemberInfoModel]



class UserIdModel(BaseModel):
    id: str

@app.post('/user_Info', response_model=Dict[str, Any])
async def user_info(user_id_data: UserIdModel):
    user_info = collection_Info.find_one({"id": user_id_data.id})
    
    if user_info:
        # Optionally remove the MongoDB '_id' field
        user_info.pop('_id', None)
        return user_info
    else:
        raise HTTPException(status_code=404, detail="User not found")
    

class GroupActionModel(BaseModel):
    id: str
    group_name: str

def convert_objectid_to_string(value):
    if isinstance(value, ObjectId):
        return str(value)
    elif isinstance(value, dict):
        for key in value:
            value[key] = convert_objectid_to_string(value[key])
    elif isinstance(value, list):
        value = [convert_objectid_to_string(item) for item in value]
    return value


class GroupModel(BaseModel):
    group_name: str
    manager_id: str
    goal_time: int
    goal_number: int
    tier: int
    is_secret: bool
    # password: str  # Note: Returning passwords is generally a bad practice
    group_bio: str
    members: List[str]

# Utility function to get the full group info
async def get_full_group_info(group_name: str) -> GroupModel:
    group = collection_Group.find_one({"group_name": group_name})
    if group:
        # Optionally remove sensitive data before returning
        # group.pop('password', None)  # Remove password for security reasons
        return GroupModel(**group)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")


class GroupCreateModel(BaseModel):
    group_name: str
    manager_id: str
    goal_time: int
    goal_number: int
    tier: int
    is_secret: bool
    password: str
    group_bio: str



class GroupUpdateModel(BaseModel):
    group_name: str
    goal_time: int
    goal_number: int
    is_secret: bool
    password: str
    group_bio: str

# WebSocket connection manager
# class ConnectionManager:
#     def __init__(self):
#         self.active_connections = {}

#     async def connect(self, websocket: WebSocket, user_id: str):
#         await websocket.accept()
#         self.active_connections[user_id] = websocket

#     def disconnect(self, user_id: str):
#         if user_id in self.active_connections:
#             del self.active_connections[user_id]

#     async def send_personal_message(self, message: str, user_id: str):
#         if user_id in self.active_connections:
#             websocket = self.active_connections[user_id]
#             await websocket.send_text(message)

# manager = ConnectionManager()

# # WebSocket route for /ws
# @app.websocket("/ws/{user_id}")
# async def websocket_endpoint(websocket: WebSocket, user_id: str):
#     await manager.connect(websocket, user_id)
#     try:
#         while True:
#             data = await websocket.receive_text()
#             action = data['action']
#             # Timer action logic here
#             # Use manager.send_personal_message to communicate back
#     except WebSocketDisconnect:
#         manager.disconnect(user_id)

# # Timer action logic (modified for WebSocket)
# async def timer_action(user_id, action):
#     if action == 'start':
#         # Start timer logic
#         await manager.send_personal_message('Timer started', user_id)
#     elif action == 'stop':
#         # Stop timer logic
#         await manager.send_personal_message('Timer stopped', user_id)



timer_sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode = 'asgi') 
timer_socket_app = socketio.ASGIApp(timer_sio)
app.mount("/socket.io", timer_socket_app)

# Define Socket.IO event handlers
@timer_sio.event
async def connect(sid, environ):
    print("Client connected", sid)

@timer_sio.event
async def disconnect(sid):
    print("Client disconnected", sid)

@timer_sio.event
async def timer_action(sid, data):
    user_id = data['id']
    action = data['action']

    if action == 'start':
        await collection_Timer.update_one(
            {"id": user_id},
            {"$set": {"isStudy": True, "recent": datetime.utcnow()}}
        )
        await timer_sio.emit('timer_started', {'id': user_id}, to=sid)

    elif action == 'stop':
        timer_data = await collection_Timer.find_one({"id": user_id})
        if timer_data:
            previous_recent = timer_data.get("recent", datetime.utcnow())
            existing_duration = timer_data.get("duration", 0)  # Get the existing duration
        else:
            previous_recent = datetime.utcnow()
            existing_duration = 0  # Default to 0 if no timer data found

        # Calculate the time difference
        time_difference = datetime.utcnow() - previous_recent

        # Add the time difference to the existing duration
        new_duration = existing_duration + time_difference.total_seconds()

        # Update the user's 'isStudy' status and duration
        await collection_Timer.update_one(
            {"id": user_id},
            {
                "$set": {
                    "isStudy": False,
                    "recent": datetime.utcnow(),
                    "duration": new_duration  # Update duration with the new calculated value
                }
            }
        )
        await timer_sio.emit('timer_stopped', {'id': user_id}, to=sid)







# Create WebSocket route for /timer
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     while True:
#         data = await websocket.receive_text()
#         await websocket.send_text(f"Message text was: {data}")


