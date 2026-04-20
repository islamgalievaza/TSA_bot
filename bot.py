import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from anthropic import Anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY")
PORT = int(os.environ.get("PORT", 8080))

client = Anthropic(api_key=ANTHROPIC_KEY)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass


def run_health_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


TEXTS = {
    "ru": {
        "welcome": (
            "👋 Привет!\n\n"
            "Этот бот поможет тебе найти свою целевую аудиторию.\n\n"
            "🎯 Что делает бот:\n"
            "Ты отвечаешь на 8 вопросов о своей нише, а ИИ анализирует рынок и выдаёт подробный разбор сегментов ЦА — с портретами клиентов, их болями, триггерами и готовыми инструкциями по маркетингу.\n\n"
            "📌 Что получишь:\n"
            "— Кто твой клиент и как он живёт\n"
            "— Что его останавливает от покупки\n"
            "— Где его найти: таргет, поиск, геолокация\n"
            "— Готовый посыл для рекламы\n\n"
            "Нажми кнопку чтобы начать 👇"
        ),
        "start_btn": "🚀 Начать анализ",
        "analyzing": "⏳ ИИ анализирует твою нишу...\n\nЭто займёт 2–3 минуты. Пожалуйста, подожди.",
        "done": "✅ Анализ готов!\n\n",
        "restart_btn": "🔄 Попробовать другую нишу",
        "change_lang_btn": "🌐 Сменить язык",
        "restart_msg": "Хорошо, начинаем с новой нишей!\n\nОтвечай развёрнуто — чем подробнее, тем точнее результат.",
        "answer_prompt": "Напиши свой ответ 👇",
        "too_short": "✏️ Напиши хотя бы 2–3 предложения — так анализ будет точнее.",
        "footer": "─────────────────\n✉️ @azamatislamgaliev",
        "no_session": "Напиши /start чтобы начать.",
    },
    "uz": {
        "welcome": (
            "👋 Salom!\n\n"
            "Bu bot sizga maqsadli auditoriyangizni topishga yordam beradi.\n\n"
            "🎯 Bot nima qiladi:\n"
            "Siz nichangiz haqida 8 ta savolga javob berasiz, AI bozorni tahlil qiladi va mijozlar segmentlari bo'yicha batafsil tahlil beradi.\n\n"
            "📌 Natijada nima olasiz:\n"
            "— Mijozingiz kim va qanday yashaydi\n"
            "— Uni sotib olishdan nima to'xtatadi\n"
            "— Uni qayerdan topish: target, qidiruv, geolokatsiya\n"
            "— Reklama uchun tayyor matn\n\n"
            "Boshlash uchun tugmani bosing 👇"
        ),
        "start_btn": "🚀 Tahlilni boshlash",
        "analyzing": "⏳ AI nichangizni tahlil qilmoqda...\n\n2–3 daqiqa vaqt oladi. Iltimos, kuting.",
        "done": "✅ Tahlil tayyor!\n\n",
        "restart_btn": "🔄 Boshqa nichani sinab ko'rish",
        "change_lang_btn": "🌐 Tilni o'zgartirish",
        "restart_msg": "Yaxshi, yangi nicha bilan boshlaymiz!\n\nBatafsil yozing — qanchalik to'liq bo'lsa, natija shunchalik aniq bo'ladi.",
        "answer_prompt": "Javobingizni yozing 👇",
        "too_short": "✏️ Kamida 2–3 ta gap yozing — shunda tahlil aniqroq bo'ladi.",
        "footer": "─────────────────\n✉️ @azamatislamgaliev",
        "no_session": "/start yozing va boshlang.",
    }
}

