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
from telegram.constants import ParseMode
from baka.utils import ensure_user_exists, format_money, get_mention
from baka.database import users_collection
from baka.config import SHOP_ITEMS

ITEMS_PER_PAGE = 6

# --- HELPERS ---

def get_rarity(price):
    if price < 5000: return "⚪ Common"
    if price < 20000: return "🟢 Uncommon"
    if price < 100000: return "🔵 Rare"
    if price < 1000000: return "🟣 Epic"
    if price < 10000000: return "🟡 Legendary"
    return "🔴 GODLY"

def get_description(item):
    """Generates a cool description based on item type."""
    if item['id'] == "deathnote": return "Writes names. Deletes people. 60% Kill Buff."
    if item['id'] == "plot": return "Literal Plot Armor. You cannot die. 60% Block."
    
    if item['type'] == 'weapon':
        return f"A deadly weapon. Increases your kill rewards by +{int(item['buff']*100)}%."
    elif item['type'] == 'armor':
        return f"Protective gear. Gives a {int(item['buff']*100)}% chance to block any robbery attempt."
    elif item['type'] == 'flex':
        return "A useless item for rich people. Shows off your massive wealth."
    return "Unknown Item."

# --- KEYBOARD BUILDERS ---

def get_main_menu_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴡєᴧᴘσηs", callback_data="shop_cat|weapon"),
            InlineKeyboardButton("ᴧꝛϻσꝛ", callback_data="shop_cat|armor")
        ],
        [
            InlineKeyboardButton("Ғʟєx & ᴠɪᴘ", callback_data="shop_cat|flex")
        ],
        [InlineKeyboardButton("ᴄʟσsє", callback_data="shop_close")]
    ])

def get_category_kb(category_type, page=0):
    items = [i for i in SHOP_ITEMS if i['type'] == category_type]
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    current_items = items[start_idx:end_idx]
    
    keyboard = []
    row = []
    for item in current_items:
        price_k = f"{item['price']//1000}k" if item['price'] >= 1000 else item['price']
        text = f"{item['name']} [{price_k}]"
        callback = f"shop_view|{item['id']}|{category_type}|{page}"
        row.append(InlineKeyboardButton(text, callback_data=callback))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    
    nav = []
    if page > 0: nav.append(InlineKeyboardButton("⬅️", callback_data=f"shop_cat|{category_type}|{page-1}"))
    nav.append(InlineKeyboardButton("ϻєηυ", callback_data="shop_home"))
    if end_idx < len(items): nav.append(InlineKeyboardButton("➡️", callback_data=f"shop_cat|{category_type}|{page+1}"))
    
    keyboard.append(nav)
    return InlineKeyboardMarkup(keyboard)

def get_item_kb(item_id, category, page, can_afford, is_owned):
    kb = []
    if is_owned:
        kb.append([InlineKeyboardButton("σᴡєηꝛ", callback_data="shop_owned")])
    elif can_afford:
        kb.append([InlineKeyboardButton("ʙυʏ ησᴡ", callback_data=f"shop_buy|{item_id}|{category}|{page}")])
    else:
        kb.append([InlineKeyboardButton("❌ 𝐂𝐚𝐧'𝐭 𝐀𝐟𝐟𝐨𝐫𝐝", callback_data="shop_poor")])
        
    kb.append([InlineKeyboardButton("🔙 𝐁𝐚𝐜𝐤", callback_data=f"shop_cat|{category}|{page}")])
    return InlineKeyboardMarkup(kb)

# --- MENUS ---

async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = ensure_user_exists(update.effective_user)
        bal = format_money(user['balance'])
        
        text = (
            f"🛒 <b>𝐁𝐚𝐤𝐚 𝐌𝐚𝐫𝐤𝐞𝐭𝐩𝐥𝐚𝐜𝐞</b>\n\n"
            f"👤 <b>Customer:</b> {get_mention(user)}\n"
            f"👛 <b>Wallet:</b> <code>{bal}</code>\n\n"
            f"<i>Select a category to browse our goods!</i>"
        )
        
        kb = get_main_menu_kb()
        
        if update.callback_query:
            await update.callback_query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
            
    except Exception as e:
        print(f"Shop Error: {e}")
        # Fallback in case of error
        if update.callback_query:
            await update.callback_query.answer("❌ Shop Error", show_alert=True)
        else:
            await update.message.reply_text("❌ <b>Shop Error:</b> Please check logs.", parse_mode=ParseMode.HTML)

# --- CALLBACK HANDLER ---

