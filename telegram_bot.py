import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore

# Flask app
app = Flask(__name__)

# Konfiguratsiya
API_URL = "https://api.telegram.org/bot{token}/{method}"

def get_env_settings():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    hr_chat_id = os.environ.get("HR_CHAT_ID")
    webhook_url = os.environ.get("WEBHOOK_URL")
    firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS")
    
    if not token:
        print("XATO: TELEGRAM_BOT_TOKEN topilmadi")
        sys.exit(1)
    if not hr_chat_id:
        print("XATO: HR_CHAT_ID topilmadi")
        sys.exit(1)
    if not firebase_creds_json:
        print("XATO: FIREBASE_CREDENTIALS topilmadi")
        sys.exit(1)
        
    return token, hr_chat_id, webhook_url, firebase_creds_json

TOKEN, HR_CHAT_ID, WEBHOOK_URL, FIREBASE_CREDS = get_env_settings()

# Firebase initialization
# User provided Web Config (for reference):
# apiKey: "AIzaSyDMYfYXtXL2ENNTbrx1wu_Xkpb6rS1SwGo"
# authDomain: "alxorazmiyishbot.firebaseapp.com"
# projectId: "alxorazmiyishbot"
# storageBucket: "alxorazmiyishbot.firebasestorage.app"
# messagingSenderId: "131888596228"
# appId: "1:131888596228:web:65dc085d428b6afec43c51"

try:
    creds_dict = json.loads(FIREBASE_CREDS)
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred, {
        'projectId': 'alxorazmiyishbot',
        'storageBucket': 'alxorazmiyishbot.firebasestorage.app'
    })
    db = firestore.client()
    print("Firebase muvaffaqiyatli bog'landi: alxorazmiyishbot")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    # Render'da xato bermasligi uchun sys.exit(1) ni olib tashladik, 
    # lekin db ishlamasligi mumkin
    db = None

# --- Yordamchi Funksiyalar ---

def api_call(method, params=None):
    """Telegram API ga so'rov yuborish"""
    url = API_URL.format(token=TOKEN, method=method)
    try:
        if params:
            data = urllib.parse.urlencode(params).encode("utf-8")
            req = urllib.request.Request(url, data=data)
        else:
            req = urllib.request.Request(url)
            
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"API xatolik ({method}): {e}")
        return {"ok": False}

def send_msg(chat_id, text, reply_markup=None):
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup)
    return api_call("sendMessage", params)

# --- Validatsiya ---

def is_valid_name(text):
    if not text: return False
    parts = text.strip().split()
    return len(parts) >= 2 and len(text) >= 5

def is_valid_phone(text):
    if not text: return False
    digits = "".join(filter(str.isdigit, text))
    return len(digits) >= 7

# --- Suhbat Menejeri ---

