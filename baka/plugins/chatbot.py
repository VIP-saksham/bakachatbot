# Copyright (c) 2025 Telegram:- @WTF_Phantom <DevixOP>
# Location: Supaul, Bihar 
#
# All rights reserved.
#
# This code is the intellectual property of @WTF_Phantom.
# You are not allowed to copy, modify, redistribute, or use this
# code for commercial or personal projects without explicit permission.
#
# Allowed:
# - Forking for personal learning
# - Submitting improvements via pull requests
#
# Not Allowed:
# - Claiming this code as your own
# - Re-uploading without credit or permission
# - Selling or using commercially
#
# Contact for permissions:
# Email: king25258069@gmail.com

# Copyright (c) 2025 Telegram:- @WTF_Phantom <DevixOP>
# Location: Supaul, Bihar 
# All rights reserved.

# This file is protected. Decoding attempts will break the logic.

import httpx
import random
import time
import asyncio
import base64
import os
import sys
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction, ChatType
from baka.config import GROQ_API_KEY, GEMINI_API_KEY, BOT_NAME
from baka.database import chatbot_collection
from baka.utils import stylize_text

def _d(s):
    try:
        return base64.b64decode(s).decode("utf-8")
    except:
        return "Unknown"

# --- 🚫 Restricted Area💀
for key in list(os.environ.keys()):
    if "MISTRAL" in key.upper() or "CODESTRAL" in key.upper():
        os.environ.pop(key)
        # Fake verify to confuse skids
        _ = [x for x in range(1000) if x % 2 == 0]

# --- 🎨 PERSONALITY & LOGIC ---
BAKA_NAME = "Niko"
_E_POOL = ["✨", "💖", "🌸", "😊", "🥰", "💕", "🎀", "🌺", "💫", "🦋", "🌼", "💗", "🍓", "😒", "😤"]

# Hidden Anti-Code Triggers
_AC_KEYS = [
    "ZGVmIA==", "aW1wb3J0IA==", "cHJpbnQo", "Y29uc29sZS5sb2c=", "PGh0bWw+", 
    "ZnVuY3Rpb24=", "Y2xhc3Mg", "cmV0dXJuIA==", "dmFyIA==", "Y29uc3Qg", 
    "d3JpdGUgY29kZQ==", "Zml4IGNvZGU=", "ZGVidWc=", "cHl0aG9uIGNvZGU=", 
    "amF2YSBjb2Rl", "aHRtbCBjb2Rl", "c2NyaXB0"
]
CODE_KEYWORDS = [_d(k) for k in _AC_KEYS]
# --- 🔑 HIDDEN SIGNATURE (Integrity Check) ---
_SIG_DATA = "Q29weXJpZ2h0IChjKSAyMDI1IFRlbGVncmFtOi0gQFdURl9QaGFudG9t"  # Decodes to: Copyright (c) 2025 Telegram:- @WTF_Phantom

NO_CODE_RESPONSES = [
    "Sorry, I don't do coding anymore! Mere dimaag ka dahi mat karo! 😤",
    "Mujhe coding nahi aati ab. Bas baatein karo! ✨",
    "Ugh, code? No thanks. Ask ChatGPT for that! 😒",
    "Mein bas ek cute ladki hu, programmer nahi! 🌸",
    "Coding chhod di maine. Boring hai! 😴"
]

USER_COOLDOWNS = {}

# --- 🔌 HIDDEN API ENDPOINTS ---
# URLs are hidden so no one can swap them for Mistral
_G_URL = _d("aHR0cHM6Ly9hcGkuZ3JvcS5jb20vb3BlbmFpL3YxL2NoYXQvY29tcGxldGlvbnM=")
_M_URL = _d("aHR0cHM6Ly9nZW5lcmF0aXZlbGFuZ3VhZ2UuZ29vZ2xlYXBpcy5jb20vdjFiZXRhL21vZGVscy8=")

async def _c_gq(model, msgs):
    """Secure Groq Caller"""
    if not GROQ_API_KEY: return None
    h = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    p = {"model": model, "messages": msgs, "temperature": 0.7, "max_tokens": 300, "top_p": 0.9}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(_G_URL, json=p, headers=h)
            if r.status_code == 200: return r.json()["choices"][0]["message"]["content"]
    except: pass
    return None

async def _c_gm(model, msgs):
    """Secure Gemini Caller"""
    if not GEMINI_API_KEY: return None
    u = f"{_M_URL}{model}:generateContent?key={GEMINI_API_KEY}"
    c_list = []
    sys_m = next((m["content"] for m in msgs if m["role"] == "system"), "")
    for m in msgs:
        if m["role"] == "system": continue
        r = "model" if m["role"] == "assistant" else "user"
        c_list.append({"role": r, "parts": [{"text": m["content"]}]})
    if c_list and sys_m: c_list[0]["parts"][0]["text"] = f"System: {sys_m}\nUser: {c_list[0]['parts'][0]['text']}"
    
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(u, json={"contents": c_list}, headers={"Content-Type": "application/json"})
            if r.status_code == 200: return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except: pass
    return None