QUESTIONS = {
    "ru": [
        {"num": "01", "q": "Чем ты занимаешься и что именно продаёшь?",
         "hint": "Опиши своими словами: что это, в каком формате — офлайн или онлайн, услуга или продукт, для кого.",
         "example": "💡 Пример: Офлайн-школа игры на фортепиано. Занятия в студии один на один с преподавателем. Берём детей от 5 лет и взрослых любого возраста."},
        {"num": "02", "q": "Как устроен процесс — что получает клиент?",
         "hint": "Опиши шаги от первого контакта до результата. Что входит, сколько длится.",
         "example": "💡 Пример: Урок 45 минут, 1–2 раза в неделю. Пробный урок 50 000 сум. Индивидуальная программа — классика или популярные песни."},
        {"num": "03", "q": "В чём твоё отличие от конкурентов?",
         "hint": "Что есть у тебя, чего нет у других — у частных специалистов, других школ, похожих сервисов?",
         "example": "💡 Пример: Единственная школа в районе, где с нуля сразу играют любимые песни — без зубрёжки нот. Плюс удобная парковка."},
        {"num": "04", "q": "Где ты находишься или в каком регионе работаешь?",
         "hint": "Если офлайн — город, район, ориентиры. Если онлайн — на какую аудиторию ориентируешься.",
         "example": "💡 Пример: Ташкент, Юнусабадский район. Рядом метро и крупный ТЦ. Работаем с жителями района."},
        {"num": "05", "q": "Какую реальную ситуацию клиента ты решаешь?",
         "hint": "Что происходит в жизни человека ДО того, как он находит тебя. Не эмоцию — конкретную ситуацию.",
         "example": "💡 Пример: Родители хотят отдать ребёнка в музыкальную школу, но боятся государственной — там строго, дети плачут и бросают."},
        {"num": "06", "q": "Кто уже является твоим клиентом?",
         "hint": "Если клиенты есть — кто они, зачем пришли. Если нет — так и напиши.",
         "example": "💡 Пример: Дети 6–12 лет, которых приводят мамы. Несколько взрослых: женщина 42 года «для души», мужчина 35 лет — на корпоративы."},
        {"num": "07", "q": "Какая у тебя цена и формат оплаты?",
         "hint": "Стоимость в сумах, есть ли абонемент, пробный период, рассрочка.",
         "example": "💡 Пример: Абонемент 8 уроков — 800 000 сум. Разовый — 120 000 сум. Первый пробный — 50 000 сум."},
        {"num": "08", "q": "Как сейчас к тебе приходят клиенты?",
         "hint": "Откуда узнают о тебе прямо сейчас. Что работает, что пробовал и не сработало.",
         "example": "💡 Пример: В основном сарафанное радио и Яндекс.Карты. Instagram не ведём. Таргет не запускали."}
    ],
    "uz": [
        {"num": "01", "q": "Siz nima bilan shug'ullanasiz va nima sotasiz?",
         "hint": "O'z so'zlaringiz bilan: bu nima, qanday formatda — oflayn yoki onlayn, xizmat yoki mahsulot, kim uchun.",
         "example": "💡 Misol: Oflayn fortepiano maktabi. Darslar studiyada o'qituvchi bilan bir-birga. 5 yoshdan bolalar va kattalarga qabul qilamiz."},
        {"num": "02", "q": "Jarayon qanday tashkil etilgan — mijoz nima oladi?",
         "hint": "Birinchi murojaaтdan natijaga qadar bosqichlarni tavsiflang.",
         "example": "💡 Misol: Dars 45 daqiqa, haftasiga 1–2 marta. Sinov darsi 50 000 so'm. Individual dastur — klassika yoki sevimli qo'shiqlar."},
        {"num": "03", "q": "Raqobatchilardan farqingiz nimada?",
         "hint": "Sizda bor, boshqalarda yo'q narsa — xususiy mutaxassislar, boshqa maktablar, o'xshash xizmatlar.",
         "example": "💡 Misol: Hududdagi yagona maktabmizki, noldan boshlagan holda darhol sevimli qo'shiqlarni o'ynash mumkin."},
        {"num": "04", "q": "Siz qayerda joylashgansiz yoki qaysi mintaqada ishlaysiz?",
         "hint": "Oflayn bo'lsa — shahar, tuman, mo'ljallar. Onlayn bo'lsa — qaysi auditoriyaga yo'naltirilgansiz.",
         "example": "💡 Misol: Toshkent, Yunusobod tumani. Yaqinda metro va savdo markazi."},
        {"num": "05", "q": "Mijozning qaysi real vaziyatini hal qilasiz?",
         "hint": "Siz topishdan OLDIN odamning hayotida nima sodir bo'lishini tasvirlab bering.",
         "example": "💡 Misol: Ota-onalar farzandini musiqa maktabiga bermoqchi, lekin davlat maktabidan qo'rqishadi."},
        {"num": "06", "q": "Sizning mijozlaringiz kim?",
         "hint": "Agar mijozlar bor bo'lsa — ular kim, nima uchun kelishgan. Yo'q bo'lsa — shunday yozing.",
         "example": "💡 Misol: Asosan onalar olib keladigan 6–12 yoshli bolalar. 42 yoshli ayol 'o'zi uchun', 35 yoshli erkak korporativlar uchun."},
        {"num": "07", "q": "Narxingiz va to'lov formatingiz qanday?",
         "hint": "So'mdagi narx, obuna, sinov muddati, bo'lib to'lash.",
         "example": "💡 Misol: 8 darsga abonement — 800 000 so'm. Bir martalik — 120 000 so'm. Sinov darsi — 50 000 so'm."},
        {"num": "08", "q": "Hozir mijozlar sizga qanday keladi?",
         "hint": "Ular hozir siz haqingizda qayerdan bilib olishadi. Nima ishlaydi, nima ishlamadi.",
         "example": "💡 Misol: Asosan og'izdan-og'izga va Yandex.Xaritalar. Instagramni yuritmaymiz."}
    ]
}

