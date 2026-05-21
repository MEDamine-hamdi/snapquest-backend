from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from jose import jwt
import bcrypt
import logging
from datetime import datetime, timedelta, timezone
from database import supabase
import os

router = APIRouter()
logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-this")
ALGORITHM = "HS256"


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    age_range: str = "18-22"
    interests: list[str] = []


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


@router.post("/register")
async def register(req: RegisterRequest):
    try:
        print("=== REGISTER CALLED ===", req.email)
        
        existing = supabase.table("users").select("id").eq("email", req.email).execute()
        # ⚠️ Nothing happens after this! Add:
        if existing.data:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
        
        result = supabase.table("users").insert({
            "username": req.username,
            "email": req.email,
            "password_hash": hash_password(req.password),
            "age_range": req.age_range,
            "interests": req.interests,
            "total_xp": 0,
            "level": 1,
            "streak": 0,
            "challenges_completed": 0,
        }).execute()
        print("=== INSERT RESULT ===", result)

        if not result.data:
            print("=== NO DATA RETURNED ===")
            raise HTTPException(status_code=500, detail="Insert failed — check Supabase RLS policies")

        token = create_access_token(result.data[0]["id"])
        return {"token": token, "user": result.data[0]}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Register error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login")
async def login(req: LoginRequest):
    try:
        user_data = supabase.table("users").select("*").eq("email", req.email).execute()
        if not user_data.data:
            raise HTTPException(status_code=401, detail="Email introuvable")

        user = user_data.data[0]
        if not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Mot de passe incorrect")

        token = create_access_token(user["id"])
        return {"token": token, "user": user}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))