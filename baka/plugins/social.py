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

import random
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatType, ChatMemberStatus
from baka.utils import ensure_user_exists, resolve_target, get_mention, format_money, stylize_text
from baka.database import users_collection
from baka.config import DIVORCE_COST, BOT_NAME
from baka.plugins.chatbot import ask_mistral_raw

def get_progress_bar(percent):
    filled = int(percent / 10)
    bar = "█" * filled + "▒" * (10 - filled)
    return bar

def get_love_comment(percent):
    if percent < 30: return "💔 Terrible!"
    if percent < 60: return "🤔 Hmm..."
    if percent < 90: return "💖 Good!"
    return "🔥 Soulmates!"

async def couple_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Matches users in group."""
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == ChatType.PRIVATE: return await update.message.reply_text("❌ Group Only!", parse_mode=ParseMode.HTML)

    user1 = ensure_user_exists(user)
    
    # Check for specific target
    target_arg = context.args[0] if context.args else None
    target, _ = await resolve_target(update, context, specific_arg=target_arg)
    
    if target:
        user2 = target
    else:
        try:
            # Random Match in Group
            pipeline = [{"$match": {"seen_groups": chat.id, "user_id": {"$ne": user.id}}}, {"$sample": {"size": 1}}]
            results = list(users_collection.aggregate(pipeline))
            if not results: return await update.message.reply_text("😔 No one else found here.", parse_mode=ParseMode.HTML)
            user2 = results[0]
        except:
             return await update.message.reply_text("⚠️ DB Error", parse_mode=ParseMode.HTML)

    percent = random.randint(0, 100)
    await update.message.reply_text(
        f"💘 <b>Match:</b> {get_mention(user1)} x {get_mention(user2)}\n"
        f"📊 <b>{percent}%</b> <code>{get_progress_bar(percent)}</code>\n"
        f"💭 <i>{get_love_comment(percent)}</i>",
        parse_mode=ParseMode.HTML
    )

async def propose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = ensure_user_exists(update.effective_user)
    if sender.get("partner_id"): return await update.message.reply_text("❌ Married!", parse_mode=ParseMode.HTML)
    
    target_arg = context.args[0] if context.args else None
    target, error = await resolve_target(update, context, specific_arg=target_arg)
    
    if not target: return await update.message.reply_text(error or "⚠️ <b>Usage:</b> <code>/propose @user</code>", parse_mode=ParseMode.HTML)
    if target['user_id'] == sender['user_id']: return await update.message.reply_text("🥲 No.", parse_mode=ParseMode.HTML)
    if target.get('partner_id'): return await update.message.reply_text("💔 Taken.", parse_mode=ParseMode.HTML)

    s_id, t_id = sender['user_id'], target['user_id']
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💍 Accept", callback_data=f"marry_y|{s_id}|{t_id}"), InlineKeyboardButton("🗑️ Reject", callback_data=f"marry_n|{s_id}|{t_id}")]])
    
    msg = await update.message.reply_text(f"💘 <b>Proposal!</b>\n{get_mention(sender)} 💍 {get_mention(target)}", reply_markup=kb, parse_mode=ParseMode.HTML)
    
    async def delete():
        await asyncio.sleep(30)
        try: await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=msg.message_id, text="❌ Expired.", parse_mode=ParseMode.HTML)
        except: pass
    asyncio.create_task(delete())

async def marry_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_arg = context.args[0] if context.args else None
    target, _ = await resolve_target(update, context, specific_arg=target_arg)
    user = target if target else ensure_user_exists(update.effective_user)
    
    pid = user.get("partner_id")
    pname = "None"
    if pid:
        p = users_collection.find_one({"user_id": pid})
        pname = get_mention(p) if p else str(pid)
    
    await update.message.reply_text(f"📊 <b>Status:</b>\n👤 {get_mention(user)}\n💍 {pname}", parse_mode=ParseMode.HTML)

async def divorce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user_exists(update.effective_user)
    if not user.get("partner_id"): return await update.message.reply_text("🤷‍♂️ Single.", parse_mode=ParseMode.HTML)
    if user['balance'] < DIVORCE_COST: return await update.message.reply_text(f"❌ Cost: {format_money(DIVORCE_COST)}", parse_mode=ParseMode.HTML)

    pid = user["partner_id"]
    users_collection.update_one({"user_id": user["user_id"]}, {"$set": {"partner_id": None}, "$inc": {"balance": -DIVORCE_COST}})
    users_collection.update_one({"user_id": pid}, {"$set": {"partner_id": None}})
    await update.message.reply_text(f"💔 <b>Divorced!</b> Paid {format_money(DIVORCE_COST)}.", parse_mode=ParseMode.HTML)

async def proposal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, p_id, t_id = data[0], int(data[1]), int(data[2])
    
    if query.from_user.id != t_id: return await query.answer("❌ Not for you!", show_alert=True)

    if action == "marry_y":
        users_collection.update_one({"user_id": p_id}, {"$set": {"partner_id": t_id}})
        users_collection.update_one({"user_id": t_id}, {"$set": {"partner_id": p_id}})
        await query.message.edit_text(f"💍 <b>Married!</b>\n<a href='tg://user?id={p_id}'>P1</a> ❤️ <a href='tg://user?id={t_id}'>P2</a>", parse_mode=ParseMode.HTML)
    elif action == "marry_n":
        roast = await ask_mistral_raw("Roaster", "Roast a rejected proposal in Hindi.")
        await query.message.edit_text(f"❌ <b>Rejected!</b>\n🔥 {stylize_text(roast or 'Lol')}", parse_mode=ParseMode.HTML)
