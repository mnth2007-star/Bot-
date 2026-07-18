import telebot
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# جلب الإعدادات من Render
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
DATA_FILE = 'data.json'

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"admins": [ADMIN_ID], "banned_users": [], "materials": {}}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@bot.message_handler(commands=['start'])
def start(message):
    data = load_data()
    if message.chat.id in data["banned_users"]:
        bot.send_message(message.chat.id, "🚫 أنت محظور من استخدام البوت.")
        return
    
    markup = InlineKeyboardMarkup()
    for key, mat in data["materials"].items():
        markup.add(InlineKeyboardButton(text=mat["name"], callback_data=f"view_{key}"))
    
    if message.chat.id in data["admins"]:
        markup.add(InlineKeyboardButton(text="⚙️ لوحة الإدارة", callback_data="admin_panel"))
    
    bot.send_message(message.chat.id, "📚 أهلاً بك! اختر المساق:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    data = load_data()
    uid = call.message.chat.id
    
    if call.data == "admin_panel" and uid in data["admins"]:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="➕ إضافة مساق", callback_data="add_mat"))
        markup.add(InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="ban_user"))
        bot.edit_message_text("⚙️ لوحة التحكم:", uid, call.message.message_id, reply_markup=markup)
        
    elif call.data.startswith("view_"):
        mat_key = call.data.split("_")[1]
        mat = data["materials"].get(mat_key)
        if not mat: return
        markup = InlineKeyboardMarkup()
        for opt, link in mat.get("options", {}).items():
            markup.add(InlineKeyboardButton(text=f"🔗 {opt}", url=link))
        if uid in data["admins"]:
            markup.add(InlineKeyboardButton(text="➕ إضافة قسم", callback_data=f"add_opt_{mat_key}"))
        markup.add(InlineKeyboardButton(text="🔙 رجوع", callback_data="back_main"))
        bot.edit_message_text(f"📋 مساق: {mat['name']}", uid, call.message.message_id, reply_markup=markup)

    elif call.data == "back_main":
        start(call.message)

    elif call.data == "add_mat" and uid in data["admins"]:
        bot.send_message(uid, "أرسل اسم المساق الجديد:")
        user_states[uid] = {"action": "wait_mat"}
    
    elif call.data == "ban_user" and uid in data["admins"]:
        bot.send_message(uid, "أرسل ID المستخدم لحظره:")
        user_states[uid] = {"action": "wait_ban"}

    elif call.data.startswith("add_opt_"):
        mat_key = call.data.split("_")[2]
        bot.send_message(uid, "أرسل اسم القسم (مثلاً: سلايدات، تلخيص):")
        user_states[uid] = {"action": "wait_opt_name", "mat": mat_key}

@bot.message_handler(func=lambda m: m.chat.id in user_states)
def handle_input(m):
    data = load_data()
    uid = m.chat.id
    state = user_states[uid]
    
    if state["action"] == "wait_mat":
        key = str(len(data["materials"]) + 1)
        data["materials"][key] = {"name": m.text, "options": {}}
        bot.send_message(uid, "✅ تم إضافة المساق.")
    elif state["action"] == "wait_ban":
        data["banned_users"].append(int(m.text))
        bot.send_message(uid, "🚫 تم حظر المستخدم.")
    elif state["action"] == "wait_opt_name":
        user_states[uid].update({"action": "wait_opt_link", "name": m.text})
        bot.send_message(uid, "أرسل رابط الملف الآن:")
        return
    elif state["action"] == "wait_opt_link":
        mat_key = state["mat"]
        data["materials"][mat_key]["options"][state["name"]] = m.text
        bot.send_message(uid, "✅ تم إضافة الملف للمساق.")
        
    save_data(data)
    del user_states[uid]

bot.infinity_polling()
