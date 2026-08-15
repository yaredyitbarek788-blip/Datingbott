"""
Supabase Database Layer for Dating Bot
"""
import os
import json
from datetime import datetime
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_supabase = None

def get_supabase():
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

# ===== USERS =====
async def get_user(user_id: int):
    sb = get_supabase()
    res = sb.table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

async def is_user_registered(user_id: int):
    sb = get_supabase()
    res = sb.table("users").select("user_id").eq("user_id", user_id).execute()
    return len(res.data) > 0

async def create_user(user_data: dict):
    sb = get_supabase()
    sb.table("users").insert(user_data).execute()

async def update_user(user_id: int, data: dict):
    sb = get_supabase()
    sb.table("users").update(data).eq("user_id", user_id).execute()

# ===== LIKES =====
async def add_like(from_user: int, to_user: int):
    sb = get_supabase()
    sb.table("likes").upsert({
        "from_user": from_user,
        "to_user": to_user,
        "created_at": datetime.now().isoformat()
    }).execute()

async def check_mutual_like(from_user: int, to_user: int):
    sb = get_supabase()
    res = sb.table("likes").select("*").eq("from_user", to_user).eq("to_user", from_user).execute()
    return len(res.data) > 0

async def get_likes_received(user_id: int):
    sb = get_supabase()
    res = sb.table("likes").select("from_user").eq("to_user", user_id).execute()
    return [row["from_user"] for row in res.data]

# ===== MATCHES =====
async def create_match(user1: int, user2: int):
    sb = get_supabase()
    u1, u2 = sorted([user1, user2])
    sb.table("matches").upsert({
        "user1": u1, "user2": u2,
        "matched_at": datetime.now().isoformat()
    }).execute()

async def get_matches(user_id: int):
    sb = get_supabase()
    res = sb.table("matches").select("*").or_(f"user1.eq.{user_id},user2.eq.{user_id}").execute()
    result = []
    for row in res.data:
        other = row["user2"] if row["user1"] == user_id else row["user1"]
        result.append(other)
    return result

# ===== SEEN =====
async def mark_profile_seen(viewer_id: int, viewed_id: int, action: str = "view"):
    sb = get_supabase()
    sb.table("seen_profiles").upsert({
        "viewer_id": viewer_id, "viewed_id": viewed_id,
        "action": action, "seen_at": datetime.now().isoformat()
    }).execute()

# ===== BLOCKED =====
async def block_user(blocker: int, blocked: int):
    sb = get_supabase()
    sb.table("blocked").upsert({"blocker": blocker, "blocked": blocked}).execute()

# ===== FILTERS =====
async def get_user_filters(user_id: int):
    sb = get_supabase()
    res = sb.table("user_filters").select("*").eq("user_id", user_id).execute()
    if not res.data:
        sb.table("user_filters").insert({
            "user_id": user_id, "min_age": 18, "max_age": 100,
            "gender_filter": "Any", "country_filter": "Any", "city_filter": "Any"
        }).execute()
        res = sb.table("user_filters").select("*").eq("user_id", user_id).execute()
    return res.data[0]

async def update_user_filters(user_id: int, data: dict):
    sb = get_supabase()
    sb.table("user_filters").update(data).eq("user_id", user_id).execute()

# ===== RANDOM PROFILE =====
async def get_random_profile(user_id: int):
    sb = get_supabase()
    filters = await get_user_filters(user_id)
    res = sb.rpc("get_random_profile", {
        "p_viewer_id": user_id,
        "p_min_age": filters.get("min_age", 18),
        "p_max_age": filters.get("max_age", 100),
        "p_gender": filters.get("gender_filter", "Any"),
        "p_country": filters.get("country_filter", "Any"),
        "p_city": filters.get("city_filter", "Any")
    }).execute()
    return res.data[0] if res.data else None

# ===== USER STATE =====
async def get_user_state(user_id: int):
    sb = get_supabase()
    res = sb.table("user_states").select("*").eq("user_id", user_id).execute()
    if not res.data:
        sb.table("user_states").insert({
            "user_id": user_id, "state": "", "temp_data": {}, "updated_at": datetime.now().isoformat()
        }).execute()
        return {"state": "", "temp_data": {}}
    return res.data[0]

async def set_user_state(user_id: int, state: str):
    sb = get_supabase()
    sb.table("user_states").upsert({
        "user_id": user_id, "state": state,
        "updated_at": datetime.now().isoformat()
    }).execute()

async def set_user_temp_data(user_id: int, key: str, value):
    sb = get_supabase()
    res = sb.table("user_states").select("temp_data").eq("user_id", user_id).execute()
    temp = res.data[0]["temp_data"] if res.data else {}
    if isinstance(temp, str):
        temp = json.loads(temp)
    temp[key] = value
    sb.table("user_states").upsert({
        "user_id": user_id, "temp_data": temp,
        "updated_at": datetime.now().isoformat()
    }).execute()

async def get_user_temp_data(user_id: int, key: str, default=None):
    sb = get_supabase()
    res = sb.table("user_states").select("temp_data").eq("user_id", user_id).execute()
    if not res.data:
        return default
    temp = res.data[0]["temp_data"]
    if isinstance(temp, str):
        temp = json.loads(temp)
    return temp.get(key, default)

async def clear_user_temp_data(user_id: int):
    sb = get_supabase()
    sb.table("user_states").upsert({
        "user_id": user_id, "temp_data": {},
        "updated_at": datetime.now().isoformat()
    }).execute()

# ===== ADMIN =====
async def get_stats():
    sb = get_supabase()
    users = sb.table("users").select("*", count="exact").execute()
    likes = sb.table("likes").select("*", count="exact").execute()
    matches = sb.table("matches").select("*", count="exact").execute()
    return {"total_users": users.count, "total_likes": likes.count, "total_matches": matches.count}

async def get_all_user_ids():
    sb = get_supabase()
    res = sb.table("users").select("user_id").execute()
    return [row["user_id"] for row in res.data]
