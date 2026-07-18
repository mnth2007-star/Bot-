import telebot, json, os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
DATA_FILE = 'data.json'
bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

def load_data():
    if not os.path.exists(DATA_FILE): return {"admins": [ADMIN_ID], "managers": [], "banned_users": [], "materials": {}}
    with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

def is_admin(uid): return uid in load_data()["admins"]
def is_manager(uid): 
    d = load_data()
    return uid in d["admins"] or uid in d["managers"]

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
        markup.add(InlineKeyboardButton("👤 تعيين مساعد", callback_data="add_mgr"), InlineKeyboardButton("🚫 طرد مساعد", callback_data="del_mgr"))
        bot.edit_message_text("⚙️ لوحة التحكم:", uid, call.message.message_id, reply_markup=markup)
    
    elif call.data == "add_mat" and is_admin(uid):
        bot.send_message(uid, "أرسل اسم المساق:")
        user_states[uid] = {"action": "wait_mat"}
        
    elif call.data == "del_mat" and is_admin(uid):
        markup = InlineKeyboardMarkup()
        for k, v in data["materials"].items(): markup.add(InlineKeyboardButton(f"❌ {v['name']}", callback_data=f"confirm_del_{k}"))
        bot.edit_message_text("اختر للحذف:", uid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("confirm_del_"):
        del data["materials"][call.data.split("_")[2]]
        save_data(data)
        bot.answer_callback_query(call.id, "تم الحذف!")
        
    elif call.data == "add_mgr" and is_admin(uid):
        bot.send_message(uid, "أرسل ID المساعد:")
        user_states[uid] = {"action": "wait_mgr"}
        
    elif call.data.startswith("view_"):
        mat_key = call.data.split("_")[1]
        mat = data["materials"][mat_key]
        markup = InlineKeyboardMarkup()
        for opt, link in mat.get("options", {}).items(): markup.add(InlineKeyboardButton(opt, url=link))
        if is_manager(uid): markup.add(InlineKeyboardButton("➕ إضافة ملف", callback_data=f"add_opt_{mat_key}"))
        bot.edit_message_text(f"مساق: {mat['name']}", uid, call.message.message_id, reply_markup=markup)

    elif call.data.startswith("add_opt_") and is_manager(uid):
        user_states[uid] = {"action": "wait_opt_name", "mat": call.data.split("_")[2]}
        bot.send_message(uid, "أرسل اسم الملف:")

@bot.message_handler(func=lambda m: m.chat.id in user_states)
def handle_input(m):
    data = load_data()
    state = user_states[m.chat.id]
    if state["action"] == "wait_mat":
        key = str(len(data["materials"]) + 1)
        data["materials"][key] = {"name": m.text, "options": {}}
    elif state["action"] == "wait_mgr":
        data["managers"].append(int(m.text))
    elif state["action"] == "wait_opt_name":
        user_states[m.chat.id].update({"action": "wait_opt_link", "name": m.text})
        bot.send_message(m.chat.id, "أرسل الرابط:")
        return
    elif state["action"] == "wait_opt_link":
        data["materials"][state["mat"]]["options"][state["name"]] = m.text
    save_data(data)
    bot.send_message(m.chat.id, "✅ تم التنفيذ.")
    del user_states[m.chat.id]

bot.infinity_polling()
