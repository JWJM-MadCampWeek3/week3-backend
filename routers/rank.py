
from ast import Dict, List
import os
from datetime import datetime
from pstats import Stats
import statistics
from bson import Timestamp
from fastapi import HTTPException, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel
from pymongo import MongoClient
import socketio
from fastapi import FastAPI, WebSocket
from motor.motor_asyncio import AsyncIOMotorClient

# FastAPI app and APIRouter initialization
rank = APIRouter(prefix="/rank")

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




class GroupQuery(BaseModel):
    group_name: str
    date: str


@rank.post("/individual_day")
async def rank_individual_day(query: GroupQuery):
    # Find the group by group name
    group = await collection_Group.find_one({"group_name": query.group_name})
    if not group:
        raise HTTPException(status_code=404, detail=f"Group '{query.group_name}' not found.")

    # Extract the list of members' IDs from the group
    member_ids = group.get("members", [])

    # Prepare to collect the durations for each member
    durations = []

    # Convert the string date to a datetime object for querying
    # try:
    #     query_date = datetime.strptime(query.date, '%Y-%m-%d')
    # except ValueError:
    #     raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format.")
    query_date = query.date
    # Loop through each member ID and collect their duration
    for member_id in member_ids:
        timer_entries_cursor = collection_Timer.find({"id": member_id, "dates.date": query_date})
        timer_entries = await timer_entries_cursor.to_list(length=100)
        
        print(f"Member ID: {member_id}, Timer Entries: {timer_entries}")

        for entry in timer_entries:
            for date_entry in entry.get('dates', []):
                if date_entry.get('date') == query_date:
                    print(f"Found matching entry for Member ID: {member_id}, Duration: {date_entry.get('duration', 0)}")

                    durations.append({
                        "id": member_id,
                        "duration": date_entry.get('duration', 0)
                    })
                    break
    # Sort the durations by the duration in descending order
    sorted_durations = sorted(durations, key=lambda x: int(x['duration']), reverse=True)

    return sorted_durations