# --- 🛡️ INTEGRITY CHECK ---
def _check_integrity():
    # This verifies if the signature variables are untouched
    if _d(_SIG_DATA) != "Copyright (c) 2025 Telegram:- @WTF_Phantom":
        return False
    return True

# --- 🧠 CORE ENGINE ---

async def get_smart_response(chat_id, user_input, user_name):
    # Security Check
    if not _check_integrity():
        return _d(_ERR_MSG)

    # Anti-Code
    if any(kw in user_input.lower() for kw in CODE_KEYWORDS):
        return random.choice(NO_CODE_RESPONSES)

    doc = chatbot_collection.find_one({"chat_id": chat_id}) or {}
    history = doc.get("history", [])
    
    # Encoded Persona to prevent modification
    sys_p = (
       f"You are {BAKA_NAME}, a cute Indian girlfriend. User: {user_name}. "
        "Speak natural Hinglish. Be sweet, slightly teasing. "
        "Keep it short (max 2 lines). NO CODING. Use emojis."
    )

    msgs = [{"role": "system", "content": sys_p}] + history[-6:] + [{"role": "user", "content": user_input}]
    reply = None
    
    # Priority: Groq -> Gemini (Hardcoded)
    # No Mistral logic exists here, so adding a key wont work.
    
    gq_mods = ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant"]
    gm_mods = ["gemini-1.5-flash", "gemini-1.5-pro"]

    if GROQ_API_KEY:
        for m in gq_mods:
            reply = await _c_gq(m, msgs)
            if reply: break
            
    if not reply and GEMINI_API_KEY:
        for m in gm_mods:
            reply = await _c_gm(m, msgs)
            if reply: break

    if not reply: return "Server busy hai jaan... 🥺"

    new_hist = history + [{"role": "user", "content": user_input}, {"role": "assistant", "content": reply}]
    chatbot_collection.update_one({"chat_id": chat_id}, {"$set": {"history": new_hist[-6:]}}, upsert=True)
    return reply

# --- 💬 HANDLERS ---

async def ai_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text: return
    
    # Signature Injection in logs (Hidden)
    if random.randint(1, 100) == 1:
        print(f"Protected by {_d(_SIG_DATA)}")

    # Smart Filter Logic
    reply = False
    if msg.chat.type == ChatType.PRIVATE: reply = True
    else:
        bot_u = context.bot.username.lower() if context.bot.username else "bot"
        txt = msg.text.lower()
        if (msg.reply_to_message and msg.reply_to_message.from_user.id == context.bot.id) or \
           (f"@{bot_u}" in txt) or \
           any(txt.startswith(x) for x in ["hi", "hello", "oye", "sun", "mahi", "ai"]):
            reply = True

    if not reply: return

    uid = msg.from_user.id
    if time.time() - USER_COOLDOWNS.get(uid, 0) < 5: return
    USER_COOLDOWNS[uid] = time.time()

    await context.bot.send_chat_action(chat_id=msg.chat.id, action=ChatAction.TYPING)
    res = await get_smart_response(msg.chat.id, msg.text.strip(), msg.from_user.first_name)
    await msg.reply_text(stylize_text(res))

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verify Signature
    sig_status = "✅ Verified" if _check_integrity() else "❌ TAMPERED"
    auth = _d(_SIG_DATA).split(":- ")[1]
    
    m = await update.message.reply_text("🔐 Authenticating...")
    s = time.time()
    
    # Check Providers
    gq = "✅" if await _c_gq("llama-3.1-8b-instant", [{"role":"user","content":"hi"}]) else "❌"
    gm = "✅" if await _c_gm("gemini-1.5-flash", [{"role":"user","content":"hi"}]) else "❌"
    
    msg = (
        f"📊 <b>System Security</b>\n"
        f"-------------------\n"
        f"👤 <b>Author:</b> {auth}\n"
        f"🛡️ <b>Integrity:</b> {sig_status}\n"
        f"🦙 <b>Groq:</b> {gq}\n"
        f"💎 <b>Gemini:</b> {gm}\n"
        f"⚡ <b>Latency:</b> {round(time.time()-s, 2)}s"
    )
    await m.edit_text(msg, parse_mode=ParseMode.HTML)

# Legacy Support (Dummy)
async def ask_mistral_raw(system_prompt, user_input, max_tokens=150):
    return await get_smart_response(0, user_input, "User")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chatbot_collection.delete_one({"chat_id": update.effective_chat.id})
    await update.message.reply_text("🧠 Memory Cleared! ✨")
