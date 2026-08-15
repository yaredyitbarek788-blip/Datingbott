"""
Bot Handlers - Database State Based for Serverless
"""
import os
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, Bot
)
import api.db as db

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@Dating_like_community")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/Dating_like_community")

logger = logging.getLogger(__name__)

def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["Browse Profiles", "My Likes"],
        ["My Matches", "My Profile"],
        ["Edit Profile", "Filters"],
        ["Help"]
    ], resize_keyboard=True)

def browse_keyboard():
    return ReplyKeyboardMarkup([
        ["Like", "Skip"],
        ["Next Profile", "Block"],
        ["Back to Menu"]
    ], resize_keyboard=True)

def gender_keyboard():
    return ReplyKeyboardMarkup([["Male", "Female"], ["Other"]], resize_keyboard=True)

def edit_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["Edit Name", "Edit Age"],
        ["Edit Gender", "Edit Country"],
        ["Edit City", "Edit Bio"],
        ["Edit Photo 1", "Edit Photo 2"],
        ["Back to Menu"]
    ], resize_keyboard=True)

def filter_gender_keyboard():
    return ReplyKeyboardMarkup([["Any", "Male"], ["Female", "Other"]], resize_keyboard=True)

def yes_no_keyboard():
    return ReplyKeyboardMarkup([["Yes", "No"]], resize_keyboard=True)

# ===== DISPATCHER =====

async def dispatch_update(update: Update, bot: Bot):
    try:
        if update.callback_query:
            await handle_callback(update, bot)
        elif update.message:
            await handle_message(update, bot)
    except Exception as e:
        logger.error(f"Error: {e}")
        if update.effective_message:
            try:
                await update.effective_message.reply_text("An error occurred. Please try /start")
            except:
                pass

async def handle_callback(update: Update, bot: Bot):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "verify_channel":
        await verify_channel(update, bot)
    elif data.startswith("likeback_"):
        await handle_like_back(update, bot)

async def handle_message(update: Update, bot: Bot):
    user_id = update.effective_user.id
    text = update.message.text or ""
    state_data = await db.get_user_state(user_id)
    state = state_data.get("state", "")

    if text.startswith("/start"):
        await cmd_start(update, bot)
        return
    elif text.startswith("/stats"):
        await cmd_stats(update, bot)
        return
    elif text.startswith("/broadcast "):
        await cmd_broadcast(update, bot)
        return

    if state == "register_name": await register_name(update, bot)
    elif state == "register_age": await register_age(update, bot)
    elif state == "register_gender": await register_gender(update, bot)
    elif state == "register_country": await register_country(update, bot)
    elif state == "register_city": await register_city(update, bot)
    elif state == "register_bio": await register_bio(update, bot)
    elif state == "register_photo1": await register_photo1(update, bot)
    elif state == "register_photo2": await register_photo2(update, bot)
    elif state == "edit_name": await edit_name(update, bot)
    elif state == "edit_age": await edit_age(update, bot)
    elif state == "edit_gender": await edit_gender(update, bot)
    elif state == "edit_country": await edit_country(update, bot)
    elif state == "edit_city": await edit_city(update, bot)
    elif state == "edit_bio": await edit_bio(update, bot)
    elif state == "edit_photo1": await edit_photo1(update, bot)
    elif state == "edit_photo2": await edit_photo2(update, bot)
    elif state == "filter_age_min": await filter_age_min(update, bot)
    elif state == "filter_age_min_input": await filter_age_max(update, bot)
    elif state == "filter_age_max_input": await filter_gender(update, bot)
    elif state == "filter_gender_input": await filter_country(update, bot)
    elif state == "filter_country_input": await filter_city(update, bot)
    elif state == "filter_city_input": await save_filters(update, bot)
    else:
        await handle_menu_buttons(update, bot)

# ===== START / REGISTRATION =====

