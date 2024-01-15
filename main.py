from typing import List
from typing import Optional, Any, Dict
from fastapi import Body, FastAPI, HTTPException, Request, Response, status, websockets , APIRouter
from pydantic import BaseModel, Field
from pymongo import MongoClient, ReturnDocument
from passlib.context import CryptContext
import os
from fastapi.middleware.cors import CORSMiddleware 
from bson import ObjectId
from fastapi.encoders import jsonable_encoder

import requests

app = FastAPI()


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

# Endpoint to get and return group information
@app.post('/group_member', response_model=GroupResponseModel)
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

@app.post('/group/join', response_model=GroupModel)
async def join_group(data: GroupActionModel):
    # Find the group by name
    group = collection_Group.find_one({"group_name": data.group_name})
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    # Find the user info and check if they are already in the group
    user_info = collection_Info.find_one({"id": data.id})
    if not user_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User info not found")
    
    # If the user is not already in the group, add them
    if data.group_name not in user_info.get('group', []):
        collection_Info.update_one({"id": data.id}, {"$addToSet": {"group": data.group_name}})
    if data.id not in group.get('members', []):
        collection_Group.update_one(
            {"group_name": data.group_name},
            {"$addToSet": {"members": data.id}}
        )
        return await get_full_group_info(data.group_name) # Return full group info after joining
    else:
# User is already a member of the group, so just return the group info
        return await get_full_group_info(data.group_name)

@app.delete('/group/leave', response_model=GroupModel)
async def leave_group(data: GroupActionModel):
# Find the group by name
    group = collection_Group.find_one({"group_name": data.group_name})
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    user_info = collection_Info.find_one({"id": data.id})
    if not user_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User info not found")

# If the user is in the group, remove them
    if data.group_name in user_info.get('group', []):
        collection_Info.update_one({"id": data.id}, {"$pull": {"group": data.group_name}})
    if data.id in group.get('members', []):
        collection_Group.update_one(
        {"group_name": data.group_name},
        {"$pull": {"members": data.id}}
    )
        return await get_full_group_info(data.group_name)  # Return full group info after leaving
    else:
    # User is not a member of the group, so raise an error
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not in the group")

class GroupCreateModel(BaseModel):
    group_name: str
    manager_id: str
    goal_time: int
    goal_number: int
    tier: int
    is_secret: bool
    password: str
    group_bio: str

@app.post('/group/create', response_model=SuccessModel)
async def create_group(group_data: GroupCreateModel):
    # Check if a group with the same name already exists
    if collection_Group.find_one({"group_name": group_data.group_name}):
        return SuccessModel(success=False, message="Group name already exists.")

    # Hash the group password
    hashed_password = pwd_context.hash(group_data.password)

    # Prepare the new group data
    new_group = {
        "group_name": group_data.group_name,
        "manager_id": group_data.manager_id,
        "goal_time": group_data.goal_time,
        "goal_number": group_data.goal_number,
        "tier": group_data.tier,
        "is_secret": group_data.is_secret,
        "password": hashed_password,
        "group_bio": group_data.group_bio,
        "members": [group_data.manager_id]  # Initialize with an empty list of members
    }

    # Insert the new group into the Group collection
    collection_Group.insert_one(new_group)
    collection_Info.update_one(
        {"id": group_data.manager_id},
        {"$addToSet": {"group": group_data.group_name}}
    )
    
    # Check if the update was successful
    manager_info = collection_Info.find_one({"id": group_data.manager_id})
    if group_data.group_name in manager_info.get("group", []):
        return SuccessModel(success=True, message="New group created successfully and manager updated.")
    else:
        return SuccessModel(success=False, message="Group created but manager update failed.")
    

class GroupUpdateModel(BaseModel):
    group_name: str
    goal_time: int
    goal_number: int
    is_secret: bool
    password: str
    group_bio: str

# Endpoint to update group information
@app.post('/group/update', response_model=SuccessModel)
async def update_group(group_update_data: GroupUpdateModel):
    # Find the group by group_name
    group = collection_Group.find_one({"group_name": group_update_data.group_name})
    if not group:
        return SuccessModel(success=False, message="Group not found.")

    # Hash the password if it's not empty
    hashed_password = pwd_context.hash(group_update_data.password) if group_update_data.password else group.get('password')

    # Prepare the updated group data
    update_data = {
        "goal_time": group_update_data.goal_time,
        "goal_number": group_update_data.goal_number,
        "is_secret": group_update_data.is_secret,
        "password": hashed_password,
        "group_bio": group_update_data.group_bio
    }
        
    result = collection_Group.update_one(
    {"group_name": group_update_data.group_name},
    {"$set": update_data}
    )

    if result.matched_count == 1:
        if result.modified_count == 0:
            message = "No changes were made to the group."
        else:
            message = "Group updated successfully."
        return SuccessModel(success=True, message=message)
    else:
        return SuccessModel(success=False, message="Update failed.")
    
@app.post('/group_info', response_model=GroupModel)
async def get_group_info(group_name: str = Body(..., embed=True)):
    group_document = collection_Group.find_one({"group_name": group_name})
    if group_document:
        group_document.pop('_id')  # Remove the MongoDB generated ID
        group_document.pop('password', None)  # Do not return the password
        return GroupModel(**group_document)
    else:
        raise HTTPException(status_code=404, detail="Group not found")