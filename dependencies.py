from fastapi import HTTPException, Header
from jose import JWTError, jwt
from database import supabase
import os

SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-this")
ALGORITHM = "HS256"

async def get_current_user(authorization: str = Header(...)):
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user_data = supabase.table("users").select("*").eq("id", user_id).execute()
    if not user_data.data:
        raise HTTPException(status_code=404, detail="User not found")

    return user_data.data[0]