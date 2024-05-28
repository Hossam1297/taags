import requests
import telebot
import os
import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from threading import Thread
import schedule
import time

# ضع هنا التوكن الخاص ببوتك ومفتاح API للطقس
TELEGRAM_BOT_TOKEN = '7096631094:AAHUHQHerLsDqEKLIG6FUQ1FJhsMel3cSRY'
WEATHER_API_KEY = 'd05691f56952e6d955b5154d6354f8b1'

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# قائمة معرفات الأدمن
ADMINS = [6133947276]  # ضع معرفات الأدمن هنا

# ملفات التخزين
MEMBERS_FILE = 'members.txt'
CHANNELS_FILE = 'channels.txt'
MESSAGE_FILE = 'message.txt'
STATS_FILE = 'stats.txt'
NEW_MEMBERS_FILE = 'new_members.txt'
SUBSCRIBED_MEMBERS_FILE = 'subscribed_members.txt'

# تحميل البيانات من الملفات
def load_data(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'r', encoding='utf-8') as file:
            return file.read().splitlines()
    return []

def save_data(data, file_name):
    with open(file_name, 'w', encoding='utf-8') as file:
        file.write('\n'.join(data))

# تحميل الأعضاء والقنوات
members = load_data(MEMBERS_FILE)
required_channels = load_data(CHANNELS_FILE)

# الحد الأقصى لعدد القنوات للاشتراك الإجباري
MAX_CHANNELS = 5

# تحميل الرسالة
if os.path.exists(MESSAGE_FILE):
    with open(MESSAGE_FILE, 'r', encoding='utf-8') as file:
        subscription_message = file.read()
else:
    subscription_message = "يجب عليك الاشتراك في القنوات التالية لاستخدام البوت:"

# دالة للتحقق من اشتراك المستخدم في القنوات المطلوبة
def is_user_subscribed(user_id):
    for channel in required_channels:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"Error checking subscription status for {user_id} in {channel}: {e}")
            return False
    return True

# دالة لجلب بيانات الطقس الحالية
def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ar"
    response = requests.get(url)
    data = response.json()

    if response.status_code == 200:
        main = data['weather'][0]['main']
        description = data['weather'][0]['description']
        temp = data['main']['temp']
        return f"الطقس الحالي في {city} :\n{main} - {description}\nدرجة الحرارة: {temp}°C"
    else:
        return "لم أتمكن من جلب بيانات الطقس. يرجى التحقق من اسم المدينة والمحاولة مرة أخرى."

# دالة لجلب بيانات الطقس للأيام المقبلة
def get_forecast(city):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ar"
    response = requests.get(url)
    data = response.json()

    if response.status_code == 200:
        forecast_list = data['list'][:7]  # جلب توقعات الأيام القادمة (7 توقعات كل 3 ساعات)
        forecast_data = f"توقعات الطقس في {city} بعد كُل 3 ساعات :\n-----------------------------------------------\n"
        for forecast in forecast_list:
            date = forecast['dt_txt']
            main = forecast['weather'][0]['main']
            description = forecast['weather'][0]['description']
            temp = forecast['main']['temp']
            forecast_data += f"الساعة واليوم : {date}\nحالة الطقس : {main} - {description}\nدرجة الحرارة: {temp}°C\n-----------------------------------------------\n"
        return forecast_data
    else:
        return "لم أتمكن من جلب بيانات الطقس للأيام المقبلة. يرجى التحقق من اسم المدينة والمحاولة مرة أخرى."

