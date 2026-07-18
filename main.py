import telebot
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# التوكن والـ ID الخاص بك
BOT_TOKEN = "8887684391:AAE99eNdu-H2BlPIjDLPy6AXtTK4JlRkkgI"
ADMIN_ID = 8780214576

# تعريف البوت
bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

# دالة قراءة البيانات
def load_data():
    if not os.path.exists('data.json'):
        return {"allowed_users": [ADMIN_ID], "admins": [ADMIN_ID], "materials": {}, "users_profile": {}}
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        # تأكيد وجود القوائم الأساسية لتفادي الأخطاء
        if "admins" not in data: data["admins"] = [ADMIN_ID]
        if "allowed_users" not in data: data["allowed_users"] = [ADMIN_ID]
        if "materials" not in data: data["materials"] = {}
        if "users_profile" not in data: data["users_profile"] = {}
        
        if ADMIN_ID not in data["admins"]: data["admins"].append(ADMIN_ID)
        if ADMIN_ID not in data["allowed_users"]: data["allowed_users"].append(ADMIN_ID)
        return data

# دالة حفظ البيانات
def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# لوحة المفاتيح الرئيسية لمشاهدة المواد
def get_main_keyboard(user_id, data):
    markup = InlineKeyboardMarkup()
    for key, mat in data["materials"].items():
        markup.add(InlineKeyboardButton(text=mat["name"], callback_data=f"view_{key}"))

    if user_id in data["admins"]:
        markup.add(InlineKeyboardButton(text="⚙️ لوحة الإدارة والتحكم", callback_data="admin_panel"))
    return markup

# أمر التشغيل /start
@bot.message_handler(commands=['start'])
def start_cmd(message):
    data = load_data()
    user_id = message.chat.id

    if user_id not in data["allowed_users"] and user_id not in data["admins"]:
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_phone = KeyboardButton(text="مشاركة رقم الجوال للتفعيل 📱", request_contact=True)
        markup.add(button_phone)
        bot.send_message(user_id, "📚 أهلاً بك في بوت المساقات الهندسية.\n\nيرجى مشاركة رقم الجوال للتفعيل:", reply_markup=markup)
        return

    bot.send_message(user_id, "📚 أهلاً بك. اختر المساق المكلّف به:", reply_markup=get_main_keyboard(user_id, data))

# استقبال رقم الجوال
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    data = load_data()
    user_id = message.chat.id
    
    if message.contact is not None:
        if message.contact.user_id == user_id:
            phone_number = message.contact.phone_number
            user_name = message.from_user.first_name if message.from_user.first_name else "طالب"
            clean_phone = phone_number.replace("+", "").strip()
            
            data["users_profile"][str(user_id)] = {"name": user_name, "phone": clean_phone}
            if user_id not in data["allowed_users"]:
                data["allowed_users"].append(user_id)
                
            save_data(data)
            bot.send_message(user_id, f"✅ تم تفعيل حسابك يا مهندس {user_name}!", reply_markup=ReplyKeyboardRemove())
            bot.send_message(user_id, "اختر المساق:", reply_markup=get_main_keyboard(user_id, data))
        else:
            bot.send_message(user_id, "❌ خطأ في التحقق.")

# التعامل مع الضغطات والمدخلات (بقية الكود كما هو)
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    # (تم الاحتفاظ بباقي المنطق كما في كودك الأصلي)
    pass

@bot.message_handler(func=lambda message: message.chat.id in user_states)
def handle_inputs(message):
    # (تم الاحتفاظ بباقي المنطق كما في كودك الأصلي)
    pass

bot.infinity_polling()
