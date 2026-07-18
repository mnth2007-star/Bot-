import telebot, os, sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

# --- إعداد قاعدة البيانات ---
conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS data (key TEXT PRIMARY KEY, value TEXT)')
# وضع قيم ابتدائية إذا كانت القاعدة فارغة
if not c.execute("SELECT * FROM data WHERE key='config'").fetchone():
    c.execute("INSERT INTO data VALUES (?, ?)", ('config', str({"admins": [ADMIN_ID], "managers": [], "banned_users": [], "materials": {}})))
    conn.commit()

def load_data():
    c.execute("SELECT value FROM data WHERE key='config'")
    return eval(c.fetchone()[0])

def save_data(data):
    c.execute("UPDATE data SET value=? WHERE key='config'", (str(data),))
    conn.commit()

# --- دوال المساعدة ---
def is_admin(uid): return uid in load_data()["admins"]
def is_manager(uid): 
    d = load_data()
    return uid in d["admins"] or uid in d["managers"]

# --- البوت ---
@bot.message_handler(commands=['start'])
def start(m):
    data = load_data()
    if m.chat.id in data["banned_users"]: return
    markup = InlineKeyboardMarkup()
    for k, v in data["materials"].items(): markup.add(InlineKeyboardButton(v["name"], callback_data=f"view_{k}"))
    if is_admin(m.chat.id): markup.add(InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel"))
    bot.send_message(m.chat.id, "📚 اختر المساق:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    data = load_data()
    uid = call.message.chat.id
    
    if call.data == "admin_panel" and is_admin(uid):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ إضافة مساق", callback_data="add_mat"), InlineKeyboardButton("🗑 حذف مساق", callback_data="del_mat"))
        bot.edit_message_text("⚙️ لوحة التحكم:", uid, call.message.message_id, reply_markup=markup)
    
    elif call.data == "add_mat" and is_admin(uid):
        bot.send_message(uid, "أرسل اسم المساق:")
        user_states[uid] = {"action": "wait_mat"}
        
    elif call.data.startswith("view_"):
        mat_key = call.data.split("_")[1]
        mat = data["materials"][mat_key]
        markup = InlineKeyboardMarkup()
        for opt, link in mat.get("options", {}).items(): markup.add(InlineKeyboardButton(opt, url=link))
        bot.edit_message_text(f"مساق: {mat['name']}", uid, call.message.message_id, reply_markup=markup)

@bot.message_handler(func=lambda m: m.chat.id in user_states)
def handle_input(m):
    data = load_data()
    state = user_states[m.chat.id]
    if state["action"] == "wait_mat":
        key = str(len(data["materials"]) + 1)
        data["materials"][key] = {"name": m.text, "options": {}}
        save_data(data)
        bot.send_message(m.chat.id, "✅ تم إضافة المساق بنجاح.")
        del user_states[m.chat.id]

# --- تشغيل Flask للبقاء نشطاً ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

bot.remove_webhook()
bot.infinity_polling()
