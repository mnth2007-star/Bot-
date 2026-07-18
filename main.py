import telebot
import json
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# جلب التوكن والـ ID الخاص بك من الـ Environment Variables في Render
#import os
import telebot

# قراءة التوكن والآيدي من الإعدادات التي وضعناها في موقع Render
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

# تعريف البوت باستخدام المتغير الذي قرأناه
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

    # إذا كان المستخدم غير مفعل وليس أدمن، نطلب منه التحقق عبر رقم الجوال أولاً
    if user_id not in data["allowed_users"] and user_id not in data["admins"]:
        markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        button_phone = KeyboardButton(text="مشاركة رقم الجوال للتفعيل 📱", request_contact=True)
        markup.add(button_phone)
        
        bot.send_message(user_id, "📚 أهلاً بك في بوت المساقات الهندسية.\n\nلتفعيل حسابك والوصول للمواد تلقائياً، يرجى الضغط على الزر بالأسفل لمشاركة رقم الجوال:", reply_markup=markup)
        return

    # إذا كان مفعلاً مسبقاً، تظهر له المواد مباشرة
    bot.send_message(user_id, "📚 أهلاً بك مجدداً. اختر المساق المكلّف به:", 
                     reply_markup=get_main_keyboard(user_id, data))

# استقبال رقم الجوال والتحقق التلقائي
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    data = load_data()
    user_id = message.chat.id
    
    if message.contact is not None:
        # التأكد من أن الرقم يخص نفس صاحب الحساب لأمان البوت
        if message.contact.user_id == user_id:
            phone_number = message.contact.phone_number
            user_name = message.from_user.first_name if message.from_user.first_name else "طالب هندسة"
            
            # تنظيف رقم الجوال (حذف الرمز الدولي إن وجد لتسهيل البحث لاحقاً)
            clean_phone = phone_number.replace("+", "").strip()
            
            # حفظ بيانات الملف الشخصي وربطه بالـ ID
            data["users_profile"][str(user_id)] = {
                "name": user_name,
                "phone": clean_phone
            }
            
            # تفعيل الطالب تلقائياً بمجرد مشاركة رقمه
            if user_id not in data["allowed_users"]:
                data["allowed_users"].append(user_id)
                
            save_data(data)
            
            bot.send_message(user_id, f"✅ تم تفعيل حسابك بنجاح يا مهندس {user_name}!\nبإمكانك الآن تصفح المساقات بحرية.", reply_markup=ReplyKeyboardRemove())
            bot.send_message(user_id, "اختر المساق المكلّف به:", reply_markup=get_main_keyboard(user_id, data))
        else:
            bot.send_message(user_id, "❌ خطأ: يرجى مشاركة رقم الجوال الخاص بحسابك الحالي فقط عبر الزر.")

# التعامل مع الضغطات (Inline Callbacks)
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
            for option_name, link in mat.get("options", {}).items():
                markup.add(InlineKeyboardButton(text=f"🔗 {option_name}", url=link))

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
        markup.add(InlineKeyboardButton(text="👤 إضافة طالب (بالرقم أو الـ ID)", callback_data="manage_add_student"))
        if user_id == ADMIN_ID:
            markup.add(InlineKeyboardButton(text="👑 تعيين أدمن جديد (مشرف)", callback_data="manage_add_admin"))
        markup.add(InlineKeyboardButton(text="🔙 خروج", callback_data="back_main"))
        bot.edit_message_text(chat_id=user_id, message_id=message_id, text="⚙️ لوحة تحكم المشرفين. اختر ماذا تريد أن تفعل:", reply_markup=markup)

    # 4. طلب إضافة طالب عادي
    elif call.data == "manage_add_student" and user_id in data["admins"]:
        bot.send_message(user_id, "👤 أرسل رقم جوال الطالب (مثال: 059xxxx) أو الـ ID الخاص به لتفعيله يدوياً:")
        user_states[user_id] = {"action": "waiting_student_id"}

    # 5. طلب إضافة أدمن جديد
    elif call.data == "manage_add_admin" and user_id == ADMIN_ID:
        bot.send_message(user_id, "👑 أرسل رقم جوال الشخص أو الـ ID الخاص به لترقيته إلى أدمن:")
        user_states[user_id] = {"action": "waiting_admin_id"}

    # 6. طلب إضافة مساق جديد
    elif call.data == "manage_add_mat" and user_id in data["admins"]:
        bot.send_message(user_id, "➕ أرسل اسم المساق الجديد (مثال: تصميم منطقي رقمي):")
        user_states[user_id] = {"action": "waiting_mat_name"}

    # 7. طلب إضافة خيار جديد داخل مساق
    elif call.data.startswith("add_opt_") and user_id in data["admins"]:
        mat_key = call.data.split("_")[2]
        bot.send_message(user_id, "📝 أرسل اسم القسم الجديد (مثال: سلايدات الشابتر الأول):")
        user_states[user_id] = {"action": "waiting_opt_name", "mat_key": mat_key}

