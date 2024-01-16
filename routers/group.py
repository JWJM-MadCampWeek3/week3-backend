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

group = APIRouter(prefix='/group')

import requests
# group.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB client initialization

CLIENT = os.environ.get("CLIENT")

client = MongoClient(CLIENT)
db = client['MadCampWeek3']
collection_User = db['User']
collection_Info = db['Info']
collection_Group = db['Group']

class SuccessModel(BaseModel):
    success: bool
    message: Optional[str] = None

class GroupModel(BaseModel):
    group_name: str
    manager_id: str
    goal_time: int
    goal_number: int
    tier: int
    is_secret: bool
    group_bio: str
    members: List[str]
    problems: Optional[List[str]] = []  # Make 'problems' optional with a default empty list

# Utility function to get the full group info
async def get_full_group_info(group_name: str) -> GroupModel:
    group = collection_Group.find_one({"group_name": group_name})
    if group:
        # Convert ObjectId to string if necessary
        group = jsonable_encoder(group, custom_encoder={ObjectId: str})
        # Check if 'problems' exists, if not, set a default value
        group.setdefault('problems', [])  # This line ensures 'problems' key exists
        return GroupModel(**group)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

class GroupRequestModel(BaseModel):
    group_name: str

class MemberInfoModel(BaseModel):
    id : str
    nickname: str
    bj_id: str
    profileImageUrl: Optional[str] = None 
    solvedCount: int
    rank: int
    rating: int

class GroupResponseModel(BaseModel):
    members: List[MemberInfoModel]


@group.post('/member', tags=['group'], response_model=GroupResponseModel)
async def get_group_info(group_request: GroupRequestModel):
    group_data = collection_Group.find_one({"group_name": group_request.group_name})
    if not group_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    member_infos = []
    for member_id in group_data.get('members', []):
        member_info = collection_Info.find_one({"id": member_id})
        if member_info:
            member_infos.append(
                MemberInfoModel(
                    id=member_id,
                    nickname=member_info['nickname'],
                    bj_id=member_info['bj_id'],
                    profileImageUrl=member_info.get('profileImageUrl'), 
                    solvedCount=member_info.get('solvedCount', 0),  # Ensuring an integer is set
                    rank=member_info.get('rank', 0),  # Ensuring an integer is set
                    rating=member_info.get('rating', 0),  
                )
            )
    
    return GroupResponseModel(members=member_infos)
# @group.post('/member', tags=['group'], response_model=GroupResponseModel)
# async def get_group_info(group_request: GroupRequestModel):
#     group_data = collection_Group.find_one({"group_name": group_request.group_name})
#     if not group_data:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
#     member_ids = group_data.get('members', [])
#     return GroupResponseModel(members=member_ids)




class UserIdModel(BaseModel):
    id: str



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



# Utility function to get the full group info
# async def get_full_group_info(group_name: str) -> GroupModel:
#     group = collection_Group.find_one({"group_name": group_name})
#     if group:
#         # Optionally remove sensitive data before returning
#         # group.pop('password', None)  # Remove password for security reasons
#         return GroupModel(**group)
#     else:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    


@group.post('/join', tags=['group'],response_model=GroupModel)
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

@group.delete('/leave',tags=['group'], response_model=GroupModel)
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

@group.post('/create', tags=['group'],response_model=SuccessModel)
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
        "members": [group_data.manager_id], 
        "problems" : [] # Initialize with an empty list of members
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
@group.post('/update',tags=['group'], response_model=SuccessModel)
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
    
@group.post('/Info', tags=['group'],response_model=GroupModel)
async def get_group_info(group_name: str = Body(..., embed=True)):
    group_document = collection_Group.find_one({"group_name": group_name})
    if group_document:
        group_document.pop('_id')  # Remove the MongoDB generated ID
        group_document.pop('password', None)  # Do not return the password
        return GroupModel(**group_document)
    else:
        raise HTTPException(status_code=404, detail="Group not found")
class GroupProblem(BaseModel):
    group_name: str
    problem: str 

@group.post("/problem/insert")
async def add_problem_to_group(group_problem: GroupProblem):
    group_name = group_problem.group_name
    problem = group_problem.problem

    # Check if the group exists in the collection.
    group = collection_Group.find_one({"group_name": group_name})
    if group:
        # Check if the problem already exists in the group's problems.
        if problem not in group.get('problems', []):
            collection_Group.update_one({"group_name": group_name}, {"$push": {"problems": problem}})
            return {"message": "Problem added to the group."}
        else:
            raise HTTPException(status_code=400, detail="Problem already exists in the group.")
    else:
        # If the group does not exist, raise an error (or you could choose to create it)
        raise HTTPException(status_code=404, detail="Group not found.")
    



@group.delete("/problem/delete")
async def delete_problem_from_group(group_problem: GroupProblem):
    group_name = group_problem.group_name
    problem = group_problem.problem


    # Check if the group exists in the collection.
    group = collection_Group.find_one({"group_name": group_name})
    if group:
        # Check if the problem exists in the group's problems.
        if problem in group.get('problems', []):
            collection_Group.update_one({"group_name": group_name}, {"$pull": {"problems": problem}})
            return {"message": "Problem deleted from the group."}
        else:
            raise HTTPException(status_code=404, detail="Problem not found in the group.")
    else:
        # If the group does not exist, raise an error.
    
        raise HTTPException(status_code=404, detail="Group not found.")
    

@group.get("/list")
async def get_group_list():
    # Query the collection_Group to retrieve all group names
    group_names_cursor = collection_Group.find({}, {"group_name": 1, "_id": 0})

    # Extract the group names from the cursor
    group_names = [group["group_name"] for group in group_names_cursor]

    return {"group_names": group_names}