# دالة لإرسال رسالة ترحيبية مع الأزرار
def send_main_menu(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("الطقس الحالي", callback_data="weather"),
        InlineKeyboardButton("توقعات الطقس", callback_data="forecast")
    )
    if chat_id in ADMINS:
        markup.add(
            InlineKeyboardButton("إرسال رسالة للجميع", callback_data="broadcast"),
            InlineKeyboardButton("إضافة اشتراك إجباري", callback_data="add_subscription"),
            InlineKeyboardButton("حذف اشتراك إجباري", callback_data="remove_subscription"),
            InlineKeyboardButton("تغيير رسالة الاشتراك", callback_data="change_message"),
            InlineKeyboardButton("عرض الإحصائيات", callback_data="show_stats")
        )
    bot.send_message(chat_id, "اهلا بك عزيزي في بوت الطقس .\nالبوت يعطيك :\n\n1 - حالة الجو اذا كانت ممطرة او غائمة.. الخ .\n2 - درجة الحرارة دقيقة جداً .\n3 - حالة الجو ودرجة الحرارة في كافة الدول . \n 4 - حالة الطقس للأيام المُقبلة . \n 5- يتم تحديث حالة الجو ودرجة الحرارة تلقائي كل 3 ساعات . \n\n#ملاحظة يمكنك كتابة اسم الدولتك او اسم محافظتك في العربي او الانجليزي .", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if str(chat_id) not in members:
        members.append(str(chat_id))
        save_data(members, MEMBERS_FILE)
        update_new_members_stats()
    if is_user_subscribed(chat_id) or chat_id in ADMINS:
        send_main_menu(chat_id)
    else:
        bot.send_message(chat_id, subscription_message)
        for channel in required_channels:
            bot.send_message(chat_id, channel)

# دالة للتعامل مع ضغط الأزرار
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if not is_user_subscribed(call.message.chat.id) and call.message.chat.id not in ADMINS:
        bot.send_message(call.message.chat.id, subscription_message)
        for channel in required_channels:
            bot.send_message(call.message.chat.id, channel)
        return
    
    if call.data == "weather":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
        bot.send_message(call.message.chat.id, "من فضلك أدخل اسم المدينة:", reply_markup=markup)
        bot.register_next_step_handler(call.message, process_city_name, "weather")
    elif call.data == "forecast":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
        bot.send_message(call.message.chat.id, "من فضلك أدخل اسم المدينة:", reply_markup=markup)
        bot.register_next_step_handler(call.message, process_city_name, "forecast")
    elif call.data == "broadcast":
        bot.send_message(call.message.chat.id, "من فضلك أدخل الرسالة التي تريد إرسالها لجميع الأعضاء:")
        bot.register_next_step_handler(call.message, broadcast_message)
    elif call.data == "add_subscription":
        if len(required_channels) >= MAX_CHANNELS:
            bot.send_message(call.message.chat.id, 'لقد وصلت إلى الحد الأقصى من القنوات.')
        else:
            bot.send_message(call.message.chat.id, 'من فضلك أدخل معرف القناة (بصيغة @channelusername):')
            bot.register_next_step_handler(call.message, add_subscription)
    elif call.data == "remove_subscription":
        bot.send_message(call.message.chat.id, 'من فضلك أدخل معرف القناة التي تريد إزالتها (بصيغة @channelusername):')
        bot.register_next_step_handler(call.message.chat.id, remove_subscription)
    elif call.data == "change_message":
        bot.send_message(call.message.chat.id, 'من فضلك أدخل الرسالة الجديدة التي تريد عرضها للمستخدمين غير المشتركين:')
        bot.register_next_step_handler(call.message, change_subscription_message)
    elif call.data == "show_stats":
        show_stats(call.message.chat.id)
    elif call.data == "main_menu":
        send_main_menu(call.message.chat.id)

# دالة لمعالجة اسم المدينة الذي أدخله المستخدم
def process_city_name(message, query_type):
    city = message.text
    if query_type == "weather":
        weather_info = get_weather(city)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
        bot.send_message(message.chat.id, weather_info, reply_markup=markup)
    elif query_type == "forecast":
        forecast_info = get_forecast(city)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("رجوع", callback_data="main_menu"))
        bot.send_message(message.chat.id, forecast_info, reply_markup=markup)

# دالة لإرسال رسالة لجميع الأعضاء
def broadcast_message(message):
    broadcast_text = message.text
    for member_id in members:
        try:
            bot.send_message(member_id, broadcast_text)
        except Exception as e:
            print(f"Failed to send message to {member_id}: {e}")
    bot.send_message(message.chat.id, "تم إرسال الرسالة لجميع الأعضاء.")