async def cmd_start(update: Update, bot: Bot):
    user_id = update.effective_user.id
    if await db.is_user_registered(user_id):
        await update.message.reply_text("Welcome back to Dating Bot!\n\nWhat would you like to do?", reply_markup=main_menu_keyboard())
        await db.set_user_state(user_id, "")
        return
    await update.message.reply_text(
        f"Welcome to Dating Like Bot!\n\nTo use this bot, you MUST join our official channel first:\n\n{CHANNEL_LINK}\n\nAfter joining, click the button below to verify:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("I have Joined the Channel", callback_data="verify_channel")]])
    )
    await db.set_user_state(user_id, "awaiting_channel")

async def verify_channel(update: Update, bot: Bot):
    query = update.callback_query
    user_id = query.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        is_member = member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Channel check error: {e}")
        is_member = False
    if not is_member:
        await query.edit_message_text(
            f"You have not joined the channel yet!\n\nPlease join first: {CHANNEL_LINK}\n\nThen click I have Joined again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("I have Joined the Channel", callback_data="verify_channel")]])
        )
        return
    await query.edit_message_text("Channel verified! Welcome to Dating Bot!\n\nLet's create your profile.\n\nStep 1: Please enter your name (this will be shown to others):")
    await db.set_user_state(user_id, "register_name")

async def register_name(update: Update, bot: Bot):
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text("Name must be between 2 and 50 characters. Please try again:")
        return
    await db.set_user_temp_data(update.effective_user.id, "name", name)
    await db.set_user_state(update.effective_user.id, "register_age")
    await update.message.reply_text(f"Nice to meet you, {name}!\n\nStep 2: Please enter your age (18-100):")

async def register_age(update: Update, bot: Bot):
    try:
        age = int(update.message.text.strip())
        if age < 18 or age > 100: raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid age between 18 and 100:")
        return
    await db.set_user_temp_data(update.effective_user.id, "age", age)
    await db.set_user_state(update.effective_user.id, "register_gender")
    await update.message.reply_text("Step 3: Please select your gender:", reply_markup=gender_keyboard())

async def register_gender(update: Update, bot: Bot):
    gender_map = {"Male": "Male", "Female": "Female", "Other": "Other"}
    gender = gender_map.get(update.message.text, "Other")
    await db.set_user_temp_data(update.effective_user.id, "gender", gender)
    await db.set_user_state(update.effective_user.id, "register_country")
    await update.message.reply_text("Step 4: Which country are you from?", reply_markup=ReplyKeyboardRemove())

async def register_country(update: Update, bot: Bot):
    country = update.message.text.strip()
    if len(country) < 2 or len(country) > 50:
        await update.message.reply_text("Please enter a valid country name:")
        return
    await db.set_user_temp_data(update.effective_user.id, "country", country)
    await db.set_user_state(update.effective_user.id, "register_city")
    await update.message.reply_text("Step 5: Which city are you from?")

async def register_city(update: Update, bot: Bot):
    city = update.message.text.strip()
    if len(city) < 2 or len(city) > 50:
        await update.message.reply_text("Please enter a valid city name:")
        return
    await db.set_user_temp_data(update.effective_user.id, "city", city)
    await db.set_user_state(update.effective_user.id, "register_bio")
    await update.message.reply_text("Step 6: Write a short bio about yourself (max 200 characters):\n\nExample: I love traveling, music, and meeting new people!")

async def register_bio(update: Update, bot: Bot):
    bio = update.message.text.strip()
    if len(bio) > 200:
        await update.message.reply_text("Bio is too long! Please keep it under 200 characters. Try again:")
        return
    await db.set_user_temp_data(update.effective_user.id, "bio", bio)
    await db.set_user_state(update.effective_user.id, "register_photo1")
    await update.message.reply_text("Step 7: Please send your FIRST profile photo:")

async def register_photo1(update: Update, bot: Bot):
    if not update.message.photo:
        await update.message.reply_text("Please send a photo, not a file or text. Try again:")
        return
    photo = update.message.photo[-1]
    await db.set_user_temp_data(update.effective_user.id, "photo1_id", photo.file_id)
    await db.set_user_state(update.effective_user.id, "register_photo2")
    await update.message.reply_text("Great! Now please send your SECOND profile photo:")

