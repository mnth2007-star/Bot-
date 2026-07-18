import telebot, os, sqlite3, json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# تحميل الإعدادات
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

# --- إعداد قاعدة البيانات ---
conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS data (key TEXT PRIMARY KEY, value TEXT)')
if not c.execute("SELECT * FROM data WHERE key='config'").fetchone():
    initial_data = {"admins": [ADMIN_ID], "materials": {}}
    c.execute("INSERT INTO data VALUES (?, ?)", ('config', json.dumps(initial_data)))
    conn.commit()

def load_data():
    c.execute("SELECT value FROM data WHERE key='config'")
    return json.loads(c.fetchone()[0])

def save_data(data):
    c.execute("UPDATE data SET value=? WHERE key='config'", (json.dumps(data),))
    conn.commit()

def is_admin(uid): return uid in load_data()["admins"]

# --- البوت ---
@bot.message_handler(commands=['start'])
def start(m):
    data = load_data()
    markup = InlineKeyboardMarkup()
    for k, v in data["materials"].items(): 
        markup.add(InlineKeyboardButton(v["name"], callback_data=f"view_{k}"))
    if is_admin(m.chat.id): 
        markup.add(InlineKeyboardButton("⚙️ لوحة الإدارة", callback_data="admin_panel"))
    bot.send_message(m.chat.id, "📚 اختر المساق:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    data = load_data()
    uid = call.message.chat.id
    
    if call.data == "admin_panel" and is_admin(uid):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ إضافة مساق", callback_data="add_mat"))
        markup.add(InlineKeyboardButton("🗑 حذف مساق", callback_data="del_mat_list"))
        bot.edit_message_text("⚙️ لوحة التحكم:", uid, call.message.message_id, reply_markup=markup)
    
    elif call.data == "add_mat" and is_admin(uid):
        bot.send_message(uid, "أرسل اسم المساق:")
        user_states[uid] = {"action": "wait_mat"}
        
    elif call.data == "del_mat_list" and is_admin(uid):
        markup = InlineKeyboardMarkup()
        for k, v in data["materials"].items():
            markup.add(InlineKeyboardButton(f"❌ {v['name']}", callback_data=f"del_{k}"))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
        bot.edit_message_text("اختر المساق للحذف:", uid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("del_") and is_admin(uid):
        mat_key = call.data.split("_")[1]
        del data["materials"][mat_key]
        save_data(data)
        bot.answer_callback_query(call.id, "✅ تم حذف المساق")
        # العودة للوحة الإدارة
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ إضافة مساق", callback_data="add_mat"))
        markup.add(InlineKeyboardButton("🗑 حذف مساق", callback_data="del_mat_list"))
        bot.edit_message_text("⚙️ لوحة التحكم:", uid, call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("view_"):
        mat_key = call.data.split("_")[1]
        mat = data["materials"][mat_key]
        markup = InlineKeyboardMarkup()
        for opt_name, link in mat.get("options", {}).items():
            markup.add(InlineKeyboardButton(f"📂 {opt_name}", url=link))
        bot.edit_message_text(f"📚 مساق: {mat['name']}\nاختر الملف:", uid, call.message.message_id, reply_markup=markup)

@bot.message_handler(func=lambda m: m.chat.id in user_states)
def handle_input(m):
    data = load_data()
    uid = m.chat.id
    state = user_states[uid]

    if state["action"] == "wait_mat":
        key = str(len(data["materials"]) + 1)
        data["materials"][key] = {"name": m.text, "options": {}}
        save_data(data)
        user_states[uid] = {"action": "wait_opt_name", "mat_key": key}
        bot.send_message(uid, f"✅ تم إضافة مساق '{m.text}'.\nأرسل الآن اسم الملف (مثلاً: سلايدات):")

    elif state["action"] == "wait_opt_name":
        user_states[uid].update({"opt_name": m.text, "action": "wait_opt_link"})
        bot.send_message(uid, "🔗 أرسل الرابط:")

    elif state["action"] == "wait_opt_link":
        mat_key = state["mat_key"]
        data["materials"][mat_key]["options"][state["opt_name"]] = m.text
        save_data(data)
        bot.send_message(uid, "✅ تم إضافة الملف بنجاح!")
        del user_states[uid]

# --- تشغيل Flask ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive"
Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()

bot.remove_webhook()
bot.infinity_polling()
