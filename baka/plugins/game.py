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
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from baka.config import PROTECT_1D_COST, PROTECT_2D_COST, REVIVE_COST, AUTO_REVIVE_HOURS, OWNER_ID
from baka.utils import ensure_user_exists, resolve_target, is_protected, get_active_protection, format_time, format_money, get_mention, check_auto_revive
from baka.database import users_collection
from baka.plugins.chatbot import ask_mistral_raw

async def get_narrative(action_type, attacker_mention, target_mention):
    if action_type == 'kill': prompt = "Funny kill message. P1 kills P2."
    elif action_type == 'rob': prompt = "Funny rob message. P1 robs P2."
    else: return "P1 -> P2"
    res = await ask_mistral_raw("Game Narrator", prompt, 50)
    text = res if res and "P1" in res else f"P1 {action_type} P2!"
    return text.replace("P1", attacker_mention).replace("P2", target_mention)

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    target, error = await resolve_target(update, context)
    
    if not target: return await update.message.reply_text(error if error else "⚠️ <b>Usage:</b> <code>/kill @user</code>\n<i>Murder a user for loot.</i>", parse_mode=ParseMode.HTML)

    if target.get('is_bot'): return await update.message.reply_text("🤖 Bot Shield!", parse_mode=ParseMode.HTML)
    if target['user_id'] == OWNER_ID: return await update.message.reply_text("🙊 Senpai Shield!", parse_mode=ParseMode.HTML)
    if attacker['status'] == 'dead': return await update.message.reply_text("💀 You are dead.", parse_mode=ParseMode.HTML)
    if target['status'] == 'dead': return await update.message.reply_text("⚰️ Already dead.", parse_mode=ParseMode.HTML)
    if target['user_id'] == attacker['user_id']: return await update.message.reply_text("🤔 No.", parse_mode=ParseMode.HTML)
    
    expiry = get_active_protection(target)
    if expiry:
        rem = expiry - datetime.utcnow()
        return await update.message.reply_text(f"🛡️ <b>Blocked!</b> Safe for <code>{format_time(rem)}</code>.", parse_mode=ParseMode.HTML)

    # --- FAIR PLAY: MAX 1 WEAPON BUFF ---
    base_reward = random.randint(100, 200)
    weapons = [i for i in attacker.get('inventory', []) if i['type'] == 'weapon']
    best_w = max(weapons, key=lambda x: x['buff']) if weapons else None
    buff = best_w['buff'] if best_w else 0
    final_reward = int(base_reward * (1 + buff))
    
    # --- BURN FLEX ITEMS ---
    flex_burn_text = ""
    target_inv = target.get('inventory', [])
    # Filter out Flex items to delete
    flex_items = [i for i in target_inv if i['type'] == 'flex']
    if flex_items:
        users_collection.update_one({"user_id": target["user_id"]}, {"$pull": {"inventory": {"type": "flex"}}})
        flex_burn_text = f"\n🔥 <b>Burned:</b> {len(flex_items)} Flex Items destroyed!"

    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "dead", "death_time": datetime.utcnow()}})
    users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"kills": 1, "balance": final_reward}})

    narration = await get_narrative("kill", get_mention(attacker), get_mention(target))
    buff_text = f"(+{int(buff*100)}% {best_w['name']})" if best_w else ""

    await update.message.reply_text(
        f"🔪 <b>ϻυꝛᴅєꝛ!</b>\n\n📝 <i>{narration}</i>\n\n😈 <b>Killer:</b> {get_mention(attacker)}\n💀 <b>Victim:</b> {get_mention(target)}\n💵 <b>Loot:</b> <code>{format_money(final_reward)}</code> {buff_text}{flex_burn_text}", 
        parse_mode=ParseMode.HTML
    )

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    if not context.args: return await update.message.reply_text("⚠️ <b>Usage:</b> <code>/rob [amount] @user</code>", parse_mode=ParseMode.HTML)
    
    try: amount = int(context.args[0])
    except: return await update.message.reply_text("⚠️ Invalid Amount", parse_mode=ParseMode.HTML)
    target_arg = context.args[1] if len(context.args) > 1 else None
    target, error = await resolve_target(update, context, specific_arg=target_arg)
    if not target: return await update.message.reply_text(error or "⚠️ Tag victim", parse_mode=ParseMode.HTML)

    if target.get('is_bot') or target['user_id'] == OWNER_ID: return await update.message.reply_text("🛡️ ᴘꝛσᴛєᴄᴛєᴅ.", parse_mode=ParseMode.HTML)
    if attacker['status'] == 'dead': return await update.message.reply_text("💀 Dead.", parse_mode=ParseMode.HTML)
    if target['user_id'] == attacker['user_id']: return await update.message.reply_text("🤦‍♂️ No.", parse_mode=ParseMode.HTML)
    
    expiry = get_active_protection(target)
    if expiry:
        rem = expiry - datetime.utcnow()
        return await update.message.reply_text(f"🛡️ <b>Shielded!</b> Safe for <code>{format_time(rem)}</code>.", parse_mode=ParseMode.HTML)

    if target['balance'] < amount: return await update.message.reply_text("📉 Too poor.", parse_mode=ParseMode.HTML)

    # --- FAIR PLAY: MAX 1 ARMOR BLOCK ---
    armors = [i for i in target.get('inventory', []) if i['type'] == 'armor']
    best_a = max(armors, key=lambda x: x['buff']) if armors else None
    block_chance = best_a['buff'] if best_a else 0

    if random.random() < block_chance:
        return await update.message.reply_text(f"🛡️ <b>BLOCKED!</b> {get_mention(target)} used {best_a['name']} to stop you!", parse_mode=ParseMode.HTML)

    # Execute
    users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": -amount}})
    users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"balance": amount}})
    
    narration = await get_narrative("rob", get_mention(attacker), get_mention(target))
    header = "🧟 <b>ɢꝛᴧᴠє ꝛσʙʙєꝛʏ!</b>" if target['status'] == 'dead' else "💰 <b>ꝛσʙʙєꝛʏ!</b>"

    await update.message.reply_text(
        f"{header}\n\n📝 <i>{narration}</i>\n\n😈 <b>Thief:</b> {get_mention(attacker)}\n💸 <b>Stolen:</b> <code>{format_money(amount)}</code>", 
        parse_mode=ParseMode.HTML
    )

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = ensure_user_exists(update.effective_user)
    if not context.args: return await update.message.reply_text("⚠️ <b>Usage:</b> <code>/protect 1d</code> or <code>2d</code>", parse_mode=ParseMode.HTML)

    dur = context.args[0].lower()
    if dur == '1d': cost, days = PROTECT_1D_COST, 1
    elif dur == '2d': cost, days = PROTECT_2D_COST, 2
    else: return await update.message.reply_text("⚠️ 1d or 2d only!", parse_mode=ParseMode.HTML)

    target_arg = context.args[1] if len(context.args) > 1 else None
    target, _ = await resolve_target(update, context, specific_arg=target_arg)
    if not target: target = sender
    is_self = target['user_id'] == sender['user_id']
    
    # Couple Check
    if not is_self and sender.get("partner_id") != target["user_id"]:
         return await update.message.reply_text("⛔ Couples only!", parse_mode=ParseMode.HTML)

    expiry = get_active_protection(target)
    if expiry:
        rem = expiry - datetime.utcnow()
        return await update.message.reply_text(f"🛡️ <b>Already Safe!</b> <code>{format_time(rem)}</code>.", parse_mode=ParseMode.HTML)
    
    if sender['balance'] < cost: return await update.message.reply_text(f"❌ Need <code>{format_money(cost)}</code>", parse_mode=ParseMode.HTML)

    users_collection.update_one({"user_id": sender["user_id"]}, {"$inc": {"balance": -cost}})
    expiry_dt = datetime.utcnow() + timedelta(days=days)
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"protection_expiry": expiry_dt}})
    
    partner_id = target.get("partner_id")
    extra = ""
    if partner_id:
        users_collection.update_one({"user_id": partner_id}, {"$set": {"protection_expiry": expiry_dt}})
        extra = "\n💞 <b>Bonus:</b> Partner Protected!"

    if is_self: await update.message.reply_text(f"🛡️ <b>Shield Active!</b> {days} days.{extra}", parse_mode=ParseMode.HTML)
    else: await update.message.reply_text(f"🛡️ <b>Guardian!</b> Protected {get_mention(target)}.{extra}", parse_mode=ParseMode.HTML)

async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reviver = ensure_user_exists(update.effective_user)
    target, _ = await resolve_target(update, context)
    if not target: target = reviver
    
    if target['status'] == 'alive': return await update.message.reply_text("✨ Alive!", parse_mode=ParseMode.HTML)
    if reviver['balance'] < REVIVE_COST: return await update.message.reply_text(f"❌ Need <code>{format_money(REVIVE_COST)}</code>.", parse_mode=ParseMode.HTML)

    users_collection.update_one({"user_id": reviver["user_id"]}, {"$inc": {"balance": -REVIVE_COST}})
    users_collection.update_one({"user_id": OWNER_ID}, {"$inc": {"balance": REVIVE_COST}})
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "alive", "death_time": None}})
    await update.message.reply_text(f"💖 <b>Revived!</b> Paid {format_money(REVIVE_COST)}.", parse_mode=ParseMode.HTML)
