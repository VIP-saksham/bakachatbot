# ©️ Copyright Reserved - @truenakshu  Saksham Swaroop

# ============================================
# ©️ 2025 Saksham Swaroop (aka @truenakshu)
# 🔗 GitHub : https://github.com/VIP-saksham/Bakachatbot
# 📢 Telegram Channel : https://t.me/TheHellBots
# ============================================


import html
import re
import asyncio
from datetime import datetime, timedelta
from telegram import Bot, User, Chat
from telegram.constants import ParseMode, ChatType
from telegram.error import TelegramError
from baka.database import users_collection, sudoers_collection, groups_collection
from baka.config import OWNER_ID, SUDO_IDS_STR, LOGGER_ID, BOT_NAME, AUTO_REVIVE_HOURS, AUTO_REVIVE_BONUS

SUDO_USERS = set()

def reload_sudoers():
    """Loads Sudo users from Env and DB."""
    try:
        SUDO_USERS.clear()
        SUDO_USERS.add(OWNER_ID)
        if SUDO_IDS_STR:
            for x in SUDO_IDS_STR.split(","):
                if x.strip().isdigit(): SUDO_USERS.add(int(x.strip()))
        for doc in sudoers_collection.find({}):
            SUDO_USERS.add(doc["user_id"])
    except Exception as e:
        print(f"Sudo Load Error: {e}")

reload_sudoers()

# --- 🌸 AESTHETIC FONT ENGINE ---
def stylize_text(text):
    """Converts normal text to Aesthetic Math Sans Bold."""
    font_map = {
        'A': 'ᴧ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'Є', 'F': 'Ғ', 'G': 'ɢ',
        'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 'K': 'ᴋ', 'L': 'ʟ', 'M': 'ϻ', 'N': 'η',
        'O': 'σ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'Ꝛ', 'S': 's', 'T': 'ᴛ', 'U': 'υ',
        'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ',
        'a': 'ᴧ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'є', 'f': 'ғ', 'g': 'ɢ',
        'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 'k': 'ᴋ', 'l': 'ʟ', 'm': 'ϻ', 'n': 'η',
        'o': 'σ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ꝛ', 's': 's', 't': 'ᴛ', 'u': 'υ',
        'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        '0': '𝟎', '1': '𝟏', '2': '𝟐', '3': '𝟑', '4': '𝟒', 
        '5': '𝟓', '6': '𝟔', '7': '𝟕', '8': '𝟖', '9': '𝟗'
    }

    def apply_style(t):
        return "".join(font_map.get(c, c) for c in t)

    # Skip Mentions, Links, Commands
    pattern = r"(@\w+|https?://\S+|`[^`]+`|/[a-zA-Z0-9_]+)"
    parts = re.split(pattern, str(text))
    result = []
    for part in parts:
        if re.match(pattern, part): result.append(part)
        else: result.append(apply_style(part))

    return "".join(result)

