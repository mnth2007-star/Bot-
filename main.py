import telebot
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ضغ التوكن والـ ID الخاص بك هنا
BOT_TOKEN = '8887684391:AAFDYqkIPq4fQX9y1QvHmBpq0R537DAtyUc'

ADMIN_ID = 8780214576  # الـ ID الشخصي الخاص بك (المالك الأساسي)

bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

# دالة قراءة البيانات
def load_data():
    if not os.path.exists('data.json'):
        return {"allowed_users": [ADMIN_ID], "admins": [ADMIN_ID], "materials": {}}
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        # تأكيد وجود القوائم الأساسية لتفادي الأخطاء
        if "admins" not in data: data["admins"] = [ADMIN_ID]
        if "allowed_users" not in data: data["allowed_users"] = [ADMIN_ID]
        if ADMIN_ID not in data["admins"]: data["admins"].append(ADMIN_ID)
        if ADMIN_ID not in data["allowed_users"]: data["allowed_users"].append(ADMIN_ID)
        return data

# دالة حفظ البيانات
def save_data(data):
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# لوحة المفاتيح الرئيسية
def get_main_keyboard(user_id, data):
    markup = InlineKeyboardMarkup()
    # عرض المساقات للجميع
    for key, mat in data["materials"].items():
        markup.add(InlineKeyboardButton(text=mat["name"], callback_data=f"view_{key}"))

    # إذا كان المستخدم أدمن (مشرف)، تظهر له خيارات التحكم
    if user_id in data["admins"]:
        markup.add(InlineKeyboardButton(text="⚙️ لوحة الإدارة والتحكم", callback_data="admin_panel"))
    return markup

# أمر التشغيل /start
@bot.message_handler(commands=['start'])
def start_cmd(message):
    data = load_data()
    user_id = message.chat.id

    if user_id not in data["allowed_users"] and user_id not in data["admins"]:
        bot.send_message(user_id, f"❌ عذراً، ليس لديك صلاحية لاستخدام البوت.\nأرسل هذا الرقم للمشرف لتفعيل حسابك: `{user_id}`", parse_mode="Markdown")
        return

    bot.send_message(user_id, "📚 أهلاً بك في بوت المساقات الهندسية المطور. اختر المساق المكلّف به:", 
                     reply_markup=get_main_keyboard(user_id, data))

# التعامل مع الضغطات
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = load_data()
    user_id = call.message.chat.id
    message_id = call.message.message_id

    # 1. استعراض مساق
    if call.data.startswith("view_"):
        mat_key = call.data.split("_")[1]
        mat = data["materials"].get(mat_key)
        if mat:
            markup = InlineKeyboardMarkup()
            # عرض الخيارات المضافة داخل المساق تلقائياً (سلايدات، تلخيص، إلخ)
            for option_name, link in mat.get("options", {}).items():
                markup.add(InlineKeyboardButton(text=f"🔗 {option_name}", url=link))

            # إذا كان أدمن، يظهر له زر إضافة خيار جديد داخل هذا المساق
            if user_id in data["admins"]:
                markup.add(InlineKeyboardButton(text="➕ إضافة قسم جديد داخل المساق", callback_data=f"add_opt_{mat_key}"))

            markup.add(InlineKeyboardButton(text="🔙 العودة للمساقات", callback_data="back_main"))
            bot.edit_message_text(chat_id=user_id, message_id=message_id, text=f"📋 مساق: {mat['name']}\nالخيارات المتاحة لطلاب الهندسة:", reply_markup=markup)

    # 2. العودة للقائمة الرئيسية
    elif call.data == "back_main":
        bot.edit_message_text(chat_id=user_id, message_id=message_id, text="اختر المساق:", reply_markup=get_main_keyboard(user_id, data))

    # 3. فتح لوحة الإدارة والتحكم
    elif call.data == "admin_panel" and user_id in data["admins"]:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="➕ إضافة مساق جديد", callback_data="manage_add_mat"))
        markup.add(InlineKeyboardButton(text="👤 إضافة طالب (تصفح فقط)", callback_data="manage_add_student"))
        # خيار إضافة أدمن جديد (متاح فقط لك كأدمن رئيسي للأمان، أو لكل المشرفين حسب رغبتك)
        if user_id == ADMIN_ID:
            markup.add(InlineKeyboardButton(text="👑 تعيين أدمن جديد (مشرف)", callback_data="manage_add_admin"))
        markup.add(InlineKeyboardButton(text="🔙 خروج", callback_data="back_main"))
        bot.edit_message_text(chat_id=user_id, message_id=message_id, text="⚙️ لوحة تحكم المشرفين. اختر ماذا تريد أن تفعل:", reply_markup=markup)

    # 4. طلب إضافة طالب عادي
    elif call.data == "manage_add_student" and user_id in data["admins"]:
        bot.send_message(user_id, "👤 من فضلك أرسل الـ ID الخاص بالطالب لإعطائه صلاحية تصفح:")
        user_states[user_id] = {"action": "waiting_student_id"}

    # 5. طلب إضافة أدمن (مشرف) جديد
    elif call.data == "manage_add_admin" and user_id == ADMIN_ID:
        bot.send_message(user_id, "👑 أرسل الـ ID الخاص بالشخص المراد ترقيته إلى أدمن (مشرف):")
        user_states[user_id] = {"action": "waiting_admin_id"}

    # 6. طلب إضافة مساق جديد
    elif call.data == "manage_add_mat" and user_id in data["admins"]:
        bot.send_message(user_id, "➕ أرسل اسم المساق الجديد (مثال: تصميم منطقي رقمي):")
        user_states[user_id] = {"action": "waiting_mat_name"}

    # 7. طلب إضافة خيار جديد داخل مساق (مثل سلايدات)
    elif call.data.startswith("add_opt_") and user_id in data["admins"]:
        mat_key = call.data.split("_")[2]
        bot.send_message(user_id, "📝 أرسل اسم القسم الجديد (مثال: سلايدات الشابتر الأول، أو تلخيص الدفعة):")
        user_states[user_id] = {"action": "waiting_opt_name", "mat_key": mat_key}

