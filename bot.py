import os
import json
import random
import time
from datetime import datetime, timedelta
import requests

from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup,
    InlineKeyboardButton, WebAppInfo, InputFile
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler,
    filters
)

# ========== CONFIG ==========
TOKEN = os.environ.get("8496346749:AAHSxbY07uT1Yfj8qdc9jaSl_HLeJOhw3Xo")  # ⚠️ теперь токен берём из переменной окружения
SITE_LINK = "https://reward-solana.icu"

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "data.json")
BANNER_PATH = "upscaled_image.webp"

ROULETTE_MIN = 0.1
ROULETTE_MAX = 0.5
ROULETTE_COOLDOWN_DAYS = 7
ROULETTE_REQUIRED_REFERRALS = 5

CHANNEL_URL = "https://t.me/solana"
SUPPORT_USERNAME = "SolanaSupp"  # @SolanaSupp
DISCORD_URL = "https://discord.com/invite/solana"
WEBSITE_URL = "https://solana.com"

PRIVACY_URL = "https://solana.com/privacy-policy"
TERMS_URL = "https://solana.com/tos"
# ===========================


# ----- storage -----
def ensure_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": {}, "referred_by": {}}, f, ensure_ascii=False, indent=2)


def load_data():
    ensure_storage()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(d):
    ensure_storage()
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def get_user(d, user_id, first_name=None):
    user_id = str(user_id)
    if user_id not in d["users"]:
        d["users"][user_id] = {
            "id": int(user_id),
            "first_name": first_name or "",
            "reg_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "balance": 0.0,
            "total_airdrop": 0.0,
            "total_roulette": 0.0,
            "invited_count": 0,
            "referrals": [],
            "last_spin": None,
            "last_fact_idx": -1
        }
        save_data(d)
    return d["users"][user_id]


def add_referral(d, referrer_id, new_user_id):
    referrer_id = str(referrer_id)
    new_user_id = str(new_user_id)

    if referrer_id == new_user_id:
        return
    if new_user_id in d.get("referred_by", {}):
        return

    d.setdefault("referred_by", {})[new_user_id] = referrer_id

    ref_user = d["users"].get(referrer_id)
    if ref_user:
        if new_user_id not in ref_user["referrals"]:
            ref_user["referrals"].append(new_user_id)
            ref_user["invited_count"] = len(ref_user["referrals"])
    save_data(d)


# ----- keyboards -----
def main_menu_kb() -> ReplyKeyboardMarkup:
    top_row = [KeyboardButton(text="Get Solana 🎯", web_app=WebAppInfo(url=SITE_LINK))]
    bottom_rows = [
        [KeyboardButton("My Profile 👤"), KeyboardButton("Referral System 🤝")],
        [KeyboardButton("Solana Price 📈"), KeyboardButton("Roulette 🎰")],
        [KeyboardButton("Policy & Rules 📜"), KeyboardButton("Our Contacts 📞")],
    ]
    return ReplyKeyboardMarkup([top_row] + bottom_rows, resize_keyboard=True)


def back_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[KeyboardButton("⬅️ Back")]], resize_keyboard=True)


# ----- helpers -----
SOLANA_FACTS = [
    "⚡ Solana processes thousands of TPS with low fees.",
    "🌱 Energy efficient: one of the most eco-friendly major L1s.",
    "🧩 Built with Rust, C, and C++ support for high-perf dApps.",
    "🔗 Parallelized execution via Sealevel for massive throughput.",
    "🧭 Timekeeping via Proof-of-History helps speed & ordering."
]


def next_fact(user):
    idx = (user.get("last_fact_idx", -1) + 1) % len(SOLANA_FACTS)
    user["last_fact_idx"] = idx
    return SOLANA_FACTS[idx]


async def send_welcome_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "🚀 Welcome aboard the Solana Airdrop Mission! 🌊\n\n"
        "🎉 Your chance to grab FREE $SOL has just begun.\n"
        "🔐 Secure, fast & effortless — complete simple steps and see your balance grow.\n\n"
        "📢 Don’t miss updates — join the official channel:\n"
        "🔗 https://t.me/solana\n\n"
        "🛟 Questions? Our support team is here:\n"
        "🔗 https://t.me/SolanaSupp\n\n"
        "⚡️ Hit Get Solana 🎯 below to start collecting your Solana rewards!"
    )
    if os.path.exists(BANNER_PATH):
        with open(BANNER_PATH, "rb") as f:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=InputFile(f),
                caption=caption,
                reply_markup=main_menu_kb()
            )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=caption,
            reply_markup=main_menu_kb()
        )


# ----- handlers -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    user = get_user(d, update.effective_user.id, update.effective_user.first_name)

    if context.args:
        arg = context.args[0]
        if arg.startswith("ref"):
            try:
                ref_id = int(arg.replace("ref", "").strip())
                if str(update.effective_user.id) not in d.get("referred_by", {}):
                    add_referral(d, ref_id, update.effective_user.id)
            except Exception:
                pass

    await send_welcome_banner(update, context)


async def on_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    user = get_user(d, update.effective_user.id, update.effective_user.first_name)
    text = (
        "👤 My Profile\n\n"
        f"ID: {user['id']}\n"
        f"Registration: {user['reg_date']}\n"
        f"Balance: {user['balance']:.4f} SOL\n"
        f"Total Airdrops: {user['total_airdrop']:.4f} SOL\n"
        f"Total Roulette: {user['total_roulette']:.4f} SOL"
    )
    await update.message.reply_text(text, reply_markup=back_kb())