# --- 🌟 ULTIMATE DASHBOARD LOGGER ---
async def log_to_channel(bot: Bot, event_type: str, details: dict):
    if LOGGER_ID == 0: return
    now = datetime.now().strftime("%I:%M:%S %p | %d %b")

    # Headers
    headers = {
        "start": f"🌸 <b>{stylize_text('SYSTEM ONLINE')}</b>",
        "join": f"🥂 <b>{stylize_text('NEW GROUP JOINED')}</b>",
        "leave": f"💔 <b>{stylize_text('LEFT GROUP')}</b>",
        "command": f"👮‍♀️ <b>{stylize_text('ADMIN COMMAND')}</b>",
        "transfer": f"💸 <b>{stylize_text('TRANSACTION')}</b>"
    }
    header = headers.get(event_type, f"📜 <b>{stylize_text('LOG ENTRY')}</b>")

    # Build Message
    text = f"{header}\n━━━━━━━━━━━━━━━━━━\n"

    # User Section
    if 'user' in details:
        # Expecting 'user' to be pre-formatted mention + ID, but we can be flexible
        text += f"👤 <b>{stylize_text('User')}:</b> {details['user']}\n"

    # Chat Section
    if 'chat' in details:
        text += f"🏰 <b>{stylize_text('Chat')}:</b> {html.escape(details['chat'])}\n"

    # Action/Content Section
    if 'action' in details:
        text += f"🎬 <b>{stylize_text('Action')}:</b> {details['action']}\n"

    # Group Link Handling
    if 'link' in details:
        link_val = details['link']
        if link_val and link_val.startswith("http"):
            text += f"🔗 <b>{stylize_text('Invite')}:</b> <a href='{link_val}'>Click to Join</a>\n"
        else:
            text += f"🔒 <b>{stylize_text('Invite')}:</b> <i>Hidden/Private</i>\n"

    # Footer
    text += f"━━━━━━━━━━━━━━━━━━\n⌚ <code>{now}</code>"

    try: 
        await bot.send_message(
            chat_id=LOGGER_ID, 
            text=text, 
            parse_mode=ParseMode.HTML, 
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Log Error: {e}")

# --- HELPERS ---

def get_mention(user_data, custom_name=None):
    """
    Robust mention generator. 
    Works for: User Objects, Dicts, and users without @usernames.
    """
    if isinstance(user_data, (User, Chat)):
        uid = user_data.id
        first_name = user_data.first_name if hasattr(user_data, "first_name") else user_data.title
    elif isinstance(user_data, dict):
        uid = user_data.get("user_id")
        first_name = user_data.get("name", "User")
    else:
        return "Unknown"

    name = custom_name or first_name
    # HTML Escape is crucial to prevent broken tags
    safe_name = html.escape(name)

    # tg://user?id= is the only way to guarantee a clickable link for everyone
    return f"<a href='tg://user?id={uid}'><b>{safe_name}</b></a>"

def check_auto_revive(user_doc):
    try:
        if user_doc['status'] != 'dead': return False
        death_time = user_doc.get('death_time')
        if not death_time: return False

        if datetime.utcnow() - death_time > timedelta(hours=AUTO_REVIVE_HOURS):
            users_collection.update_one(
                {"user_id": user_doc["user_id"]}, 
                {
                    "$set": {"status": "alive", "death_time": None},
                    "$inc": {"balance": AUTO_REVIVE_BONUS}
                }
            )
            return True
    except: pass
    return False

def ensure_user_exists(tg_user):
    try:
        user_doc = users_collection.find_one({"user_id": tg_user.id})
        username = tg_user.username.lower() if tg_user.username else None

        if not user_doc:
            new_user = {
                "user_id": tg_user.id, 
                "name": tg_user.first_name, 
                "username": username, 
                "is_bot": tg_user.is_bot,
                "balance": 0, "inventory": [], "waifus": [], "daily_streak": 0, "last_daily": None,
                "kills": 0, "status": "alive", "protection_expiry": datetime.utcnow(), 
                "registered_at": datetime.utcnow(), "death_time": None, "seen_groups": []
            }
            users_collection.insert_one(new_user)
            return new_user
        else:
            if check_auto_revive(user_doc): 
                user_doc['status'] = 'alive'
                user_doc['balance'] += AUTO_REVIVE_BONUS

            updates = {}
            if user_doc.get("username") != username: updates["username"] = username
            if user_doc.get("name") != tg_user.first_name: updates["name"] = tg_user.first_name
            # Cleanup
            if "waifu_coins" in user_doc: users_collection.update_one({"user_id": tg_user.id}, {"$unset": {"waifu_coins": ""}})

            if updates: users_collection.update_one({"user_id": tg_user.id}, {"$set": updates})
            return user_doc
    except Exception as e:
        print(f"DB Error: {e}")
        # Fallback to prevent crash
        return {
            "user_id": tg_user.id, "name": tg_user.first_name, 
            "balance": 0, "inventory": [], "kills": 0, "status": "alive"
        }

def track_group(chat, user=None):
    """Safe Group Tracker."""
    try:
        if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            if not groups_collection.find_one({"chat_id": chat.id}):
                groups_collection.insert_one({"chat_id": chat.id, "title": chat.title, "claimed": False})
            if user:
                users_collection.update_one(
                    {"user_id": user.id}, 
                    {"$addToSet": {"seen_groups": chat.id}}
                )
    except Exception as e:
        print(f"Track Group Error: {e}")

async def resolve_target(update, context, specific_arg=None):
    # 1. Reply
    if update.message.reply_to_message:
        return ensure_user_exists(update.message.reply_to_message.from_user), None

    # 2. Argument
    query = specific_arg if specific_arg else (context.args[0] if context.args else None)
    if not query: return None, "No target"

    # 3. Lookup
    if query.isdigit():
        doc = users_collection.find_one({"user_id": int(query)})
        if doc: return doc, None
        return None, f"❌ <b>{stylize_text('Niko')}!</b> ID <code>{query}</code> not found."

    clean_username = query.replace("@", "").lower()
    doc = users_collection.find_one({"username": clean_username})
    if doc: return doc, None

    return None, f"❌ <b>{stylize_text('Oops')}!</b> User <code>@{clean_username}</code> has not started me."

def get_active_protection(user_data):
    try:
        now = datetime.utcnow()
        self_expiry = user_data.get("protection_expiry")
        partner_expiry = None
        partner_id = user_data.get("partner_id")
        if partner_id:
            partner = users_collection.find_one({"user_id": partner_id})
            if partner: partner_expiry = partner.get("protection_expiry")
        valid_expiries = []
        if self_expiry and self_expiry > now: valid_expiries.append(self_expiry)
        if partner_expiry and partner_expiry > now: valid_expiries.append(partner_expiry)
        if not valid_expiries: return None
        return max(valid_expiries)
    except: return None

def is_protected(user_data):
    return get_active_protection(user_data) is not None

def format_money(amount): return f"${amount:,}"

def format_time(timedelta_obj):
    total_seconds = int(timedelta_obj.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"