async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = ensure_user_exists(query.from_user)
    data = query.data.split("|")
    action = data[0]
    
    if action == "shop_close":
        await query.message.delete()
        return

    if action == "shop_home":
        await shop_menu(update, context)
        return
    
    # --- CATEGORY VIEW ---
    if action == "shop_cat":
        cat_type = data[1]
        page = int(data[2]) if len(data) > 2 else 0
        
        titles = {
            "weapon": "⚔️ <b>𝐖𝐞𝐚𝐩𝐨𝐧𝐬 𝐀𝐫𝐦𝐨𝐫𝐲</b>\n<i>Lethal gear for killers.</i>",
            "armor": "🛡️ <b>𝐃𝐞𝐟𝐞𝐧𝐬𝐞 𝐒𝐲𝐬𝐭𝐞𝐦𝐬</b>\n<i>Protection against thieves.</i>",
            "flex": "💎 <b>𝐕𝐈𝐏 𝐅𝐥𝐞𝐱 𝐙𝐨𝐧𝐞</b>\n<i>Pure status symbols.</i>"
        }
        
        text = f"{titles.get(cat_type, 'Shop')}\n\n💰 <b>Balance:</b> <code>{format_money(user['balance'])}</code>"
        
        await query.message.edit_text(
            text, 
            parse_mode=ParseMode.HTML, 
            reply_markup=get_category_kb(cat_type, page)
        )
        return

    # --- ITEM INSPECTOR ---
    if action == "shop_view":
        item_id, cat, page = data[1], data[2], data[3]
        item = next((i for i in SHOP_ITEMS if i['id'] == item_id), None)
        if not item: return await query.answer("❌ Item removed.", show_alert=True)
        
        # Stats Display
        rarity = get_rarity(item['price'])
        desc = get_description(item)
        
        stats = ""
        life = "♾️ Permanent" if item['type'] == 'flex' else "⏳ 24 Hours"
        
        if item['type'] == 'weapon':
            stats = f"💥 <b>Buff:</b> +{int(item['buff']*100)}% Kill Loot"
        elif item['type'] == 'armor':
            stats = f"🛡️ <b>Defense:</b> {int(item['buff']*100)}% Block Chance"
        
        is_owned = any(i['id'] == item_id for i in user.get('inventory', []))
        can_afford = user['balance'] >= item['price']
        
        text = (
            f"🛍️ <b>{item['name']}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📖 <i>{desc}</i>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Price:</b> <code>{format_money(item['price'])}</code>\n"
            f"🌟 <b>Rarity:</b> {rarity}\n"
            f"{stats}\n"
            f"⏱️ <b>Life:</b> {life}\n\n"
            f"👛 <b>Your Wallet:</b> <code>{format_money(user['balance'])}</code>"
        )
        
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_item_kb(item_id, cat, page, can_afford, is_owned)
        )
        return

    # --- BUY ACTION ---
    if action == "shop_buy":
        item_id = data[1]
        item = next((i for i in SHOP_ITEMS if i['id'] == item_id), None)
        
        if not item: return await query.answer("❌ Error", show_alert=True)
        
        # Re-fetch user to be safe
        user = ensure_user_exists(query.from_user)

        if user['balance'] < item['price']:
            return await query.answer(f"❌ You need {format_money(item['price'])}!", show_alert=True)
            
        # FAIR PLAY: Unique Items
        if any(i['id'] == item_id for i in user.get('inventory', [])):
            return await query.answer("⚠️ You already own this item!", show_alert=True)
            
        # Add Timestamp for 24h expiry
        from datetime import datetime
        item_with_time = item.copy()
        item_with_time['bought_at'] = datetime.utcnow()

        users_collection.update_one(
            {"user_id": user['user_id']},
            {
                "$inc": {"balance": -item['price']},
                "$push": {"inventory": item_with_time}
            }
        )
        
        await query.answer(f"🎉 Bought {item['name']}!", show_alert=True)
        
        # Refresh View to show "Owned"
        await shop_callback(update, context)

    # --- ALERTS ---
    if action == "shop_poor":
        await query.answer("📉 You are too poor for this!", show_alert=True)
    
    if action == "shop_owned":
        await query.answer("🎒 You already have this in your inventory!", show_alert=True)

# --- SHORTCUT (/buy) ---
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user_exists(update.effective_user)
    
    if not context.args: 
        return await update.message.reply_text("⚠️ <b>Usage:</b> <code>/buy knife</code>", parse_mode=ParseMode.HTML)
    
    item_key = context.args[0].lower()
    item = next((i for i in SHOP_ITEMS if i['id'] == item_key), None)
    
    if not item: 
        return await update.message.reply_text(f"❌ Item <b>{item_key}</b> not found in shop.", parse_mode=ParseMode.HTML)
    
    if user['balance'] < item['price']: 
        return await update.message.reply_text(f"❌ You need <code>{format_money(item['price'])}</code>!", parse_mode=ParseMode.HTML)
    
    if any(i['id'] == item_key for i in user.get('inventory', [])): 
        return await update.message.reply_text("⚠️ You already own this item!", parse_mode=ParseMode.HTML)

    from datetime import datetime
    item_with_time = item.copy()
    item_with_time['bought_at'] = datetime.utcnow()

    users_collection.update_one(
        {"user_id": user['user_id']}, 
        {"$inc": {"balance": -item['price']}, "$push": {"inventory": item_with_time}}
    )
    await update.message.reply_text(f"✅ Bought <b>{item['name']}</b>!", parse_mode=ParseMode.HTML)
