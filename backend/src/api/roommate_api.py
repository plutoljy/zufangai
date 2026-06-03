"""
合租匹配 API - MVP 版本
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

router = APIRouter(prefix="/api/roommate", tags=["roommate"])

# ===== 请求/响应模型 =====

class LifestyleHabitsCreate(BaseModel):
    sleep_time: str
    cleanliness: int
    social_level: int
    noise_level: int
    smoking: bool
    pets: bool
    deal_breakers: List[str]

class RoommateRequestCreate(BaseModel):
    title: str
    location: str
    rent_min: int
    rent_max: int
    mode: str  # 'quick' or 'deep'

class ProfileResponse(BaseModel):
    profile_id: str
    lifestyle_habits: Dict[str, Any]
    deal_breakers: List[str]
    pet_personality: Dict[str, Any]

class CandidateResponse(BaseModel):
    id: str
    name: str
    matchScore: int
    avatar: str
    lifestyle: Dict[str, Any]
    dealBreakers: List[str]
    interviewStatus: str

    class Config:
        populate_by_name = True

# ===== 临时内存存储（MVP 用） =====
profiles_db: Dict[str, Dict] = {}
requests_db: Dict[str, Dict] = {}

# ===== API 端点 =====

@router.post("/profile", response_model=ProfileResponse)
async def create_profile(data: LifestyleHabitsCreate):
    """创建宠物画像"""
    profile_id = str(uuid4())

    # 生成简单的宠物人格
    pet_personality = {
        "type": "friendly" if data.social_level >= 3 else "quiet",
        "traits": ["爱干净"] if data.cleanliness >= 4 else ["随和"],
    }

    profile = {
        "profile_id": profile_id,
        "lifestyle_habits": data.dict(),
        "deal_breakers": data.deal_breakers,
        "pet_personality": pet_personality,
        "created_at": datetime.now().isoformat(),
    }

    profiles_db[profile_id] = profile

    return ProfileResponse(**profile)

@router.post("/request")
async def create_request(data: RoommateRequestCreate):
    """发布合租需求"""
    request_id = str(uuid4())

    request = {
        "request_id": request_id,
        "title": data.title,
        "location": data.location,
        "rent_range": {"min": data.rent_min, "max": data.rent_max},
        "mode": data.mode,
        "status": "published",
        "created_at": datetime.now().isoformat(),
    }

    requests_db[request_id] = request

    return {"request_id": request_id, "status": "published"}

@router.get("/candidates")
async def get_candidates():
    """获取候选人列表（模拟数据）"""
    # MVP: 返回模拟数据（使用驼峰命名）
    mock_candidates = [
        {
            "id": "1",
            "name": "小明",
            "matchScore": 85,
            "avatar": "👨",
            "lifestyle": {
                "sleepTime": "正常作息",
                "cleanliness": 4,
                "socialLevel": 3,
            },
            "dealBreakers": [],
            "interviewStatus": "completed",
        },
        {
            "id": "2",
            "name": "小红",
            "matchScore": 65,
            "avatar": "👩",
            "lifestyle": {
                "sleepTime": "夜猫子",
                "cleanliness": 3,
                "socialLevel": 4,
            },
            "dealBreakers": ["吸烟"],
            "interviewStatus": "completed",
        },
        {
            "id": "3",
            "name": "小李",
            "matchScore": 45,
            "avatar": "🧑",
            "lifestyle": {
                "sleepTime": "早睡早起",
                "cleanliness": 2,
                "socialLevel": 5,
            },
            "dealBreakers": ["吸烟", "噪音"],
            "interviewStatus": "completed",
        },
    ]

    return mock_candidates

@router.get("/interview/{candidate_id}")
async def get_interview(candidate_id: str):
    """获取面试对话和匹配结果"""
    # MVP: 返回模拟数据（使用驼峰命名）
    mock_data = {
        "candidateName": "小明",
        "messages": [
            {
                "id": "1",
                "sender": "pet",
                "senderName": "旺财",
                "content": "你好！我是房东的宠物代理。请问你平时几点睡觉呢？",
                "timestamp": "10:00",
                "messageType": "question",
            },
            {
                "id": "2",
                "sender": "user",
                "senderName": "小明",
                "content": "我一般晚上11点左右睡觉，早上7点起床。",
                "timestamp": "10:01",
                "messageType": "answer",
            },
            {
                "id": "3",
                "sender": "pet",
                "senderName": "旺财",
                "content": "了解！那你对室友的清洁习惯有什么要求吗？",
                "timestamp": "10:01",
                "messageType": "question",
            },
            {
                "id": "4",
                "sender": "user",
                "senderName": "小明",
                "content": "我比较爱干净，希望室友也能保持公共区域整洁。",
                "timestamp": "10:02",
                "messageType": "answer",
            },
        ],
        "matchResult": {
            "score": 85,
            "dealBreakers": [
                {
                    "item": "吸烟",
                    "triggered": False,
                    "reason": "候选人不吸烟",
                },
                {
                    "item": "养宠物",
                    "triggered": False,
                    "reason": "候选人不养宠物",
                },
            ],
            "commonGrounds": ["作息规律", "爱干净", "不吸烟"],
            "recommendation": "该候选人与你的生活习惯高度匹配，建议进一步线下沟通。",
        },
    }

    return mock_data

@router.post("/interview/{candidate_id}/interrupt")
async def send_interrupt_message(candidate_id: str, message: dict):
    """房东插入消息"""
    # MVP: 简单验证并返回成功
    # 实际应该存储到数据库
    print(f"[房东插入消息] 候选人ID: {candidate_id}, 消息: {message}")

    # 模拟存储成功
    return {
        "status": "success",
        "message_id": str(uuid4()),
        "timestamp": datetime.now().isoformat()
    }
