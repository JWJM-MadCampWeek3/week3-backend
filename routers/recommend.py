
from ast import Dict, List
from dataclasses import Field
import os
from datetime import datetime
from pstats import Stats, StatsProfile
import statistics
from typing import Optional
from bson import ObjectId, Timestamp
from fastapi import HTTPException, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel, validator
from pymongo import ASCENDING, MongoClient
import socketio
from fastapi import FastAPI, WebSocket
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# FastAPI app and APIRouter initialization
recommend = APIRouter(prefix="/recommend")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB client initialization
CLIENT = os.environ.get("CLIENT")
print("Connecting to MongoDB with URI:", CLIENT)  # For debugging

client = AsyncIOMotorClient(CLIENT)
db = client['MadCampWeek3']
collection_User = db['User']
collection_Info = db['Info']
collection_Group = db['Group']
collection_Timer = db['Timer']
collection_Problems = db['Problems']


class Problem(BaseModel):
    problemId: int
    titleKo: str
    level: int
    key: str

    # Custom validator to convert ObjectId to string
    # @validator('id', pre=True, allow_reuse=True)
    # def validate_id(cls, value):
    #     if isinstance(value, ObjectId):
    #         return str(value)
    #     return value

class ProblemResponse(BaseModel):
    problems : list[Problem]

class RecommendRequest(BaseModel):
    tier: int
    keys: list[str]

@recommend.post("/list", response_model=ProblemResponse)
async def recommend_list(request: RecommendRequest):
    tier = request.tier
    keys = request.keys
    # Create a filter for tier range and keys
    filter_query = {
        "$and": [
            {"level": {"$gte": tier - 3, "$lte": tier + 3}},
            {"key": {"$in": keys}}
        ]
    }
    # Query the database with the filter, sort by level ascending, limit to 10 results
    cursor = collection_Problems.find(filter_query).limit(10)
    # Convert the cursor to a list
    problems_list = await cursor.to_list(length=10)

    problems = []
    if problems_list:
        for prob in problems_list:
            # Assuming 'prob' is a dictionary returned from MongoDB, we map it to our 'Problem' class
            # We'll use the 'ObjectId' of the document as the 'id' field in 'Problem'
            problem = Problem(
                id=str(prob['_id']),  # Convert ObjectId to string
                problemId=prob['problemId'],
                titleKo=prob['titleKo'],
                level=prob['level'],
                key=prob['key']
            )
            problems.append(problem)
        return ProblemResponse(problems=problems)
    else:
        raise HTTPException(
        status_code=statistics.StatisticsError.HTTP_404_NOT_FOUND,
        detail="No matching problems found."
        )

