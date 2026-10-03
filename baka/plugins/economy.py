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

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatType
from baka.config import REGISTER_BONUS, OWNER_ID, TAX_RATE, CLAIM_BONUS, MARRIED_TAX_RATE, SHOP_ITEMS, MIN_CLAIM_MEMBERS
from baka.utils import ensure_user_exists, get_mention, format_money, resolve_target, log_to_channel, stylize_text, track_group
from baka.database import users_collection, groups_collection
from baka.plugins.chatbot import ask_mistral_raw

# --- INVENTORY CALLBACK ---
async def inventory_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    item_id = data[1]
    
    item = next((i for i in SHOP_ITEMS if i['id'] == item_id), None)
    if not item: 
        await query.answer("❌ Item data not found.", show_alert=True)
        return

    rarity_text = "Common"
    if item['price'] > 100000: rarity_text = "Rare"
    if item['price'] > 1000000: rarity_text = "Legendary"
    if item['price'] > 100000000: rarity_text = "Godly"

    text = (
        f"💎 𝐅𝐥𝐞𝐱 𝐈𝐭𝐞𝐦: {item['name']}\n"
        f"💰 𝐕𝐚𝐥𝐮𝐞: {format_money(item['price'])}\n"
        f"🌟 𝐑𝐚𝐫𝐢𝐭𝐲: {rarity_text}\n"
        f"🛡️ 𝐒𝐭𝐚𝐭𝐮𝐬: Safe (Unless you die!)"
    )
    await query.answer(text, show_alert=True)