async def register_photo2(update: Update, bot: Bot):
    if not update.message.photo:
        await update.message.reply_text("Please send a photo, not a file or text. Try again:")
        return
    photo = update.message.photo[-1]
    user_id = update.effective_user.id
    user = update.effective_user
    user_data = {
        "user_id": user_id, "telegram_name": user.first_name or "Unknown",
        "custom_name": await db.get_user_temp_data(user_id, "name"),
        "username": user.username or f"user_{user_id}",
        "age": await db.get_user_temp_data(user_id, "age"),
        "gender": await db.get_user_temp_data(user_id, "gender"),
        "country": await db.get_user_temp_data(user_id, "country"),
        "city": await db.get_user_temp_data(user_id, "city"),
        "bio": await db.get_user_temp_data(user_id, "bio"),
        "photo1_id": await db.get_user_temp_data(user_id, "photo1_id"),
        "photo2_id": photo.file_id, "joined_channel": 1
    }
    await db.create_user(user_data)
    await db.update_user_filters(user_id, {})
    await db.clear_user_temp_data(user_id)
    await db.set_user_state(user_id, "")
    await update.message.reply_text("Profile created successfully!")
    profile_text = f"{user_data['custom_name']}, {user_data['age']}\n{user_data['gender']} | {user_data['country']}, {user_data['city']}\n{user_data['bio']}"
    await update.message.reply_photo(photo=user_data["photo1_id"], caption=profile_text)
    await update.message.reply_photo(photo=user_data["photo2_id"])
    await update.message.reply_text("Registration complete!\n\nYou can now browse profiles and find your match!", reply_markup=main_menu_keyboard())

# ===== BROWSE PROFILES =====

async def browse_profiles(update: Update, bot: Bot):
    user_id = update.effective_user.id
    if not await db.is_user_registered(user_id):
        await update.message.reply_text("You need to register first! Use /start")
        return
    profile = await db.get_random_profile(user_id)
    if not profile:
        await update.message.reply_text("No more profiles available right now!\n\nTry adjusting your filters or check back later.", reply_markup=main_menu_keyboard())
        return
    await db.set_user_temp_data(user_id, "current_profile", profile["user_id"])
    await db.mark_profile_seen(user_id, profile["user_id"], "viewed")
    profile_text = f"{profile['custom_name']}, {profile['age']}\n{profile['gender']} | {profile['country']}, {profile['city']}\n{profile['bio']}"
    await update.message.reply_photo(photo=profile["photo1_id"], caption=profile_text, reply_markup=browse_keyboard())
    if profile.get("photo2_id"):
        await update.message.reply_photo(photo=profile["photo2_id"])

async def handle_like(update: Update, bot: Bot):
    user_id = update.effective_user.id
    liked_user_id = await db.get_user_temp_data(user_id, "current_profile")
    if not liked_user_id:
        await update.message.reply_text("Please browse profiles first!")
        return
    await db.mark_profile_seen(user_id, liked_user_id, "liked")
    await db.add_like(user_id, liked_user_id)
    try:
        await bot.send_message(chat_id=liked_user_id, text="💌 Someone liked your profile!\n\nUse My Likes to see who liked you!")
    except Exception as e:
        logger.error(f"Could not notify liked user: {e}")
    if await db.check_mutual_like(user_id, liked_user_id):
        await db.create_match(user_id, liked_user_id)
        user1 = await db.get_user(user_id)
        user2 = await db.get_user(liked_user_id)
        match_msg = f"❤️ It's a Match!\n\nYou and {user2['custom_name']} liked each other!"
        if user2.get("username"): match_msg += f"\n@{user2['username']}"
        match_msg += "\n\nStart chatting!"
        await update.message.reply_text(match_msg)
        try:
            other_msg = f"❤️ It's a Match!\n\nYou and {user1['custom_name']} liked each other!"
            if user1.get("username"): other_msg += f"\n@{user1['username']}"
            other_msg += "\n\nStart chatting!"
            await bot.send_message(chat_id=liked_user_id, text=other_msg)
        except Exception as e:
            logger.error(f"Could not notify matched user: {e}")
    else:
        await update.message.reply_text("Liked! If they like you back, you will get a match!")

