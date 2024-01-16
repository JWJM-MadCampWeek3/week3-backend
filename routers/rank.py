
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
    query_date = query.date

    # Loop through each member ID and collect their duration
    for member_id in member_ids:
        timer_entries_cursor = collection_Timer.find({"id": member_id, "dates.date": query_date})
        timer_entries = await timer_entries_cursor.to_list(length=100)
        
        print(f"Member ID: {member_id}, Timer Entries: {timer_entries}")

        member_duration = {
            "id": member_id,
            "duration": 0  # Initialize duration as 0
        }

        for entry in timer_entries:
            for date_entry in entry.get('dates', []):
                if date_entry.get('date') == query_date:
                    print(f"Found matching entry for Member ID: {member_id}, Duration: {date_entry.get('duration', 0)}")
                    member_duration["duration"] += int(date_entry.get('duration', 0))

        durations.append(member_duration)

    # Sort the durations by the duration in descending order
    sorted_durations = sorted(durations, key=lambda x: int(x['duration']), reverse=True)

    return sorted_durations

class MonthQuery(BaseModel):
    group_name: str
    date: str

class MemberDurationModel(BaseModel):
    id: str
    duration: int

@rank.post("/individual_month", response_model=list[MemberDurationModel])
async def rank_individual_month(query: MonthQuery):
    # Find the group by group name
    group = await collection_Group.find_one({"group_name": query.group_name})
    if not group:
        raise HTTPException(status_code=404, detail=f"Group '{query.group_name}' not found.")

    # Extract the list of members' IDs from the group
    member_ids = group.get("members", [])

    # Keep the string date as it is for querying (YYYY-MM format)
    query_month = query.date

    # Prepare to collect the total durations for each member
    member_durations = []

    # Loop through each member ID and collect their total duration for the specified month
    for member_id in member_ids:
        timer_entries_cursor = collection_Timer.find({"id": member_id})
        timer_entries = await timer_entries_cursor.to_list(length=100)

        # Initialize the total duration for the member
        total_duration = 0

        # Loop through each entry and sum the durations for the specified month
        for entry in timer_entries:
            for date_entry in entry.get('dates', []):
                # Parse the date in "YYYY-MM-DD" format
                entry_date = date_entry.get('date')
                if entry_date.startswith(query_month):
                    total_duration += int(date_entry.get('duration', 0))

        # Append the member's total duration to the list
        member_durations.append({
            "id": member_id,
            "duration": total_duration
        })

    # Sort the member durations by duration in descending order
    sorted_durations = sorted(member_durations, key=lambda x: x['duration'], reverse=True)

    return sorted_durations