# --- COMMANDS ---

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registers a new user (PM Only)."""
    user = update.effective_user
    chat = update.effective_chat
    
    # --- FIX: PM ONLY CHECK ---
    if chat.type != ChatType.PRIVATE:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Register Here", url=f"https://t.me/{context.bot.username}?start=register")]])
        return await update.message.reply_text(
            "❌ <b>Niko!</b> You cannot register in a group!\n"
            "<i>Go to my PM to create your wallet securely.</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb
        )

    if users_collection.find_one({"user_id": user.id}): 
        return await update.message.reply_text(f"✨ <b>Ara?</b> {get_mention(user)}, you are already registered!", parse_mode=ParseMode.HTML)
    
    ensure_user_exists(user)
    users_collection.update_one({"user_id": user.id}, {"$set": {"balance": REGISTER_BONUS}})
    
    await update.message.reply_text(
        f"🎉 <b>Yayy!</b> {get_mention(user)} Registered!\n"
        f"🎁 <b>Welcome Bonus:</b> <code>+{format_money(REGISTER_BONUS)}</code>\n"
        f"ℹ️ <i>Use /help to learn how to play!</i>", 
        parse_mode=ParseMode.HTML
    )

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """One-time bonus for groups (Group Only)."""
    chat = update.effective_chat
    user = update.effective_user
    
    # --- FIX: GROUP ONLY CHECK ---
    if chat.type == ChatType.PRIVATE:
        return await update.message.reply_text("⚠️ <b>Niko!</b> This command is for Group Bonuses only.", parse_mode=ParseMode.HTML)
    
    ensure_user_exists(user)
    
    # Ensure group exists in DB (Fixes 'Not Working' issue)
    track_group(chat, user)
    
    group_doc = groups_collection.find_one({"chat_id": chat.id})
    
    if group_doc.get("claimed"): 
        return await update.message.reply_text("❌ <b>Too late!</b> This group bonus has already been claimed.", parse_mode=ParseMode.HTML)
    
    # Check Member Count
    try: 
        count = await context.bot.get_chat_member_count(chat.id)
    except: 
        return await update.message.reply_text("⚠️ I need <b>Admin Rights</b> to verify member count!", parse_mode=ParseMode.HTML)

    if count < MIN_CLAIM_MEMBERS:
        # Generate Roast
        roast = await ask_mistral_raw("Roaster", f"Roast {user.first_name} for claiming in a group with only {count} members. Needs {MIN_CLAIM_MEMBERS}.")
        final_roast = roast if roast else "Itna sannaata kyu hai bhai? 😂"
        
        return await update.message.reply_text(
            f"❌ <b>Claim Failed!</b>\n\n"
            f"📉 <b>Members:</b> {count}/{MIN_CLAIM_MEMBERS}\n"
            f"🔥 <b>Roast:</b> <i>{stylize_text(final_roast)}</i>", 
            parse_mode=ParseMode.HTML
        )
    
    # Process Claim
    users_collection.update_one({"user_id": user.id}, {"$inc": {"balance": CLAIM_BONUS}})
    groups_collection.update_one({"chat_id": chat.id}, {"$set": {"claimed": True}})
    
    await update.message.reply_text(
        f"💎 <b>𝐂𝐥𝐚𝐢𝐦 𝐒𝐮𝐜𝐜𝐞𝐬𝐬𝐟𝐮𝐥!</b>\n\n"
        f"👤 <b>Claimer:</b> {get_mention(user)}\n"
        f"💰 <b>Reward:</b> <code>+{format_money(CLAIM_BONUS)}</code>\n"
        f"🏆 <i>Congratulations! You were the fastest.</i>", 
        parse_mode=ParseMode.HTML
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target, error = await resolve_target(update, context)
    if not target and error == "No target": target = ensure_user_exists(update.effective_user)
    elif not target: return await update.message.reply_text(error, parse_mode=ParseMode.HTML)

    rank = users_collection.count_documents({"balance": {"$gt": target["balance"]}}) + 1
    status = "💖 Alive" if target['status'] == 'alive' else "💀 Dead"
    
    inventory = target.get('inventory', [])
    weapons = [i for i in inventory if i['type'] == 'weapon']
    armors = [i for i in inventory if i['type'] == 'armor']
    flex_items = [i for i in inventory if i['type'] == 'flex']
    
    best_w = max(weapons, key=lambda x: x['buff']) if weapons else None
    best_a = max(armors, key=lambda x: x['buff']) if armors else None
    
    w_text = f"{best_w['name']} (+{int(best_w['buff']*100)}%)" if best_w else "None"
    a_text = f"{best_a['name']} ({int(best_a['buff']*100)}% Block)" if best_a else "None"
    
    kb = []
    row = []
    for item in flex_items:
        row.append(InlineKeyboardButton(item['name'], callback_data=f"inv_view|{item['id']}"))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row: kb.append(row)
    reply_markup = InlineKeyboardMarkup(kb) if kb else None

    msg = (
        f"👤 <b>User:</b> {get_mention(target)}\n"
        f"👛 <b>Balance:</b> <code>{format_money(target['balance'])}</code>\n"
        f"🏆 <b>Rank:</b> <code>#{rank}</code>\n"
        f"❤️ <b>Status:</b> {status}\n"
        f"⚔️ <b>Kills:</b> <code>{target['kills']}</code>\n\n"
        f"🎒 <b>𝐀𝐜𝐭𝐢𝐯𝐞 𝐆𝐞𝐚𝐫:</b>\n"
        f"🗡️ <b>Weapon:</b> {w_text}\n"
        f"🛡️ <b>Armor:</b> {a_text}\n\n"
        f"💎 <b>𝐅𝐥𝐞𝐱 𝐂𝐨𝐥𝐥𝐞𝐜𝐭𝐢𝐨𝐧:</b>"
    )
    
    if not flex_items: msg += "\n<i>(No flex items owned)</i>"
    else: msg += "\n<i>(Click buttons to view details)</i>"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rich = users_collection.find().sort("balance", -1).limit(10)
    kills = users_collection.find().sort("kills", -1).limit(10)

    def get_badge(i): return ["🥇","🥈","🥉"][i-1] if i<=3 else f"<code>{i}.</code>"

    msg = "🏆 <b>𝐆𝐋𝐎𝐁𝐀𝐋 𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃</b> 🏆\n\n"
    msg += "💰 <b>𝐓𝐨𝐩 𝟏𝟎 𝐑𝐢𝐜𝐡𝐞𝐬𝐭:</b>\n"
    for i, d in enumerate(rich, 1): 
        msg += f"{get_badge(i)} {get_mention(d)} » <b>{format_money(d['balance'])}</b>\n"
    
    msg += "\n🩸 <b>𝐓𝐨𝐩 𝟏𝟎 𝐊𝐢𝐥𝐥𝐞𝐫𝐬:</b>\n"
    for i, d in enumerate(kills, 1): 
        msg += f"{get_badge(i)} {get_mention(d)} » <b>{d.get('kills',0)} Kills</b>\n"

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = ensure_user_exists(update.effective_user)
    args = context.args
    if not args: return await update.message.reply_text("⚠️ <b>Usage:</b> <code>/give 100 @user</code>", parse_mode=ParseMode.HTML)

    amount = None
    target_str = None
    for arg in args:
        if arg.isdigit() and amount is None: amount = int(arg)
        else: target_str = arg
    
    if amount is None: return await update.message.reply_text("⚠️ <b>Error:</b> Amount must be a number.", parse_mode=ParseMode.HTML)

    target, error = await resolve_target(update, context, specific_arg=target_str)
    
    if not target: return await update.message.reply_text(error or "⚠️ <b>Tag someone to give coins.</b>", parse_mode=ParseMode.HTML)

    if amount <= 0: return await update.message.reply_text("⚠️ Don't be cheeky!", parse_mode=ParseMode.HTML)
    if sender['balance'] < amount: return await update.message.reply_text(f"📉 <b>Poor!</b> You only have <code>{format_money(sender['balance'])}</code>", parse_mode=ParseMode.HTML)
    if sender['user_id'] == target['user_id']: return await update.message.reply_text("🤔 Sending money to yourself?", parse_mode=ParseMode.HTML)

    current_tax = TAX_RATE
    tax_type = "Standard"
    
    if sender.get("partner_id") == target["user_id"]:
        current_tax = MARRIED_TAX_RATE
        tax_type = "Couple (5%)"

    tax = int(amount * current_tax)
    final_amt = amount - tax
    
    users_collection.update_one({"user_id": sender["user_id"]}, {"$inc": {"balance": -amount}})
    users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": final_amt}})
    users_collection.update_one({"user_id": OWNER_ID}, {"$inc": {"balance": tax}})

    msg = (
        f"💸 <b>𝐓𝐫𝐚𝐧𝐬𝐟𝐞𝐫 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞!</b>\n"
        f"👤 <b>From:</b> {get_mention(sender)}\n"
        f"👤 <b>To:</b> {get_mention(target)}\n"
        f"💰 <b>Sent:</b> <code>{format_money(final_amt)}</code>\n"
        f"🏦 <b>Tax:</b> <code>{format_money(tax)}</code> ({tax_type})"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    
    await log_to_channel(context.bot, "transfer", {
        "user": f"{get_mention(sender)} (`{sender['user_id']}`)",
        "action": f"Transferred {format_money(amount)} to {get_mention(target)} (Tax: {tax_type})",
        "chat": "Economy System"
    })