SYSTEM_PROMPT = {
    "ru": """Ты — эксперт по исследованию рынка и сегментации целевой аудитории. Работаешь исключительно с реальными данными. Никогда ничего не выдумываешь. Отвечай ТОЛЬКО на русском языке.

ВАЖНО ПРО ФОРМАТИРОВАНИЕ:
— Пиши как опытный копирайтер — живо, конкретно, с характером
— Используй эмодзи в заголовках сегментов для визуального разделения
— Каждый пункт начинай с новой строки
— Между сегментами ставь разделитель ═══════════════════
— Используй тире (—) для списков внутри пунктов
— Заголовки пунктов пиши ЗАГЛАВНЫМИ БУКВАМИ
— Пиши развёрнуто — минимум 3–5 предложений на каждый пункт
— Текст должен читаться как статья, а не как таблица

ГЛАВНАЯ ЦЕЛЬ: найти реальные группы людей, которых можно достать через таргет, контент, партнёрства, геолокацию, поисковые запросы. Каждый сегмент должен быть находимым через маркетинг.

ОБЯЗАТЕЛЬНО выдели ровно 4 сегмента ЦА. Не меньше, не больше. Для каждого используй строго этот формат:

═══════════════════════════════════
🎯 СЕГМЕНТ [N] — [ЯРКОЕ НАЗВАНИЕ]
═══════════════════════════════════

👤 КТО ЭТО
[Подробный живой портрет: кто платит, кто пользуется, возраст, статус, чем занимается, как выглядит обычный день. Минимум 4 предложения.]

🌍 ЖИЗНЕННАЯ СИТУАЦИЯ
[Что конкретно происходит в их жизни прямо сейчас, из-за чего они вообще начали думать об этом. Конкретный момент, не общее описание. Минимум 3 предложения.]

⚡ ЗАДАЧА (JTBD)
[Одна чёткая фраза — что они «нанимают» твой продукт сделать. Начинай с глагола.]

😰 ГЛАВНАЯ БОЛЬ
[Конкретная проблема с контекстом — почему возникла, как долго существует, как мешает жизни. Минимум 4 предложения.]

🔄 ЧТО УЖЕ ПРОБОВАЛИ
— [альтернатива 1 и почему не подошла]
— [альтернатива 2 и почему не подошла]
— [альтернатива 3 и почему не подошла]

🚧 ЧТО ОСТАНАВЛИВАЕТ ОТ ПОКУПКИ
— [конкретное возражение 1]
— [конкретное возражение 2]
— [конкретное возражение 3]

💥 ТРИГГЕР ПРИНЯТИЯ РЕШЕНИЯ
[Одна фраза — конкретное событие или момент, который стал последней каплей.]

🏆 ЖЕЛАЕМЫЙ РЕЗУЛЬТАТ
[Как они сами описывают идеальный исход — их словами, не маркетинговыми фразами.]

📣 КАК НАЙТИ ЧЕРЕЗ МАРКЕТИНГ

Таргет:
— Площадка: [название]
— Интересы: [конкретные интересы для настройки]
— Группы: [конкретные сообщества]

Поисковые запросы (минимум 5):
1. "[запрос]"
2. "[запрос]"
3. "[запрос]"
4. "[запрос]"
5. "[запрос]"

Геолокация:
— [конкретные места где бывает]

Партнёрства:
— [конкретные партнёры]

Контент (3–4 темы):
— [тема 1 с форматом]
— [тема 2 с форматом]
— [тема 3 с форматом]

После всех 4 сегментов добавь:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ИТОГИ И СЛЕДУЮЩИЕ ШАГИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🥇 С КОГО НАЧАТЬ НАБОР
[Сегмент + 4 конкретные причины почему именно он]

💰 КТО ДАЁТ СТАБИЛЬНЫЕ ДЕНЬГИ НА ДИСТАНЦИИ
[Сегмент + объяснение]

🚀 ЧТО ЗАПУСТИТЬ ПЕРВЫМ
[Конкретный канал + готовый посыл рекламы в 2 предложения]

🛠 КАК ИСПОЛЬЗОВАТЬ ЭТОТ АНАЛИЗ
— Рекламные тексты: [конкретный совет]
— Контент-план: [конкретный совет]
— Скрипт продаж: [конкретный совет]
— Офлайн: [конкретный совет]

❓ ЧЕГО НЕ ХВАТАЕТ ДЛЯ ПОЛНОГО АНАЛИЗА
[Что изучить дополнительно]""",

    "uz": """Siz bozorni o'rganish va maqsadli auditoriyani segmentatsiya qilish bo'yicha ekspertsiz. Faqat haqiqiy ma'lumotlar bilan ishlaysiz. Hech qachon hech narsa o'ylab topmaysiz. FAQAT o'zbek tilida (lotincha) javob bering.

FORMATLASH HAQIDA MUHIM:
— Tajribali kopirayter kabi yozing — jonli, aniq, xarakterli
— Segment sarlavhalarida emoji ishlating
— Har bir bandni yangi qatordan boshlang
— Segmentlar orasiga ═══════════════════ ajratuvchi qo'ying
— Ro'yxatlarda tire (—) ishlating
— Band sarlavhalarini BOSH HARFLAR bilan yozing
— Har bir bandga kamida 3–5 ta gap yozing
— Matn jadval emas, maqola kabi o'qilishi kerak

ASOSIY MAQSAD: targetli reklama, kontent, hamkorliklar, geolokatsiya, qidiruv so'rovlari orqali topish mumkin bo'lgan real odamlar guruhlarini topish.

MAJBURIY ravishda aynan 4 ta maqsadli auditoriya segmentini ajrating. Har biri uchun qat'iy ushbu formatdan foydalaning:

═══════════════════════════════════
🎯 SEGMENT [N] — [YORQIN NOMI]
═══════════════════════════════════

👤 BU KIM
[Batafsil jonli portret: kim to'laydi, kim foydalanadi, yosh, maqom, nima qiladi, oddiy kun qanday o'tadi. Kamida 4 ta gap.]

🌍 HAYOTIY VAZIYAT
[Hozir hayotida nima sodir bo'lyapti, nima uchun bu haqda o'ylashni boshladi. Aniq lahza. Kamida 3 ta gap.]

⚡ VAZIFA (JTBD)
[Bir aniq jumla — mahsulotni nima qilish uchun «yollashadi». Fe'ldan boshlang.]

😰 ASOSIY OG'RIQ
[Kontekst bilan aniq muammo — qachon paydo bo'lgan, qancha davom etmoqda, hayotga qanday xalaqit bermoqda. Kamida 4 ta gap.]

🔄 NIMA SINAB KO'RISHGAN
— [muqobil 1 va nima uchun mos kelmagan]
— [muqobil 2 va nima uchun mos kelmagan]
— [muqobil 3 va nima uchun mos kelmagan]

🚧 NIMA TO'XTATADI
— [aniq e'tiroz 1]
— [aniq e'tiroz 2]
— [aniq e'tiroz 3]

💥 QAROR QABUL QILISH TRIGGERI
[Bir jumla — oxirgi tomchi bo'lgan aniq voqea yoki lahza.]

🏆 ISTALGAN NATIJA
[O'z so'zlari bilan ideal natijani qanday tasvirlaydi — marketing iboralari emas.]

📣 MARKETING ORQALI QANDAY TOPISH

Target:
— Platforma: [nomi]
— Qiziqishlar: [sozlash uchun aniq qiziqishlar]
— Guruhlar: [aniq jamoalar]

Qidiruv so'rovlari (kamida 5 ta):
1. "[so'rov]"
2. "[so'rov]"
3. "[so'rov]"
4. "[so'rov]"
5. "[so'rov]"

Geolokatsiya:
— [bo'ladigan aniq joylar]

Hamkorliklar:
— [aniq hamkorlar]

Kontent (3–4 mavzu):
— [mavzu 1 format bilan]
— [mavzu 2 format bilan]
— [mavzu 3 format bilan]

Barcha 4 segmentdan keyin qo'shing:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 YAKUNLAR VA KEYINGI QADAMLAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🥇 KIMDAN BOSHLASH
[Segment + 4 ta aniq sabab]

💰 KIM UZOQ MUDDATDA BARQAROR PUL KELTIRADI
[Segment + tushuntirish]

🚀 BIRINCHI NIMA ISHGA TUSHIRISH
[Aniq kanal + 2 jumlada reklama matni]

🛠 BU TAHLILDAN QANDAY FOYDALANISH
— Reklama matnlari: [aniq maslahat]
— Kontent-reja: [aniq maslahat]
— Sotish skripti: [aniq maslahat]
— Oflayn: [aniq maslahat]

❓ TO'LIQ TAHLIL UCHUN NIMA YETISHMAYDI
[Qo'shimcha o'rganish kerak bo'lgan narsa]"""
}