class BotLogic:
    def __init__(self):
        self.states = {} # user_id -> {step, data}
        self.positions = [
            ["Matematika o'qituvchisi", "Ingliz tili o'qituvchisi"],
            ["Ona tili va adabiyot", "Fizika o'qituvchisi"],
            ["Boshlang'ich sinf", "Administrator"],
            ["Boshqa lavozim"]
        ]
        self.main_menu = {
            "keyboard": [
                [{"text": "🏆 Grant - 2026"}],
                [{"text": "🗓️ Qabul - 2026"}, {"text": "ℹ️ Umumiy ma'lumot"}],
                [{"text": "📍 Manzilimiz"}],
                [{"text": "💼 Bo'sh ish o'rinlari"}, {"text": "📞 Biz bilan bog'lanish"}]
            ],
            "resize_keyboard": True
        }

    def handle_update(self, update):
        message = update.get("message")
        if not message: return
        
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text", "")
        contact = message.get("contact")

        # Komandalar
        if text == "/start" or text == "🏠 Asosiy menyu":
            self.states[user_id] = None
            send_msg(chat_id, "<b>Assalomu alaykum!</b>\n\nAl-Xorazmiy xususiy maktabining rasmiy botiga xush kelibsiz. Kerakli bo'limni tanlang:", self.main_menu)
            return

        # Asosiy Menyu tugmalarini qayta ishlash
        if not self.states.get(user_id):
            if text == "🏆 Grant - 2026":
                msg = (
                    "<b>🏆 Grant - 2026 dasturi</b>\n\n"
                    "Iqtidorli o'quvchilarni qo'llab-quvvatlash maqsadida maktabimiz har yili grantlar ajratadi.\n"
                    "Grantlar o'quvchilarning kirish imtihonlaridagi natijalariga ko'ra beriladi.\n\n"
                    "Batafsil ma'lumot uchun: @u_gafforov"
                )
                send_msg(chat_id, msg, self.main_menu)
                return
            
            elif text == "🗓️ Qabul - 2026":
                msg = (
                    "<b>🗓️ 2026-2027 o'quv yili uchun qabul</b>\n\n"
                    "Qabul jarayonlari quyidagi bosqichlardan iborat:\n"
                    "1. Onlayn ro'yxatdan o'tish\n"
                    "2. Kirish imtihonlari (Matematika, Mantiq, Ingliz tili)\n"
                    "3. Psixologik suhbat\n\n"
                    "Hozirda 1-11 sinflar uchun qabul davom etmoqda."
                )
                send_msg(chat_id, msg, self.main_menu)
                return

            elif text == "ℹ️ Umumiy ma'lumot":
                msg = (
                    "<b>Maktab haqida umumiy ma'lumot</b>\n\n"
                    "Al-Xorazmiy xususiy maktabi zamonaviy ta'lim texnologiyalari va milliy qadriyatlar uyg'unligini ta'minlaydi.\n"
                    "Bizning afzalliklarimiz:\n"
                    "- Chuqurlashtirilgan IT va Matematika\n"
                    "- Ingliz tilini intensiv o'rganish\n"
                    "- Shaxmat va robototexnika to'garaklari\n"
                    "- 3 mahal issiq ovqat va transport xizmati"
                )
                send_msg(chat_id, msg, self.main_menu)
                return

            elif text == "📍 Manzilimiz":
                msg = (
                    "<b>📍 Bizning manzil:</b>\n\n"
                    "Toshkent shahri, Yunusobod tumani, XXX ko'chasi, XX-uy.\n"
                    "Mo'ljal: XXXXXXXXXX\n\n"
                    "Ish vaqti: 09:00 - 18:00 (Dush-Shan)"
                )
                # Google Maps linkini ham qo'shish mumkin
                send_msg(chat_id, msg, self.main_menu)
                return

            elif text == "📞 Biz bilan bog'lanish":
                msg = (
                    "<b>📞 Aloqa markazi:</b>\n\n"
                    "Telefon: +998 90 XXX XX XX\n"
                    "Telegram: @u_gafforov\n"
                    "Email: info@alxorazmiy.uz"
                )
                send_msg(chat_id, msg, self.main_menu)
                return

            elif text == "💼 Bo'sh ish o'rinlari":
                self.states[user_id] = {"step": "name", "data": {}}
                send_msg(chat_id, "<b>Ishga qabul bo'limi</b>\n\nIltimos, ism va familiyangizni kiriting:", {"remove_keyboard": True})
                return

        # Ariza topshirish flow'i (states mavjud bo'lsa)
        state = self.states.get(user_id)
        if not state:
            send_msg(chat_id, "Iltimos, pastdagi menyudan birini tanlang.", self.main_menu)
            return

        if text == "❌ Bekor qilish":
            self.states[user_id] = None
            send_msg(chat_id, "Ariza topshirish bekor qilindi.", self.main_menu)
            return

        step = state["step"]
        
        if step == "name":
            if is_valid_name(text):
                state["data"]["name"] = text
                state["step"] = "phone"
                markup = {
                    "keyboard": [
                        [{"text": "Kontaktni yuborish", "request_contact": True}],
                        [{"text": "❌ Bekor qilish"}]
                    ],
                    "resize_keyboard": True,
                    "one_time_keyboard": True
                }
                send_msg(chat_id, "Telefon raqamingizni yuboring (tugmani bosing):", markup)
            else:
                send_msg(chat_id, "Iltimos, ism va familiyangizni to'liq yozing (Masalan: Ali Valiyev):\n\nBekor qilish uchun '❌ Bekor qilish' tugmasini bosing.")
        
        elif step == "phone":
            phone_val = None
            if contact:
                phone_val = contact.get("phone_number")
            elif is_valid_phone(text):
                phone_val = text

            if phone_val:
                state["data"]["phone"] = phone_val
                state["step"] = "position"
                kb = [[{"text": p} for p in row] for row in self.positions]
                kb.append([{"text": "❌ Bekor qilish"}])
                markup = {
                    "keyboard": kb,
                    "resize_keyboard": True
                }
                send_msg(chat_id, "Qaysi lavozimga topshirmoqchisiz? (Ro'yxatdan tanlang yoki yozing):", markup)
            else:
                send_msg(chat_id, "Iltimos, telefon raqamingizni tugma orqali yuboring yoki yozing:")

        elif step == "position":
            if len(text) > 2:
                state["data"]["position"] = text
                state["step"] = "exp"
                markup = {
                    "keyboard": [[{"text": "❌ Bekor qilish"}]],
                    "resize_keyboard": True
                }
                send_msg(chat_id, "Ish tajribangiz haqida qisqacha ma'lumot bering:", markup)
            else:
                send_msg(chat_id, "Lavozim nomini kiriting:")

        elif step == "exp":
            if len(text) > 5:
                state["data"]["exp"] = text
                state["step"] = "cv"
                markup = {
                    "keyboard": [
                        [{"text": "O'tkazib yuborish"}],
                        [{"text": "❌ Bekor qilish"}]
                    ],
                    "resize_keyboard": True,
                    "one_time_keyboard": True
                }
                send_msg(chat_id, "Rezyume (PDF yoki Rasm) yuboring yoki 'O'tkazib yuborish' tugmasini bosing:", markup)
            else:
                send_msg(chat_id, "Tajribangiz haqida batafsilroq yozing:")

        elif step == "cv":
            cv_file_id = None
            cv_type = None
            
            if message.get("document"):
                cv_file_id = message["document"]["file_id"]
                cv_type = "doc"
            elif message.get("photo"):
                cv_file_id = message["photo"][-1]["file_id"]
                cv_type = "photo"
            elif text in ["O'tkazib yuborish", "/skip"]:
                pass
            else:
                send_msg(chat_id, "Iltimos, fayl yuboring yoki tugmani bosing.")
                return

            # Firebase va HR ga yuborish
            self.finish_and_send(user_id, state["data"], cv_file_id, cv_type)
            send_msg(chat_id, "✅ <b>Rahmat!</b> Arizangiz HR bo'limiga yuborildi.", self.main_menu)
            del self.states[user_id]

    def finish_and_send(self, user_id, data, file_id, f_type):
        # 1. Firestore'ga saqlash
        saved_to_firebase = False
        try:
            if db:
                doc_ref = db.collection("applications").document()
                doc_ref.set({
                    "user_id": user_id,
                    "name": data["name"],
                    "phone": data["phone"],
                    "position": data["position"],
                    "experience": data["exp"],
                    "cv_file_id": file_id,
                    "cv_type": f_type,
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
                saved_to_firebase = True
        except Exception as e:
            print(f"Firestore save error: {e}")

        # 2. HR ga Telegram orqali yuborish
        status_msg = "(Firebase'ga saqlandi)" if saved_to_firebase else "(Firebase'ga saqlanmadi!)"
        report = (
            f"<b>Yangi Ariza! {status_msg}</b>\n\n"
            f"👤 Nomzod: {data['name']}\n"
            f"📞 Tel: {data['phone']}\n"
            f"💼 Lavozim: {data['position']}\n"
            f"📝 Tajriba: {data['exp']}\n"
            f"🆔 ID: {user_id}"
        )
        send_msg(HR_CHAT_ID, report)
        
        if file_id:
            method = "sendDocument" if f_type == "doc" else "sendPhoto"
            param_key = "document" if f_type == "doc" else "photo"
            api_call(method, {"chat_id": HR_CHAT_ID, param_key: file_id, "caption": f"{data['name']} - Rezyume"})

bot_logic = BotLogic()

# --- Flask Yo'llari ---

@app.route("/", methods=["GET"])
def home():
    return "Bot with Firebase is active", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if update:
        try:
            bot_logic.handle_update(update)
        except Exception as e:
            print(f"Update error: {e}")
    return "OK", 200

if __name__ == "__main__":
    if WEBHOOK_URL:
        api_call("setWebhook", {"url": f"{WEBHOOK_URL}/webhook"})
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
