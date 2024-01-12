import json
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import requests
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define environment variables
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")
CLIENT = os.environ.get("CLIENT")

# Connect to MongoDB
client = MongoClient(CLIENT)
db = client['MadCampWeek2']
collection_User = db['User']
collection_Info = db['Info']


class TokenResponse(BaseModel):
    access_token: str

class UserInfo(BaseModel):
    user_id: str
    nickname: str
    profile_image: str

@app.post("/oauth", response_model=UserInfo)
async def oauth_api(authorization_code: str):
    if not authorization_code:
        raise HTTPException(status_code=400, detail="Authorization code is required")

    token_url = 'https://kauth.kakao.com/oauth/token'
    
    payload = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'code': authorization_code,
    }
    if CLIENT_SECRET:
        payload['client_secret'] = CLIENT_SECRET
    
    try:
        token_response = requests.post(token_url, data=payload)
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get('access_token')

        if not access_token:
            raise HTTPException(status_code=400, detail="Access token not found")

        # Fetch User Information
        user_info_url = 'https://kapi.kakao.com/v2/user/me'
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        user_response = requests.get(user_info_url, headers=headers)
        user_response.raise_for_status()
        user_info = user_response.json()

        user_id_str = str(user_info.get('id'))

        existing_user = collection_User.find_one({"user_id": user_id_str})
        if existing_user:
            # Fetch the user's goal data from collection_Goal
            # user_goals = collection_Goal.find_one({"user_id": user_id_str})
            # if user_goals:
            #     # Remove the '_id' field from the user_goals if it exists
            #     user_goals.pop('_id', None)

            # Extract nickname and profile_image from existing_user
            nickname = existing_user.get('nickname')
            profile_image = existing_user.get('profile_image')

            # Construct the user_data response
            user_data = {
                "user_id": user_id_str,
                "nickname": nickname,
                "profile_image": profile_image,
            }

            return user_data

        else:
            user_nickname = user_info['kakao_account']['profile']['nickname']
            user_profile_image = user_info['kakao_account']['profile']['profile_image_url']

            # Prepare the document to insert into MongoDB
            new_user_document = {
                "user_id": user_id_str,
                "nickname": user_nickname,
                "profile_image": user_profile_image
            }
            
            # Insert User Information into MongoDB
            collection_User.insert_one(new_user_document)
            
            return new_user_document
    
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    
class UpdateUserInfo(BaseModel):
    user_id: str
    bj_id: str
    new_nickname: str


@app.post("/info")
async def update_user_info(update_info: UpdateUserInfo):
    # 사용자 문서를 user_id를 기준으로 찾기
    user_document = collection_User.find_one({"user_id": update_info.user_id})
    
    if user_document:
        # 사용자 문서에 bj_id와 new_nickname 추가/업데이트
        collection_User.update_one(
            {"user_id": update_info.user_id},
            {"$set": {"bj_id": update_info.bj_id, "nickname": update_info.new_nickname}}
        )
        message = "User info updated successfully"
    else:
        # user_id가 데이터베이스에 없다면 에러 반환
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": message}




    