# دالة مساعدة للبحث عن الـ ID بواسطة رقم الهاتف أو النص المدخل
def find_user_id(input_text, data):
    input_text = input_text.strip().replace("+", "")
    # أولاً: تجربة تحويل المدخل إلى رقم معرف ID مباشر
    if input_text.isdigit() and len(input_text) > 7 and not input_text.startswith("0"):
        return int(input_text)
    
    # ثانياً: البحث عن طريق رقم الهاتف في قاعدة البيانات profile
    for u_id, profile in data.get("users_profile", {}).items():
        if profile.get("phone") == input_text or input_text in profile.get("phone", ""):
            return int(u_id)
    return None

# استقبال المدخلات النصية من المشرفين والتعديل على البيانات
@bot.message_handler(func=lambda message: message.chat.id in user_states)
def handle_inputs(message):
    data = load_data()
    user_id = message.chat.id
    state = user_states[user_id]
    input_text = message.text.strip()

    # أ) إضافة طالب عادي
    if state["action"] == "waiting_student_id":
        target_id = find_user_id(input_text, data)
        if target_id:
            if target_id not in data["allowed_users"]:
                data["allowed_users"].append(target_id)
                save_data(data)
                bot.send_message(user_id, f"✅ تم تفعيل صلاحية الطالب بنجاح للمعرف: `{target_id}`", parse_mode="Markdown")
            else:
                bot.send_message(user_id, "هذا الطالب مضاف مسبقاً ومفعّل.")
        else:
            bot.send_message(user_id, "❌ لم نتمكن من العثور على طالب بهذا الرقم في قاعدة البيانات، يرجى التأكد من كتابة الرقم الصحيح أو الـ ID المباشر.")
        del user_states[user_id]

    # ب) إضافة أدمن جديد
    elif state["action"] == "waiting_admin_id":
        target_id = find_user_id(input_text, data)
        if target_id:
            if target_id not in data["admins"]:
                data["admins"].append(target_id)
                if target_id not in data["allowed_users"]: data["allowed_users"].append(target_id)
                save_data(data)
                bot.send_message(user_id, f"👑 تم ترقية المستخدم بنجاح إلى أدمن: `{target_id}`", parse_mode="Markdown")
            else:
                bot.send_message(user_id, "هذا المستخدم أدمن بالفعل.")
        else:
            bot.send_message(user_id, "❌ لم نتمكن من العثور على هذا الحساب بالرقم المدخل.")
        del user_states[user_id]

    # ج) إضافة مساق جديد
    elif state["action"] == "waiting_mat_name":
        mat_name = input_text
        mat_key = str(len(data["materials"]) + 1)
        data["materials"][mat_key] = {"name": mat_name, "options": {}}
        save_data(data)
        bot.send_message(user_id, f"✅ تم إضافة مساق جديد باسم: {mat_name}")
        del user_states[user_id]

    # د) تحديد اسم الخيار الجديد
    elif state["action"] == "waiting_opt_name":
        opt_name = input_text
        mat_key = state["mat_key"]
        bot.send_message(user_id, f"🔗 الآن أرسل رابط الـ Google Drive الخاص بـ ({opt_name}):")
        user_states[user_id] = {"action": "waiting_opt_link", "mat_key": mat_key, "opt_name": opt_name}

    # هـ) ربط الرابط بالقسم الجديد
    elif state["action"] == "waiting_opt_link":
        link = input_text
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
