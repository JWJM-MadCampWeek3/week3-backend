
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

        member_info = await collection_Info.find_one({"id": member_id})
        member_duration["nickname"] = member_info.get("nickname", "Unknown") if member_info else "Unknown"
        member_duration["bj_id"] = member_info.get("bj_id", "Unknown") if member_info else "Unknown"
        member_duration["solvedCount"] = member_info.get("solvedCount", "Unknown") if member_info else "Unknown"
        member_duration["tier"] = member_info.get("tier", "Unknown") if member_info else "Unknown"




        
        durations.append(member_duration)

    # Sort the durations by the duration in descending order
    sorted_durations = sorted(durations, key=lambda x: int(x['duration']), reverse=True)

    # for duration_entry in sorted_durations:
    #     member_info = collection_Info.find_one({"id": duration_entry["id"]})
    #     duration_entry["nickname"] = member_info.get("nickname", "")

    return sorted_durations

class MonthQuery(BaseModel):
    group_name: str
    date: str

class MemberDurationModel(BaseModel):
    id: str
    nickname : str
    bj_id : str
    solvedCount : int
    duration: int
    tier : int


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

        member_duration = {
            "id": member_id, # Initialize duration as 0
        }

        # Initialize the total duration for the member
        total_duration = 0
        nickname = "Unknown" 
        
        # if member_info:
        #     nickname = member_info.get("nickname", "Unknown")
        #     print(nickname)
        # Loop through each entry and sum the durations for the specified month
        for entry in timer_entries:
            for date_entry in entry.get('dates', []):
                # Parse the date in "YYYY-MM-DD" format
                entry_date = date_entry.get('date')
                if entry_date.startswith(query_month):
                    total_duration += int(date_entry.get('duration', 0))
        
        member_duration["duration"] = total_duration
        
        # Append the member's total duration to the list
        member_info = await collection_Info.find_one({"id": member_id})
        member_duration["nickname"] = member_info.get("nickname", "Unknown") if member_info else "Unknown"
        member_duration["bj_id"] = member_info.get("bj_id", "Unknown") if member_info else "Unknown"
        member_duration["solvedCount"] = member_info.get("solvedCount", "Unknown") if member_info else "Unknown"
        member_duration["tier"] = member_info.get("tier", "Unknown") if member_info else "Unknown"



        # member_durations.append({
        #     "id": member_id,
        #     "duration": total_duration,
        #     "nickname" : nickname
        # })
        member_durations.append(member_duration)
    # Sort the member durations by duration in descending order
    sorted_durations = sorted(member_durations, key=lambda x: x['duration'], reverse=True)

    return sorted_durations