async def handle_like_back(update: Update, bot: Bot):
    query = update.callback_query
    user_id = query.from_user.id
    liked_user_id = int(query.data.split("_")[1])
    await db.add_like(user_id, liked_user_id)
    if await db.check_mutual_like(user_id, liked_user_id):
        await db.create_match(user_id, liked_user_id)
        user1 = await db.get_user(user_id)
        user2 = await db.get_user(liked_user_id)
        match_msg = f"❤️ It's a Match!\n\nYou and {user2['custom_name']} liked each other!"
        if user2.get("username"): match_msg += f"\n@{user2['username']}"
        match_msg += "\n\nStart chatting!"
        await query.edit_message_text(match_msg)
        try:
            other_msg = f"❤️ It's a Match!\n\nYou and {user1['custom_name']} liked each other!"
            if user1.get("username"): other_msg += f"\n@{user1['username']}"
            other_msg += "\n\nStart chatting!"
            await bot.send_message(chat_id=liked_user_id, text=other_msg)
        except Exception as e:
            logger.error(f"Could not notify matched user: {e}")
    else:
        await query.edit_message_text("✅ Liked back! If they like you too, it's a match!")

async def handle_skip(update: Update, bot: Bot):
    user_id = update.effective_user.id
    skipped_id = await db.get_user_temp_data(user_id, "current_profile")
    if skipped_id: await db.mark_profile_seen(user_id, skipped_id, "skipped")
    await db.set_user_temp_data(user_id, "current_profile", None)
    await browse_profiles(update, bot)

async def handle_next(update: Update, bot: Bot):
    user_id = update.effective_user.id
    current_id = await db.get_user_temp_data(user_id, "current_profile")
    if current_id: await db.mark_profile_seen(user_id, current_id, "skipped")
    await db.set_user_temp_data(user_id, "current_profile", None)
    await browse_profiles(update, bot)

async def handle_block(update: Update, bot: Bot):
    user_id = update.effective_user.id
    blocked_id = await db.get_user_temp_data(user_id, "current_profile")
    if blocked_id: await db.block_user(user_id, blocked_id)
    await update.message.reply_text("User blocked. You will not see them again.", reply_markup=main_menu_keyboard())

# ===== MY LIKES / MATCHES / PROFILE =====

async def my_likes(update: Update, bot: Bot):
    user_id = update.effective_user.id
    likes = await db.get_likes_received(user_id)
    if not likes:
        await update.message.reply_text("No one has liked you yet.\n\nDon't worry, keep browsing and someone will like you soon!", reply_markup=main_menu_keyboard())
        return
    shown = 0
    for liker_id in likes:
        if await db.check_mutual_like(liker_id, user_id): continue
        liker = await db.get_user(liker_id)
        if not liker: continue
        profile_text = f"💌 {liker['custom_name']}, {liker['age']}\n{liker['gender']} | {liker['country']}, {liker['city']}\n{liker['bio']}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("❤️ Like Back", callback_data=f"likeback_{liker_id}")]])
        await update.message.reply_photo(photo=liker["photo1_id"], caption=profile_text, reply_markup=keyboard)
        if liker.get("photo2_id"): await update.message.reply_photo(photo=liker["photo2_id"])
        shown += 1
    if shown == 0:
        await update.message.reply_text("No new likes. Check your matches!", reply_markup=main_menu_keyboard())
    else:
        await update.message.reply_text(f"You have {len(likes)} like(s)! Like them back for a match!", reply_markup=main_menu_keyboard())

async def my_matches(update: Update, bot: Bot):
    user_id = update.effective_user.id
    matches = await db.get_matches(user_id)
    if not matches:
        await update.message.reply_text("No matches yet.\n\nKeep browsing and liking profiles. When someone likes you back, it's a match!", reply_markup=main_menu_keyboard())
        return
    text = f"You have {len(matches)} match(es)!\n\n"
    for match_id in matches:
        user = await db.get_user(match_id)
        if user: text += f"{user['custom_name']} - @{user.get('username', 'N/A')}\n"
    text += "\nYou can contact them directly on Telegram!"
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())

