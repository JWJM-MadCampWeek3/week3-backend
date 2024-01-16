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

# FastAPI app and APIRouter initialization
timer = APIRouter(prefix="/timer")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB client initialization
CLIENT = os.environ.get("CLIENT")
print("Connecting to MongoDB with URI:", CLIENT)  # For debugging

client = MongoClient(CLIENT)
db = client['MadCampWeek3']
collection_User = db['User']
collection_Info = db['Info']
collection_Group = db['Group']
collection_Timer = db['Timer']


@timer.get("/duration/{user_id}/{date}")
async def get_duration(user_id: str, date: str):
    # Query the collection for a document with the matching id
    timer_document = collection_Timer.find_one({"id": user_id})
    
    # If the document is not found, return an error response
    if not timer_document:
        raise HTTPException(status_code=404, detail="User not found")

    # Extract the durations array
    durations = timer_document.get("dates", [])
    
    # Find the duration for the given date
    for duration_entry in durations:
        if duration_entry['date'] == date:
            return {"duration": duration_entry['duration']}
    
    # If the date is not found, return an error response
    raise HTTPException(status_code=404, detail="Date not found for this user")


class TimerDataModel(BaseModel):
    date: str
    duration: int

class MemberTimerInfoModel(BaseModel):
    id: str
    total: int
    recent: dict[str, int]  # or a more specific type if you have one
    dates: list[TimerDataModel]

class TimerGroupRequestModel(BaseModel):
    group_name: str
    date: str

class TimerGroupResponseModel(BaseModel):
    members: list[MemberTimerInfoModel]

@timer.post('/group', response_model=TimerGroupResponseModel)
async def get_timer_info_for_group(timer_group_request: TimerGroupRequestModel):
    # Find the group by name
    group_data = collection_Group.find_one({"group_name": timer_group_request.group_name})
    if not group_data:
        raise HTTPException(status_code=Stats.HTTP_404_NOT_FOUND, detail="Group not found")

    # Retrieve member IDs from the group
    member_ids = group_data.get('members', [])

    # Get timer info for each member for the specified date
    member_timer_infos = []
    for member_id in member_ids:
        # Query the timer data for each member and the specified date
        timer_data = collection_Timer.find_one({"id": member_id, "dates.date": timer_group_request.date})
        if timer_data:
            # Extract only the relevant date's data
            dates_info = [date_info for date_info in timer_data.get('dates', []) if date_info['date'] == timer_group_request.date]

            # Handle the recent field
            # If 'recent' is a Timestamp, convert to your preferred format, here is an example converting to a string
            recent = timer_data.get('recent')
            if isinstance(recent, Timestamp):
                # Convert MongoDB Timestamp to Unix timestamp
                recent_dict = {"timestamp": recent.time}
            else:
                recent_dict = {}
  # Assuming 'recent' has a 'timestamp()' method

            # Create the MemberTimerInfoModel object
            member_timer_info = MemberTimerInfoModel(
                id=member_id,
                total=timer_data.get('total', 0),
                recent=recent_dict,
                dates=dates_info
            )
            member_timer_infos.append(member_timer_info)

    return TimerGroupResponseModel(members=member_timer_infos)



# Setup Socket.IO within the timer router
# timer_sio = socketio.AsyncServer(cors_allowed_origins='*')
# timer_socket_app = socketio.ASGIApp(timer_sio)

# # Define Socket.IO event handlers
# @timer_sio.event
# async def connect(sid, environ):
#     print("Client connected", sid)

# @timer_sio.event
# async def disconnect(sid):
#     print("Client disconnected", sid)

# @timer_sio.event
# async def timer_action(sid, data):
#     user_id = data['id']
#     action = data['action']

#     if action == 'start':
#         await collection_Timer.update_one(
#             {"id": user_id},
#             {"$set": {"isStudy": True, "recent": datetime.utcnow()}}
#         )
#         await timer_sio.emit('timer_started', {'id': user_id}, to=sid)

#     elif action == 'stop':
#         timer_data = await collection_Timer.find_one({"id": user_id})
#         if timer_data:
#             previous_recent = timer_data.get("recent", datetime.utcnow())
#         else:
#             previous_recent = datetime.utcnow()

#         # Calculate the time difference
#         time_difference = datetime.utcnow() - previous_recent

#         # Update the user's 'isStudy' status and add the time difference
#         await collection_Timer.update_one(
#             {"id": user_id},
#             {
#                 "$set": {"isStudy": False, "recent": datetime.utcnow()},
#                 "$inc": {"duration": time_difference.total_seconds()}
#             }
#         )
#         await timer_sio.emit('timer_stopped', {'id': user_id}, to=sid)

# # Create WebSocket route for /timer
# @timer.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     while True:
#         data = await websocket.receive_text()
#         await websocket.send_text(f"Message text was: {data}")


# from fastapi import HTTPException

