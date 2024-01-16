from datetime import datetime
from typing import List
from typing import Optional, Any, Dict
from fastapi import Body, Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status, websockets , APIRouter
import httpx
from pydantic import BaseModel, Field
from pymongo import MongoClient, ReturnDocument
from passlib.context import CryptContext
import os
from fastapi.middleware.cors import CORSMiddleware 
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from routers.group import group
from routers.timer import timer
from routers.rank import rank
from routers.recommend import recommend
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
app.include_router(rank)
app.include_router(recommend)
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
collection_Problems = db['Problems']

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
@app.get('/test')
async def test_endpoint():
    try:
        # Define the URL of the external API
        url = 'https://solved.ac/api/v3/user/top_100?handle=yongseong97'

        # Make a GET request to the external API
        async with httpx.AsyncClient() as client:
            response = await client.get(url)

        # Check if the response status code is 200 (OK)
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            
            # Extract relevant fields from each item in the 'items' list
            parsed_data = []
            for item in data['items']:
                problem_id = item['problemId']
                title_ko = item['titleKo']
                level = item['level']
                key = item['tags'][0]['key'] if item['tags'] else None
                
                parsed_data.append({
                    'problemId': problem_id,
                    'titleKo': title_ko,
                    'level': level,
                    'key': key
                })
                for item in parsed_data:
                    problem_id = item['problemId']
            
            # Check if a document with the same problemId exists in collection_Problems
                existing_problem = collection_Problems.find_one({'problemId': problem_id})
            
                if not existing_problem:
                # If it doesn't exist, insert the new document
                    collection_Problems.insert_one(item)
                else:
                # If it already exists, update the existing document (optional)
                # You can choose to update or skip duplicates as needed
                # Here, we are updating the 'key' field of the existing document
                    collection_Problems.update_one(
                    {'problemId': problem_id},
                    {'$set': {'key': item['key']}}
                )

            return parsed_data  # Return the parsed data as a list of dictionaries
        else:
            # Raise an HTTPException with the appropriate status code and error message
            raise HTTPException(status_code=response.status_code, detail="External API request failed")

    except httpx.RequestError as e:
        # Handle any network-related errors here
        raise HTTPException(status_code=500, detail="Network error occurred")


# @app.post('/test', response_model=ExistResponseModel)
# async def test(str: TestModel):
#     CLIENT = os.environ.get("CLIENT")
#     print("Connecting to MongoDB with URI:", CLIENT) 

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
    "nickname" : signup_data.nickname,
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


class StartTimerRequest(BaseModel):
    id: str
    date : str


@app.post("/start")
async def start_timer(request_data: StartTimerRequest):
    user_id = request_data.id
    date = request_data.date

    existing_timer_data = collection_Timer.find_one(
        {"id": user_id, "dates.date": date}
    )
    # Update the isStudy status and recent timestamp
    if not existing_timer_data:
        collection_Timer.update_one(
            {"id": user_id},
            {
                "$addToSet": {
            "dates": {
            "date": date,
            "duration": 0
            }
            },
                "$set": {
                "isStudy": True,
                "recent": datetime.utcnow()
            }
        },
        upsert=True
        )

        # If the date already exists, just update 'isStudy' and 'recent'
    else:
        collection_Timer.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "isStudy": True,
                        "recent": datetime.utcnow()
                    }
                }
            )

    # Check if the update was successful
    updated_timer_data = collection_Timer.find_one(
    {"id": user_id, "dates.date": date},
    {"dates.$": 1}
    )

    if not updated_timer_data or "dates" not in updated_timer_data or len(updated_timer_data["dates"]) == 0:
        raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No duration found for user ID {user_id} on date {date}."
    )

# Extract the duration for the response
    duration = updated_timer_data["dates"][0]["duration"]

    return {"duration": duration}


class StopTimerRequest(BaseModel):
    id: str
    date: str  # Assuming you want to use this date to

@app.post("/stop")
async def stop_timer(request_data: StopTimerRequest):
    user_id = request_data.id
    date = request_data.date

    
    # Retrieve the current timer data
    timer_data = collection_Timer.find_one(
        {"id": user_id, "dates.date": date}
    )

    if not timer_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No timer found for user ID {user_id}."
        )

    # Find the index of the date entry to update
    date_entry_index = next(
        (index for (index, d) in enumerate
    (timer_data["dates"]) if d["date"] == date), None)

    # If there's no matching date entry, raise an exception
    if date_entry_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No duration entry found for user ID {user_id} on date {date}."
        )

    # Calculate the time difference
    previous_recent = timer_data["recent"] if "recent" in timer_data else datetime.utcnow()
    time_difference = datetime.utcnow() - previous_recent

    # Update the user's 'isStudy' status, the 'recent' timestamp, and increment the duration
    update_result = collection_Timer.update_one(
        {"id": user_id},
        {
            "$set": {
                f"dates.{date_entry_index}.duration": int(timer_data["dates"][date_entry_index]["duration"]) + int(time_difference.total_seconds()),
                "isStudy": False,
                "recent": datetime.utcnow()
            }
        }
    )

    # Check if the update was successful
    if update_result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed to update timer for user ID {user_id}."
        )
    
    # Return the updated duration
    updated_duration = timer_data["dates"][date_entry_index]["duration"] + int(time_difference.total_seconds())
    return {"id": user_id, "date": date, "duration": updated_duration}

class Problem(BaseModel):
    id: str
    problem: str


@app.post("/user/problem/insert")
async def add_problem_to_user(problem: Problem):
    user_id = problem.id
    user_problem = problem.problem

    # Check if the user exists in the collection.
    user = collection_Info.find_one({"id": user_id})
    if user:
        # Check if the problem already exists for the user.
        if user_problem not in user.get('problems', []):
            collection_Info.update_one({"id": user_id}, {"$push": {"problems": user_problem}})
            return {"message": "Problem added to the user."}
        else:
            raise HTTPException(status_code=400, detail="Problem already exists for the user.")
    else:
        # If the user does not exist, create a new entry.
        await collection_Info.insert_one({"id": user_id, "problems": [user_problem]})
        return {"message": "User created and problem added."}
    
@app.delete("/user/problem/delete")
async def delete_problem_from_user(problem_data: Problem):
    user_id = problem_data.id
    problem_to_delete = problem_data.problem

    # Check if the user exists in the collection.
    user = collection_Info.find_one({"id": user_id})
    if user:
        # Check if the problem exists in the user's problems.
        if problem_to_delete in user.get('problems', []):
            collection_Info.update_one({"id": user_id}, {"$pull": {"problems": problem_to_delete}})
            return {"message": "Problem deleted from the user."}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Problem not found in the user.")
    else:
        # If the user does not exist, raise an error.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
