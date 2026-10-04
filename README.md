# Niko 5.0 - Premium Telegram Economy, Game & Chatbot Bot

<p align="center">
  <b>Niko branch is running</b>
</p>

<p align="center">
  <img src="https://telegra.ph/file/5e5480760e412bd402e88.jpg" width="250">
</p>

<h1 align="center">Protected By The Hell Bots Network</h1>

<p align="center">
  <a href="https://t.me/trueNakshu">
    <img src="https://img.shields.io/badge/Owner%20@trueNakshu-purple?style=for-the-badge&logo=telegram" width="200">
  </a>
  <a href="https://github.com/VIP-saksham/bakachatbot">
    <img src="https://img.shields.io/badge/GitHub%20VIP-saksham-black?style=for-the-badge&logo=github" width="200">
  </a>
</p>

---

## About

**Niko 5.0** is an advanced AI-powered Telegram bot combining RPG combat, economy, social systems, and AI chatbot features. Built with **Python, python-telegram-bot v20, Flask, and AI providers (Groq & Gemini)**.

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&pause=900&color=F7006A&width=650&lines=Protected+by+The+Hell+Bots+Network;Sassy+AI+Chatbot+Hinglish;Auto-Responder+with+Watchdog;Groq+%26+Gemini+AI+Providers">
</p>

---

## ✨ Features

### 🔥 AI System
- **AI Chatbot**: Sassy, cute Indian girl (Hinglish) powered by Groq & Gemini
- **Smart Replies**: /status shows system health, API status, and integrity check
- **Sticker Reply**: Reacts to stickers with cute sticker collection
- **Narrator**: AI narrates /kill and /rob battles dynamically
- **Media**: /draw (Anime Art) & /speak (Anime Voice)
- **Memory**: Chatbot maintains conversation history with memory clearing

### ⚔️ RPG & Economy
- **Combat**: Kill users for loot (boosted by weapons)
- **Robbery**: 100% Success Rate (blocked only by armor)
- **Shop**: Buy 60+ items (Weapons, Armor, Flex)
- **Inventory**: Visual inventory with rarity tags and fair play limits
- **Revive**: Auto-revive in 6h or pay to revive instantly

### 💍 Social System
- **Marriage**: Propose to users, couples get 5% tax on transfers
- **Protection**: Shared shields between partners
- **Waifu Gacha**: Collect anime characters by guessing names in groups

### 📊 Administration
- **Sudo Panel**: Owner-only commands for coins, broadcast, updates
- **Broadcast**: Send messages to all users or groups
- **Database**: /cleandb to clean database

### 🎰 Games
- **Dice**: Roll dice for rewards
- **Slots**: Casino-style slot machine
- **Riddle**: AI-generated riddles with auto-answer check
- **Couple**: Matchmaking fun game

---

## 🔧 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| BOT_TOKEN | Your Bot Token from @BotFather | ✅ |
| MONGO_URI | MongoDB Connection String | ❌ |
| OWNER_ID | Your Telegram User ID | ✅ |
| LOGGER_ID | Channel ID for Logs (e.g. -100xxxx) | ✅ |
| GROQ_API_KEY | Groq API Key (For Fast AI) | ❌ |
| GEMINI_API_KEY | Google Gemini API Key | ❌ |
| GIT_PYTHON_REFRESH | Set value to quiet | ✅ |
| PORT | Flask port (default: 5000) | ❌ |

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/VIP-saksham/bakachatbot
cd ryanbaka

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ryan.env.example ryan.env  # If exists, otherwise set your own

# Run the bot
python3 Ryan.py
```

---

## 🚀 Deployment

### VPS (Recommended)

```bash
# Copy ryan.env to your server
cp ryan.env /root/nakshu/ryanbaka/

# Run with start.sh (includes watchdog)
cd /root/nakshu/ryanbaka
nohup bash start.sh > /tmp/start_out.log 2>&1 &

# Health check
curl http://localhost:5000/
```

### Heroku (Alternative)

```bash
# Login to Heroku
heroku login

# Create app
heroku create

# Set config vars
heroku config:set BOT_TOKEN=your_bot_token
heroku config:set MONGO_URI=your_mongo_uri
heroku config:set OWNER_ID=your_telegram_id
heroku config:set LOGGER_ID=-100channel_id
heroku config:set GROQ_API_KEY=your_groq_api_key
heroku config:set GIT_PYTHON_REFRESH=quiet

# Deploy
git push heroku main
```

---

## 📞 Contact & Support

- **Owner**: @trueNakshu
- **GitHub**: [VIP-saksham](https://github.com/VIP-saksham)
- **Telegram Channel**: @TheHellBots
- **Bot**: 🌊 **Niko ✦**
- **Network**: The Hell Bots Network

---

<p align="center">
  <b>🌸 ©️ 2025 Saksham Swaroop (@truenakshu) — All Rights Reserved 🌸</b>
</p>

<p align="center">
  Made with ❤️ by <a href="https://t.me/trueNakshu">@trueNakshu</a>
</p>