async def my_profile(update: Update, bot: Bot):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("Profile not found. Use /start to register.")
        return
    profile_text = f"Your Profile:\n\nName: {user['custom_name']}\nAge: {user['age']}\nGender: {user['gender']}\nCountry: {user['country']}\nCity: {user['city']}\nBio: {user['bio']}\nUsername: @{user.get('username', 'N/A')}\n"
    await update.message.reply_photo(photo=user["photo1_id"], caption=profile_text)
    if user.get("photo2_id"): await update.message.reply_photo(photo=user["photo2_id"])
    await update.message.reply_text("Main Menu:", reply_markup=main_menu_keyboard())

# ===== EDIT PROFILE =====

async def edit_profile_menu(update: Update, bot: Bot):
    await update.message.reply_text("What would you like to edit?", reply_markup=edit_menu_keyboard())
    await db.set_user_state(update.effective_user.id, "edit_menu")

async def edit_name(update: Update, bot: Bot):
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text("Name must be 2-50 characters. Try again:")
        return
    await db.update_user(update.effective_user.id, {"custom_name": name})
    await db.set_user_state(update.effective_user.id, "")
    await update.message.reply_text("Name updated!", reply_markup=edit_menu_keyboard())

async def edit_age(update: Update, bot: Bot):
    try:
        age = int(update.message.text.strip())
        if age < 18 or age > 100: raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid age (18-100):")
        return
    await db.update_user(update.effective_user.id, {"age": age})
    await db.set_user_state(update.effective_user.id, "")
    await update.message.reply_text("Age updated!", reply_markup=edit_menu_keyboard())

async def edit_gender(update: Update, bot: Bot):
    gender_map = {"Male": "Male", "Female": "Female", "Other": "Other"}
    gender = gender_map.get(update.message.text, "Other")
    await db.update_user(update.effective_user.id, {"gender": gender})
    await db.set_user_state(update.effective_user.id, "")
    await update.message.reply_text("Gender updated!", reply_markup=edit_menu_keyboard())

async def edit_country(update: Update, bot: Bot):
    country = update.message.text.strip()
    if len(country) < 2:
        await update.message.reply_text("Please enter a valid country:")
        return
    await db.update_user(update.effective_user.id, {"country": country})
    await db.set_user_state(update.effective_user.id, "")
    await update.message.reply_text("Country updated!", reply_markup=edit_menu_keyboard())

async def edit_city(update: Update, bot: Bot):
    city = update.message.text.strip()
    if len(city) < 2:
        await update.message.reply_text("Please enter a valid city:")
        return
    await db.update_user(update.effective_user.id, {"city": city})
    await db.set_user_state(update.effective_user.id, "")
    await update.message.reply_text("City updated!", reply_markup=edit_menu_keyboard())

async def edit_bio(update: Update, bot: Bot):
    bio = update.message.text.strip()
    if len(bio) > 200:
        await update.message.reply_text("Bio too long! Max 200 chars. Try again:")
        return
    await db.update_user(update.effective_user.id, {"bio": bio})
    await db.set_user_state(update.effective_user.id, "")
    await update.message.reply_text("Bio updated!", reply_markup=edit_menu_keyboard())

async def edit_photo1(update: Update, bot: Bot):
    if not update.message.photo:
        await update.message.reply_text("Please send a photo. Try again:")
        return
    photo = update.message.photo[-1]
    await db.update_user(update.effective_user.id, {"photo1_id": photo.file_id})
    await db.set_user_state(update.effective_user.id, "")
    await update.message.reply_text("Photo 1 updated!", reply_markup=edit_menu_keyboard())

async def edit_photo2(update: Update, bot: Bot):
    if not update.message.photo:
        await update.message.reply_text("Please send a photo. Try again:")
        return
    photo = update.message.photo[-1]
    await db.update_user(update.effective_user.id, {"photo2_id": photo.file_id})
    await db.set_user_state(update.effective_user.id, "")
    await update.message.reply_text("Photo 2 updated!", reply_markup=edit_menu_keyboard())

