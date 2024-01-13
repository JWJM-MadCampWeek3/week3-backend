from typing import List
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel
from pymongo import MongoClient, ReturnDocument
from passlib.context import CryptContext
import os
from fastapi.middleware.cors import CORSMiddleware 
import httpx

import requests

app = FastAPI()

# origins = [
#     "http://localhost:3000",  # Add the domains you want to allow
#     "http://localhost:8080",  # You can also use '*' to allow all domains
# ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
            
        }

        # Insert or update the additional user data in Info collection
        collection_Info.find_one_and_update(
            {"id": signup_data.id},
            {"$set": info_data},
            upsert=True
        )
        updated_group = collection_Group.find_one_and_update(
        {"group_name": "default"},
        {"$addToSet": {"members": signup_data.nickname}},  # Use $addToSet to add unique value to array
        return_document=ReturnDocument.AFTER
    )

    # Check if the group update was successful
    if updated_group:
        return SuccessModel(success=True, message="User created successfully and added to the default group.")
    else:
        # If the external API call fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch additional user data from solved.ac"
        )
    
@app.post('/login', response_model=SuccessModel)
async def login(login_data: LoginModel):
    user = collection_User.find_one({"id": login_data.id})
    if user and pwd_context.verify(login_data.password, user['password']):
        return SuccessModel(success=True, message="Login successful.")
    else:
        return SuccessModel(success=False, message="Incorrect ID or password.")
    


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

# Endpoint to get and return group information
@app.post('/group', response_model=GroupResponseModel)
async def get_group_info(group_request: GroupRequestModel):
    group_data = collection_Group.find_one({"group_name": group_request.group_name})
    if not group_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    member_infos = []
    for member_nickname in group_data.get('members', []):
        member_info = collection_Info.find_one({"nickname": member_nickname})
        if member_info:
            member_infos.append(
                MemberInfoModel(
                    nickname=member_info['nickname'],
                    bj_id=member_info['bj_id'],
                    profileImageUrl=member_info.get('profileImageUrl', ''),
                    solvedCount=str(member_info.get('solvedCount', 0)),
                    rank=member_info.get('rank', 0),
                    rating=member_info.get('rating', 0),
                )
            )
    
    return GroupResponseModel(members=member_infos)