# دالة لإضافة اشتراك إجباري
def add_subscription(message):
    channel_username = message.text
    if channel_username.startswith('@'):
        if channel_username not in required_channels:
            required_channels.append(channel_username)
            save_data(required_channels, CHANNELS_FILE)
            bot.send_message(message.chat.id, f'تم إضافة {channel_username} إلى الاشتراك الإجباري.')
        else:
            bot.send_message(message.chat.id, f'القناة {channel_username} موجودة بالفعل في الاشتراك الإجباري.')
    else:
        bot.send_message(message.chat.id, 'يرجى إدخال معرف صالح.')

# دالة لحذف اشتراك إجباري
def remove_subscription(message):
    channel_username = message.text
    if channel_username in required_channels:
        required_channels.remove(channel_username)
        save_data(required_channels, CHANNELS_FILE)
        bot.send_message(message.chat.id, f'تم إزالة {channel_username} من الاشتراك الإجباري.')
    else:
        bot.send_message(message.chat.id, 'المعرف غير موجود في قائمة الاشتراك الإجباري.')

# دالة لتغيير رسالة الاشتراك الإجباري
def change_subscription_message(message):
    global subscription_message
    subscription_message = message.text
    with open(MESSAGE_FILE, 'w', encoding='utf-8') as file:
        file.write(subscription_message)
    bot.send_message(message.chat.id, 'تم تغيير رسالة الاشتراك بنجاح.')

# دالة لتحديث إحصائيات الأعضاء الجدد
def update_new_members_stats():
    today = datetime.date.today().isoformat()
    new_members_stats = load_data(NEW_MEMBERS_FILE)
    
    if new_members_stats and new_members_stats[-1].startswith(today):
        date, count = new_members_stats[-1].split(':')
        count = int(count) + 1
        new_members_stats[-1] = f"{today}:{count}"
    else:
        new_members_stats.append(f"{today}:1")
    
    save_data(new_members_stats, NEW_MEMBERS_FILE)

# دالة لعرض الإحصائيات
def show_stats(chat_id):
    num_members = len(members)
    num_channels = len(required_channels)

    new_members_stats = load_data(NEW_MEMBERS_FILE)
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    month_start = datetime.date.today().replace(day=1).isoformat()

    new_today = sum(int(line.split(':')[1]) for line in new_members_stats if line.startswith(today))
    new_yesterday = sum(int(line.split(':')[1]) for line in new_members_stats if line.startswith(yesterday))
    new_this_month = sum(int(line.split(':')[1]) for line in new_members_stats if line.startswith(month_start[:7]))

    subscribed_members = load_data(SUBSCRIBED_MEMBERS_FILE)
    num_subscribed = len(set(subscribed_members))

    stats_message = (
        f"إحصائيات البوت:\n\n"
        f"عدد الأعضاء الكلي: {num_members}\n"
        f"عدد الأعضاء الجدد اليوم: {new_today}\n"
        f"عدد الأعضاء الجدد بالأمس: {new_yesterday}\n"
        f"عدد الأعضاء الجدد هذا الشهر: {new_this_month}\n"
        f"عدد الأعضاء المشتركين في القنوات: {num_subscribed}\n"
        f"عدد القنوات في الاشتراك الإجباري: {num_channels}"
    )
    bot.send_message(chat_id, stats_message)

# دالة لتحديث الإحصائيات يوميًا
def update_stats_daily():
    subscribed_members = []

    for member_id in members:
        if is_user_subscribed(member_id):
            subscribed_members.append(member_id)
    
    save_data(subscribed_members, SUBSCRIBED_MEMBERS_FILE)

def start_daily_stats_update():
    schedule.every().day.at("00:00").do(update_stats_daily)
    while True:
        schedule.run_pending()
        time.sleep(1)

# بدء تشغيل الوظيفة في خيط منفصل
Thread(target=start_daily_stats_update).start()

# بدء تشغيل البوت
bot.polling()
