from database import supabase
from datetime import date, timedelta, datetime, timezone

LEVEL_THRESHOLDS = [0, 500, 1200, 2500, 5000]

def calculate_level(total_xp: int) -> int:
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if total_xp >= threshold:
            level = i + 1
    return min(level, 5)

def calculate_streak_bonus(user: dict) -> int:
    last_date = user.get("last_activity_date")
    today = date.today()
    if not last_date:
        return 0
    last = date.fromisoformat(str(last_date))
    if last == today - timedelta(days=1):
        return user["streak"] * 10
    return 0

async def award_xp_and_badges(
    user_id: str,
    challenge_id: str,
    xp_reward: int,
    category: str
) -> dict:
    # 1. Récupérer utilisateur
    user_data = supabase.table("users").select("*").eq("id", user_id).execute()
    user = user_data.data[0]
    today = date.today()

    # 2. Calculer streak
    last_date = user.get("last_activity_date")
    new_streak = user["streak"]
    if last_date:
        last = date.fromisoformat(str(last_date))
        if last == today - timedelta(days=1):
            new_streak += 1
        elif last != today:
            new_streak = 1
    else:
        new_streak = 1

    streak_bonus = calculate_streak_bonus(user)

    # 3. Calculer nouveau XP et niveau
    total_xp_earned = xp_reward + streak_bonus
    new_total_xp = user["total_xp"] + total_xp_earned
    new_level = calculate_level(new_total_xp)
    level_up = new_level > user["level"]

    # 4. Mettre à jour l'utilisateur
    user_update = supabase.table("users").update({
        "total_xp": new_total_xp,
        "level": new_level,
        "streak": new_streak,
        "challenges_completed": user["challenges_completed"] + 1,
        "last_activity_date": today.isoformat()
    }).eq("id", user_id).execute()
    print("=== USER UPDATE ===", user_update.data)

    # 5. Enregistrer la completion
    challenge_update = supabase.table("user_challenges").update({
        "status": "completed",
        "xp_earned": total_xp_earned,
        "completed_at": datetime.now(timezone.utc).isoformat()
    }).eq("user_id", user_id).eq("challenge_id", challenge_id).execute()
    print("=== USER_CHALLENGES UPDATE ===", challenge_update.data)

    # 6. Vérifier les badges
    new_badges = await check_and_award_badges(
        user_id=user_id,
        challenges_completed=user["challenges_completed"] + 1,
        total_xp=new_total_xp,
        streak=new_streak,
        category=category
    )

    return {
        "xp_earned": total_xp_earned,
        "streak_bonus": streak_bonus,
        "new_total_xp": new_total_xp,
        "new_level": new_level,
        "level_up": level_up,
        "new_streak": new_streak,
        "new_badges": new_badges
    }

async def check_and_award_badges(user_id, challenges_completed, total_xp, streak, category) -> list:
    all_badges = supabase.table("badges").select("*").execute().data
    earned_ids = {b["badge_id"] for b in
                  supabase.table("user_badges").select("badge_id").eq("user_id", user_id).execute().data}

    new_badges = []
    for badge in all_badges:
        if badge["id"] in earned_ids:
            continue
        cond = badge.get("condition_value", {})
        ctype = badge.get("condition_type", "")
        earned = False

        if ctype == "challenges_count" and challenges_completed >= cond.get("min", 0):
            earned = True
        elif ctype == "xp" and total_xp >= cond.get("min", 0):
            earned = True
        elif ctype == "streak" and streak >= cond.get("min", 0):
            earned = True

        if earned:
            supabase.table("user_badges").insert({
                "user_id": user_id,
                "badge_id": badge["id"]
            }).execute()
            new_badges.append(badge)

    return new_badges