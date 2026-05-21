from fastapi import APIRouter, Depends
from dependencies import get_current_user
from database import supabase

router = APIRouter()

@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    user_badges = supabase.table("user_badges") \
        .select("*, badges(*)") \
        .eq("user_id", user["id"]).execute()
    return {
        "user": user,
        "badges": [ub["badges"] for ub in user_badges.data if ub.get("badges")]
    }