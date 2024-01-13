from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from pymongo import MongoClient, ReturnDocument
from passlib.context import CryptContext
import os
from fastapi.middleware.cors import CORSMiddleware 

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

# Endpoints
@app.post('/login', response_model=SuccessModel)
async def login(login_data: LoginModel):
    user = collection_User.find_one({"id": login_data.id})
    if user and pwd_context.verify(login_data.password, user['password']):
        return SuccessModel(success=True, message="Login successful.")
    else:
        return SuccessModel(success=False, message="Incorrect ID or password.")
    

@app.post('/signup_id', response_model=ExistModel)
async def check_id(check_id_data: CheckIdModel):
    exist = collection_User.find_one({"id": check_id_data.id}) is not None
    return ExistModel(exist=exist)

# @app.post('/signup', response_model=SuccessModel)
# async def signup(signup_data: SignupModel):
#     # Check if the user ID already exists
#     if collection_User.find_one({"id": signup_data.id}):
#         return SuccessModel(success=False, message="ID already exists.")

#     # Hash the password
#     hashed_password = pwd_context.hash(signup_data.password)

#     # User data for collection_User
#     user_data = {
#         "id": signup_data.id,
#         "bj_id": signup_data.bj_id,
#         "nickname": signup_data.nickname,
#         "password": hashed_password
#     }

#     # Insert user data into User collection
#     collection_User.insert_one(user_data)

#     # Fetch additional user information from the external API
#     response = requests.get(f'https://solved.ac/api/v3/user/show?handle={signup_data.bj_id}')
#     if response.status_code == 200:
#         additional_user_data = response.json()

#         # Combine the fetched data with bj_id and nickname
#         info_data = {
#             **additional_user_data,
#             "bj_id": signup_data.bj_id,
#             "nickname": signup_data.nickname
#         }

#         # Insert or update the additional user data in Info collection
#         collection_Info.find_one_and_update(
#             {"bj_id": signup_data.bj_id},
#             {"$set": info_data},
#             upsert=True
#         )

#         return SuccessModel(success=True, message="User created successfully and additional info stored.")
#     else:
#         # If the external API call fails
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to fetch additional user data from solved.ac"
#         )

@app.post('/signup', response_model=SuccessModel)
async def signup(signup_data: SignupModel):
    # Check if the user ID already exists
    # if collection_User.find_one({"id": signup_data.id}):
    #     return SuccessModel(success=False, message="ID already exists.")

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
            "bj_id": signup_data.bj_id,
            "nickname": signup_data.nickname
        }

        # Insert or update the additional user data in Info collection
        collection_Info.find_one_and_update(
            {"bj_id": signup_data.bj_id},
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
    