# ===== FILTERS =====

async def show_filters(update: Update, bot: Bot):
    user_id = update.effective_user.id
    filters = await db.get_user_filters(user_id)
    text = (
        f"Your Current Filters:\n\n"
        f"Min Age: {filters.get('min_age', 18)}\n"
        f"Max Age: {filters.get('max_age', 100)}\n"
        f"Gender: {filters.get('gender_filter', 'Any')}\n"
        f"Country: {filters.get('country_filter', 'Any')}\n"
        f"City: {filters.get('city_filter', 'Any')}\n\n"
        f"Would you like to update your filters?"
    )
    await update.message.reply_text(text, reply_markup=yes_no_keyboard())
    await db.set_user_state(user_id, "filter_age_min")

async def filter_age_min(update: Update, bot: Bot):
    text = update.message.text
    if text == "No":
        await db.set_user_state(update.effective_user.id, "")
        await update.message.reply_text("Filters unchanged.", reply_markup=main_menu_keyboard())
        return
    await update.message.reply_text("Enter minimum age (18-100):", reply_markup=ReplyKeyboardRemove())
    await db.set_user_state(update.effective_user.id, "filter_age_min_input")

async def filter_age_max(update: Update, bot: Bot):
    try:
        min_age = int(update.message.text.strip())
        if min_age < 18 or min_age > 100: raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid age (18-100):")
        return
    await db.set_user_temp_data(update.effective_user.id, "filter_min_age", min_age)
    await update.message.reply_text("Enter maximum age (18-100):")
    await db.set_user_state(update.effective_user.id, "filter_age_max_input")

async def filter_gender(update: Update, bot: Bot):
    try:
        max_age = int(update.message.text.strip())
        if max_age < 18 or max_age > 100: raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid age (18-100):")
        return
    min_age = await db.get_user_temp_data(update.effective_user.id, "filter_min_age", 18)
    if max_age < min_age:
        await update.message.reply_text("Max age must be greater than min age. Try again:")
        return
    await db.set_user_temp_data(update.effective_user.id, "filter_max_age", max_age)
    await update.message.reply_text("Select gender filter:", reply_markup=filter_gender_keyboard())
    await db.set_user_state(update.effective_user.id, "filter_gender_input")

async def filter_country(update: Update, bot: Bot):
    gender = update.message.text
    await db.set_user_temp_data(update.effective_user.id, "filter_gender", gender)
    await update.message.reply_text("Enter country filter (or type 'Any' for all):", reply_markup=ReplyKeyboardRemove())
    await db.set_user_state(update.effective_user.id, "filter_country_input")

async def filter_city(update: Update, bot: Bot):
    country = update.message.text.strip()
    await db.set_user_temp_data(update.effective_user.id, "filter_country", country)
    await update.message.reply_text("Enter city filter (or type 'Any' for all):")
    await db.set_user_state(update.effective_user.id, "filter_city_input")

async def save_filters(update: Update, bot: Bot):
    city = update.message.text.strip()
    user_id = update.effective_user.id
    await db.update_user_filters(user_id, {
        "min_age": await db.get_user_temp_data(user_id, "filter_min_age", 18),
        "max_age": await db.get_user_temp_data(user_id, "filter_max_age", 100),
        "gender_filter": await db.get_user_temp_data(user_id, "filter_gender", "Any"),
        "country_filter": await db.get_user_temp_data(user_id, "filter_country", "Any"),
        "city_filter": city
    })
    await db.clear_user_temp_data(user_id)
    await db.set_user_state(user_id, "")
    await update.message.reply_text("Filters updated successfully!", reply_markup=main_menu_keyboard())

# ===== HELP =====