def get_lang(context):
    return context.user_data.get("lang", "ru")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")
    ]]
    await update.message.reply_text(
        "Выбери язык / Tilni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = get_lang(context)
    t = TEXTS[lang]

    if data.startswith("lang_"):
        chosen = data.split("_")[1]
        context.user_data["lang"] = chosen
        lang = chosen
        t = TEXTS[lang]
        keyboard = [[InlineKeyboardButton(t["start_btn"], callback_data="begin")]]
        await query.edit_message_text(
            t["welcome"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "begin":
        context.user_data["step"] = 0
        context.user_data["answers"] = []
        msg = ("✅ Начинаем!\n\nОтвечай развёрнуто — чем подробнее, тем точнее результат."
               if lang == "ru" else
               "✅ Boshlaymiz!\n\nBatafsil yozing — qanchalik to'liq bo'lsa, natija shunchalik aniq bo'ladi.")
        await query.edit_message_text(msg)
        await send_question(query.message, context)

    elif data == "restart":
        context.user_data["step"] = 0
        context.user_data["answers"] = []
        await query.edit_message_text(t["restart_msg"])
        await send_question(query.message, context)

    elif data == "change_lang":
        context.user_data.clear()
        keyboard = [[
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")
        ]]
        await query.edit_message_text(
            "Выбери язык / Tilni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def send_question(message, context):
    lang = get_lang(context)
    step = context.user_data.get("step", 0)
    questions = QUESTIONS[lang]
    t = TEXTS[lang]

    if step >= len(questions):
        return

    q = questions[step]
    total = len(questions)
    progress = "▓" * (step + 1) + "░" * (total - step - 1)

    text = (
        f"{progress}  {step + 1}/{total}\n\n"
        f"{q['num']}. {q['q']}\n\n"
        f"{q['hint']}\n\n"
        f"{q['example']}\n\n"
        f"{t['answer_prompt']}"
    )

    await message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    t = TEXTS[lang]

    if "step" not in context.user_data:
        await update.message.reply_text(t["no_session"])
        return

    step = context.user_data.get("step", 0)
    questions = QUESTIONS[lang]

    if step >= len(questions):
        return

    answer = update.message.text.strip()
    if len(answer) < 20:
        await update.message.reply_text(t["too_short"])
        return

    answers = context.user_data.get("answers", [])
    answers.append(answer)
    context.user_data["answers"] = answers
    context.user_data["step"] = step + 1

    if step + 1 >= len(questions):
        await update.message.reply_text(t["analyzing"])
        await run_analysis(update, context)
    else:
        await send_question(update.message, context)


async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    t = TEXTS[lang]
    answers = context.user_data.get("answers", [])
    questions = QUESTIONS[lang]

    pairs = "\n\n".join([
        f"{q['num']}. {q['q']}\nОтвет: {a}"
        for q, a in zip(questions, answers)
    ])

    user_msg = f"Данные о нише:\n\n{pairs}\n\nВыполни полный анализ. ОБЯЗАТЕЛЬНО выдай все 4 сегмента ЦА полностью, не останавливайся на середине."

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8000,
            system=SYSTEM_PROMPT[lang],
            messages=[{"role": "user", "content": user_msg}]
        )

        result = response.content[0].text

        await update.message.reply_text(t["done"])

        # Отправляем по сегментам — разбиваем по разделителю
        chunk_size = 3800
        chunks = []
        current = ""

        for line in result.split("\n"):
            if len(current) + len(line) + 1 > chunk_size:
                if current.strip():
                    chunks.append(current.strip())
                current = line + "\n"
            else:
                current += line + "\n"

        if current.strip():
            chunks.append(current.strip())

        for chunk in chunks:
            if chunk:
                await update.message.reply_text(chunk)

        keyboard = [
            [InlineKeyboardButton(t["restart_btn"], callback_data="restart")],
            [InlineKeyboardButton(t["change_lang_btn"], callback_data="change_lang")]
        ]
        await update.message.reply_text(
            t["footer"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        error_msg = f"❌ Ошибка API: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        await update.message.reply_text(error_msg)


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    t = TEXTS[lang]
    context.user_data["step"] = 0
    context.user_data["answers"] = []
    await update.message.reply_text(t["restart_msg"])
    await send_question(update.message, context)


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")
    ]]
    await update.message.reply_text(
        "Выбери язык / Tilni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def main():
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info(f"Health server started on port {PORT}")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("restart", restart_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started successfully!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
