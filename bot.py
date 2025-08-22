import telebot
from telebot import types
import os, json, re, time
from requests.exceptions import ConnectionError, ReadTimeout

# ---------------- BOT CONFIG ----------------
BOT_TOKEN = "8477965075:AAG4tbCD-n6S8vWzdA6ejRang_p1F-PzADs"      # <-- yahan naya token dalo
ADMIN_ID = 6444071433                    # <-- yahan apna Telegram numeric ID
QR_PATH = "/data/data/com.termux/files/home/storage/downloads/upi_qr.jpg"
WELCOME_IMG = "/data/data/com.termux/files/home/storage/downloads/welcome.jpg"
GAMEID_IMG = "/data/data/com.termux/files/home/storage/downloads/game_id.jpg"
IGN_IMG = "/data/data/com.termux/files/home/storage/downloads/in_game_name.jpg"
HISTORY_FILE = "purchases.json"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------------- UC PACKS ----------------
UC_PACKS = {
    "60": "💎 60 UC - ₹40",
    "1900": "💎 1900 UC - ₹950",
    "3850": "💎 3850 UC - ₹1540",
    "8100": "💎 8100 UC - ₹2430",
}

# state during one order flow
user_data = {}

# ---------------- PERSISTENT HISTORY ----------------
def load_history():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except:
        return {}

def save_history():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(purchase_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        try:
            bot.send_message(ADMIN_ID, f"⚠️ Could not save purchases.json: {e}")
        except:
            pass

purchase_history = load_history()

def has_bought_60(user_id: int):
    return UC_PACKS["60"] in purchase_history.get(str(user_id), [])

def add_purchase(user_id: int, pack_text: str):
    uid = str(user_id)
    if uid not in purchase_history:
        purchase_history[uid] = []
    purchase_history[uid].append(pack_text)
    save_history()

# ---------------- UI HELPERS ----------------
def packs_inline_keyboard(user_id: int):
    kb = types.InlineKeyboardMarkup()
    for key, val in UC_PACKS.items():
        if key == "60" and has_bought_60(user_id):
            continue
        kb.add(types.InlineKeyboardButton(val, callback_data=f"pack_{key}"))
    return kb

def send_qr(chat_id: int):
    if os.path.exists(QR_PATH):
        with open(QR_PATH, "rb") as photo:
            bot.send_photo(
                chat_id,
                photo,
                caption="📲 Scan & Pay using UPI QR\n\nAfter payment, send *screenshot* here.\n\n⏳ UC delivery may take 5–10 minutes.",
                parse_mode="Markdown",
            )
    else:
        bot.send_message(chat_id, "⚠️ QR code not found. Contact @UC_Bank_admin")

# ---------------- COMMANDS ----------------
@bot.message_handler(commands=["start", "help"])
def start(message):
    user_id = message.chat.id
    if os.path.exists(WELCOME_IMG):
        with open(WELCOME_IMG, "rb") as photo:
            bot.send_photo(user_id, photo, caption="👋 *Welcome to UC BANK Store*\n\nPlease accept our Terms & Conditions before proceeding:", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "👋 *Welcome to UC BANK Store*\n\nPlease accept our Terms & Conditions before proceeding:", parse_mode="Markdown")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Accept Terms & Conditions", callback_data="accept_tnc"))
    bot.send_message(user_id, 
        "📜 Terms & Conditions – UC BANK Store\n\n"
        "1. Correct Details: Customers must provide the correct Game ID (10 digits) and In-Game Name. We are not responsible for delays or failed deliveries caused by incorrect details.\n\n"
        "2. Delivery Time: UC will be delivered within 5–10 minutes after payment confirmation. In rare cases, delivery may take a little longer.\n\n"
        "3. Payment Proof: A valid payment screenshot must be submitted for every order. Orders without proof of payment will not be processed.\n\n"
        "4. Refund Policy: If UC is not delivered due to a technical or processing issue, a full refund will be provided. Refunds are not available for incorrect details provided by the customer.\n\n",
        reply_markup=kb
    )

@bot.message_handler(commands=["status"])
def status(message):
    user_id = message.chat.id
    bought = purchase_history.get(str(user_id), [])

    msg = "🧾 *Your Purchase History*\n\n"
    if bought:
        msg += "\n".join([f"• {b}" for b in bought])
    else:
        msg += "❌ No purchases yet."

    bot.send_message(user_id, msg, parse_mode="Markdown")

# ---------------- ADMIN COMMAND: MARK DELIVERED ----------------
@bot.message_handler(commands=["delivered"])
def mark_delivered(message):
    if message.from_user.id != ADMIN_ID:
        return  # only admin can use
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(ADMIN_ID, "⚠️ Usage: /delivered <user_id>")
            return
        user_id = int(parts[1])
        bot.send_message(user_id, "✅ Your UC has been delivered successfully! Enjoy your game 🎮")
        bot.send_message(ADMIN_ID, f"📢 Notified user {user_id} about delivery ✅")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"⚠️ Error: {e}")