async def help_command(update: Update, bot: Bot):
    help_text = (
        "Dating Bot Help\n\n"
        "Browse Profiles - See random profiles and like/skip them\n"
        "My Likes - See who liked you (with photos and Like Back button)\n"
        "My Matches - See your mutual matches (reveals usernames!)\n"
        "My Profile - View your own profile\n"
        "Edit Profile - Update your profile info and photos\n"
        "Filters - Set age, gender, country, city filters\n\n"
        "How it works:\n"
        "1. Browse profiles and click Like if you like someone\n"
        "2. If they like you back, it's a MATCH!\n"
        "3. When matched, both usernames are revealed\n"
        "4. You can then contact each other on Telegram\n\n"
        "You can block users you don't want to see\n"
        "Use Filters to find your perfect match!\n\n"
        f"Join our channel: {CHANNEL_LINK}"
    )
    await update.message.reply_text(help_text, reply_markup=main_menu_keyboard())

# ===== ADMIN =====

async def cmd_stats(update: Update, bot: Bot):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("You are not authorized!")
        return
    stats = await db.get_stats()
    text = f"Bot Statistics\n\nTotal Users: {stats['total_users']}\nTotal Likes: {stats['total_likes']}\nTotal Matches: {stats['total_matches']}"
    await update.message.reply_text(text)

async def cmd_broadcast(update: Update, bot: Bot):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("You are not authorized!")
        return
    text = update.message.text
    if not text.startswith("/broadcast "):
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = text[11:]
    user_ids = await db.get_all_user_ids()
    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(chat_id=uid, text=f"Message from Admin:\n\n{message}")
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {uid}: {e}")
    await update.message.reply_text(f"Broadcast sent to {sent} users. Failed: {failed}")

# ===== MENU BUTTONS =====

async def handle_menu_buttons(update: Update, bot: Bot):
    text = update.message.text
    if text == "Browse Profiles":
        await browse_profiles(update, bot)
    elif text == "Like":
        await handle_like(update, bot)
    elif text == "Skip":
        await handle_skip(update, bot)
    elif text == "Next Profile":
        await handle_next(update, bot)
    elif text == "My Likes":
        await my_likes(update, bot)
    elif text == "Block":
        await handle_block(update, bot)
    elif text == "My Matches":
        await my_matches(update, bot)
    elif text == "My Profile":
        await my_profile(update, bot)
    elif text == "Edit Profile":
        await edit_profile_menu(update, bot)
    elif text == "Edit Name":
        await update.message.reply_text("Enter your new name:", reply_markup=ReplyKeyboardRemove())
        await db.set_user_state(update.effective_user.id, "edit_name")
    elif text == "Edit Age":
        await update.message.reply_text("Enter your new age (18-100):", reply_markup=ReplyKeyboardRemove())
        await db.set_user_state(update.effective_user.id, "edit_age")
    elif text == "Edit Gender":
        await update.message.reply_text("Select your gender:", reply_markup=gender_keyboard())
        await db.set_user_state(update.effective_user.id, "edit_gender")
    elif text == "Edit Country":
        await update.message.reply_text("Enter your country:", reply_markup=ReplyKeyboardRemove())
        await db.set_user_state(update.effective_user.id, "edit_country")
    elif text == "Edit City":
        await update.message.reply_text("Enter your city:", reply_markup=ReplyKeyboardRemove())
        await db.set_user_state(update.effective_user.id, "edit_city")
    elif text == "Edit Bio":
        await update.message.reply_text("Enter your new bio (max 200 chars):", reply_markup=ReplyKeyboardRemove())
        await db.set_user_state(update.effective_user.id, "edit_bio")
    elif text == "Edit Photo 1":
        await update.message.reply_text("Send your new FIRST profile photo:", reply_markup=ReplyKeyboardRemove())
        await db.set_user_state(update.effective_user.id, "edit_photo1")
    elif text == "Edit Photo 2":
        await update.message.reply_text("Send your new SECOND profile photo:", reply_markup=ReplyKeyboardRemove())
        await db.set_user_state(update.effective_user.id, "edit_photo2")
    elif text == "Filters":
        await show_filters(update, bot)
    elif text == "Help":
        await help_command(update, bot)
    elif text == "Back to Menu":
        await db.set_user_state(update.effective_user.id, "")
        await update.message.reply_text("Main Menu:", reply_markup=main_menu_keyboard())
    else:
        await update.message.reply_text("I didn't understand that. Please use the menu buttons.", reply_markup=main_menu_keyboard())