async def on_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    user = get_user(d, update.effective_user.id, update.effective_user.first_name)
    bot_user = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_user.username}?start=ref{user['id']}"
    text = (
        "🎉 Airdrop Referral Program Alert! 🎉\n\n"
        "Invite your friends to join our exciting Solana Airdrop event! 🌟 Refer 15 friends and unlock an extra bonus – your airdrop amount will be doubled! 🚀\n\n"
        "How to participate:\n"
        "1. Share your unique referral link with your friends. 🌐\n"
        "2. Ensure 15 of them sign up using your link. 🤝\n"
        "3. Get your Solana Airdrop amount doubled and enjoy your extra rewards! 💰\n\n"
        "Don’t miss this amazing opportunity to boost your earnings! Start referring now and watch your rewards grow! 📈\n\n"
        f"Your referral link is: {ref_link}\n"
        f"Total invited: {user['invited_count']}"
    )
    await update.message.reply_text(text, reply_markup=back_kb())


async def on_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    user = get_user(d, update.effective_user.id, update.effective_user.first_name)

    price_text = "❌ Failed to fetch SOL price."
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "solana", "vs_currencies": "usd"},
            timeout=10
        )
        if r.ok:
            usd = r.json().get("solana", {}).get("usd")
            if usd is not None:
                price_text = f"💰 The current rate of Solana in USD — {usd}$"
    except Exception:
        pass

    fact = next_fact(user)
    save_data(d)

    msg = f"{price_text}\n\n💡 {fact}"
    await update.message.reply_text(msg, reply_markup=back_kb())


async def on_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Telegram", url=CHANNEL_URL)],
        [InlineKeyboardButton("Discord", url=DISCORD_URL)],
        [InlineKeyboardButton("Website", url=WEBSITE_URL)],
        [InlineKeyboardButton("Telegram Support", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ])
    await update.message.reply_text("📣 Official Solana Contacts:", reply_markup=kb)
    await update.message.reply_text("Press Back to return.", reply_markup=back_kb())


async def on_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Privacy Policy", url=PRIVACY_URL)],
        [InlineKeyboardButton("Terms of Service", url=TERMS_URL)],
    ])
    await update.message.reply_text("📜 Policy & Rules", reply_markup=kb)
    await update.message.reply_text("Press Back to return.", reply_markup=back_kb())


def can_play_roulette(user) -> (bool, str):
    if user.get("invited_count", 0) < ROULETTE_REQUIRED_REFERRALS:
        need = ROULETTE_REQUIRED_REFERRALS - user.get("invited_count", 0)
        return False, f"❌ You need {need} more referrals to play Roulette."
    last = user.get("last_spin")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if datetime.utcnow() < last_dt + timedelta(days=ROULETTE_COOLDOWN_DAYS):
                left = (last_dt + timedelta(days=ROULETTE_COOLDOWN_DAYS)) - datetime.utcnow()
                days = left.days
                hours = left.seconds // 3600
                return False, f"⏳ Try again in ~{days}d {hours}h."
        except Exception:
            pass
    return True, ""


async def on_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    user = get_user(d, update.effective_user.id, update.effective_user.first_name)
    ok, reason = can_play_roulette(user)
    if not ok:
        await update.message.reply_text(reason, reply_markup=back_kb())
        return

    msg = await update.message.reply_text("🎰 Spinning the roulette...", reply_markup=back_kb())
    time.sleep(1.2)

    prize = round(random.uniform(ROULETTE_MIN, ROULETTE_MAX), 3)
    user["balance"] += prize
    user["total_roulette"] += prize
    user["last_spin"] = datetime.utcnow().isoformat()
    save_data(d)

    await msg.reply_text(
        f"🎉 Congrats! You won {prize} SOL!\nNew balance: {user['balance']:.4f} SOL",
        reply_markup=back_kb()
    )


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    if txt.startswith("Get Solana"):
        await update.message.reply_text(f"Open WebApp: {SITE_LINK}", reply_markup=main_menu_kb())
    elif txt == "⬅️ Back":
        await update.message.reply_text("🏠 Main Menu", reply_markup=main_menu_kb())
    elif txt.startswith("My Profile"):
        await on_profile(update, context)
    elif "Referral" in txt:
        await on_referrals(update, context)
    elif "Solana Price" in txt:
        await on_price(update, context)
    elif "Roulette" in txt:
        await on_roulette(update, context)
    elif "Policy" in txt:
        await on_policy(update, context)
    elif "Contacts" in txt:
        await on_contacts(update, context)
    else:
        await update.message.reply_text("Choose an option:", reply_markup=main_menu_kb())


def build_app():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    return app


# ====== ЗАМЕНА long polling на Flask + webhook ======
from flask import Flask, request
import asyncio

flask_app = Flask(__name__)
tg_app = None


@flask_app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200


@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    global tg_app
    if tg_app is None:
        return "App not ready", 503
    data = request.get_json(force=True)
    update = Update.de_json(data, tg_app.bot)
    asyncio.get_event_loop().create_task(tg_app.process_update(update))
    return "OK", 200


if __name__ == "__main__":
    ensure_storage()
    tg_app = build_app()

    public_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if public_url and not public_url.startswith("http"):
        public_url = "https://" + public_url
    if public_url:
        webhook_url = f"{public_url}/{TOKEN}"
        tg_app.bot.delete_webhook(drop_pending_updates=True)
        tg_app.bot.set_webhook(url=webhook_url, allowed_updates=["message", "callback_query"])

    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port, debug=False)