# استقبال النصوص من المشرفين وتعديل قاعدة البيانات
@bot.message_handler(func=lambda message: message.chat.id in user_states)
def handle_inputs(message):
    data = load_data()
    user_id = message.chat.id
    state = user_states[user_id]

    # أ) إضافة طالب عادي
    if state["action"] == "waiting_student_id":
        try:
            target_id = int(message.text.strip())
            if target_id not in data["allowed_users"]:
                data["allowed_users"].append(target_id)
                save_data(data)
                bot.send_message(user_id, f"✅ تم تفعيل صلاحية التصفح للطالب: `{target_id}`", parse_mode="Markdown")
            else:
                bot.send_message(user_id, "هذا الطالب مضاف مسبقاً.")
        except ValueError:
            bot.send_message(user_id, "❌ خطأ، أرسل أرقام الـ ID فقط.")
        del user_states[user_id]

    # ب) إضافة أدمن جديد
    elif state["action"] == "waiting_admin_id":
        try:
            target_id = int(message.text.strip())
            if target_id not in data["admins"]:
                data["admins"].append(target_id)
                if target_id not in data["allowed_users"]: data["allowed_users"].append(target_id)
                save_data(data)
                bot.send_message(user_id, f"👑 تم ترقية المستخدم بنجاح إلى أدمن: `{target_id}`", parse_mode="Markdown")
            else:
                bot.send_message(user_id, "هذا المستخدم أدمن بالفعل.")
        except ValueError:
            bot.send_message(user_id, "❌ خطأ، أرسل أرقام الـ ID فقط.")
        del user_states[user_id]

    # ج) إضافة مساق جديد
    elif state["action"] == "waiting_mat_name":
        mat_name = message.text.strip()
        mat_key = str(len(data["materials"]) + 1)
        data["materials"][mat_key] = {"name": mat_name, "options": {}}
        save_data(data)
        bot.send_message(user_id, f"✅ تم إضافة مساق جديد باسم: {mat_name}")
        del user_states[user_id]

    # د) تحديد اسم الخيار الجديد داخل المساق
    elif state["action"] == "waiting_opt_name":
        opt_name = message.text.strip()
        mat_key = state["mat_key"]
        bot.send_message(user_id, f"🔗 الآن أرسل رابط الـ Google Drive أو الملف الخاص بـ ({opt_name}):")
        user_states[user_id] = {"action": "waiting_opt_link", "mat_key": mat_key, "opt_name": opt_name}

    # هـ) ربط الرابط بالخيار الجديد
    elif state["action"] == "waiting_opt_link":
        link = message.text.strip()
        mat_key = state["mat_key"]
        opt_name = state["opt_name"]

        if link.startswith("http"):
            data["materials"][mat_key]["options"][opt_name] = link
            save_data(data)
            bot.send_message(user_id, f"✅ تم بنجاح إضافة '{opt_name}' داخل المساق!")
        else:
            bot.send_message(user_id, "❌ خطأ، يجب إرسال رابط صحيح يبدأ بـ http.")
        del user_states[user_id]

bot.infinity_polling()