# ---------------- CALLBACK HANDLERS ----------------
@bot.callback_query_handler(func=lambda call: call.data == "accept_tnc")
def accepted_terms(call):
    bot.edit_message_text(
        "✅ Terms accepted. Now choose your UC pack:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=packs_inline_keyboard(call.message.chat.id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("pack_"))
def pack_selected(call):
    user_id = call.message.chat.id
    pack_key = call.data.split("_")[1]
    pack_text = UC_PACKS[pack_key]

    if pack_key == "60" and has_bought_60(user_id):
        bot.answer_callback_query(call.id, "You can only buy 60 UC pack once.", show_alert=True)
        return

    user_data[user_id] = {"pack": pack_text}

    if os.path.exists(GAMEID_IMG):
        with open(GAMEID_IMG, "rb") as photo:
            bot.send_photo(user_id, photo, caption="🆔 Please enter your *10-digit Game ID*:", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "🆔 Please enter your *10-digit Game ID*:", parse_mode="Markdown")

# ---------------- CONVERSATION FLOW ----------------
@bot.message_handler(func=lambda m: m.chat.id in user_data and "game_id" not in user_data[m.chat.id])
def get_game_id(message):
    user_id = message.chat.id
    gid = message.text.strip()
    if not re.fullmatch(r"\d{10}", gid):
        bot.send_message(user_id, "⚠️ Invalid Game ID. It must be exactly 10 digits.")
        return

    user_data[user_id]["game_id"] = gid
    bot.send_message(user_id, "✅ Game ID saved!")

    if os.path.exists(IGN_IMG):
        with open(IGN_IMG, "rb") as photo:
            bot.send_photo(user_id, photo, caption="🎮 Now enter your *In-Game Name*:", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "🎮 Now enter your *In-Game Name*:", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.chat.id in user_data and "game_name" not in user_data[m.chat.id])
def get_game_name(message):
    user_id = message.chat.id
    user_data[user_id]["game_name"] = message.text.strip()
    bot.send_message(user_id, "✅ IGN saved! Proceed to payment:")
    send_qr(user_id)

# ---------------- PAYMENT HANDLER ----------------
@bot.message_handler(content_types=["photo"])
def handle_payment(message):
    user_id = message.chat.id
    if user_id not in user_data:
        bot.send_message(user_id, "ℹ️ Please /start and select a pack first.")
        return

    order = user_data[user_id]
    selected_pack = order.get("pack")

    bot.send_message(user_id, "✅ Payment screenshot received! Your order is being processed. ⏳\n\n🙏 Thank you for shopping with UC BANK Store.\nUC delivery usually takes 5–10 minutes.")

    username = f"@{message.from_user.username}" if message.from_user.username else "❌ No username"
    profile_link = f"[Profile Link](tg://user?id={user_id})"

    caption = (
        "📢 *New Order Received*\n\n"
        f"👤 Customer: {message.from_user.first_name or ''}\n"
        f"💬 Telegram User ID: `{user_id}`\n"
        f"🔗 Username: {username}\n"
        f"🌐 {profile_link}\n\n"
        f"🆔 Game ID: {order.get('game_id','')}\n"
        f"🎮 Game Name: {order.get('game_name','')}\n"
        f"💎 Pack: {selected_pack}\n"
    )

    # ✅ Delivered button
    kb_admin = types.InlineKeyboardMarkup()
    kb_admin.add(types.InlineKeyboardButton("✅ Mark Delivered", callback_data=f"deliver_{user_id}"))

    try:
        bot.send_photo(
            ADMIN_ID,
            message.photo[-1].file_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=kb_admin
        )
    except Exception as e:
        bot.send_message(ADMIN_ID, f"⚠️ Could not forward screenshot: {e}")

    if selected_pack == UC_PACKS["60"]:
        add_purchase(user_id, selected_pack)

    del user_data[user_id]

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("/start")
    bot.send_message(user_id, "✅ Order received! You can buy another pack if you want:", reply_markup=kb)

# ---------------- ADMIN: DELIVER BUTTON ----------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("deliver_"))
def deliver_order(call):
    if call.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(call.data.split("_")[1])
        bot.send_message(user_id, "✅ Your UC has been delivered successfully! Enjoy your game 🎮")
        bot.answer_callback_query(call.id, "✅ Customer notified about delivery")
        bot.send_message(ADMIN_ID, f"📢 Delivered confirmed for user {user_id}")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"⚠️ Delivery error: {e}")

# ---------------- FALLBACK ----------------
@bot.message_handler(content_types=["text"])
def fallback(message):
    if message.text.startswith("/"):
        return
    bot.send_message(message.chat.id, "ℹ️ Please /start to begin.")

# ---------------- RUN (24/7 MODE) ----------------
print("🤖 UC BANK Bot running...")
bot.remove_webhook()  # safety, long-polling ke liye

while True:
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=20)
    except (ConnectionError, ReadTimeout) as e:
        print(f"⚠️ Network error: {e}. Retrying in 10s...")
        time.sleep(10)
        continue
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}. Restarting in 10s...")
        time.sleep(10)
        continue
