import os
import logging
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
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@azamatislamgaliev")

client = Anthropic(api_key=ANTHROPIC_KEY)

TEXTS = {
    "ru": {
        "choose_lang": "Выбери язык / Tilni tanlang:",
        "welcome": (
            "👋 Привет! Я помогу найти твою целевую аудиторию.\n\n"
            "📋 Как это работает:\n"
            "1. Отвечаешь на 8 вопросов о своей нише\n"
            "2. ИИ анализирует рынок и находит сегменты ЦА\n"
            "3. Получаешь готовый разбор с инструкцией по маркетингу\n\n"
            "Пиши развёрнуто — чем подробнее, тем точнее результат.\n\n"
            "Нажми кнопку чтобы начать 👇"
        ),
        "start_btn": "🚀 Начать анализ",
        "not_subscribed": (
            "⚠️ Чтобы использовать бота, подпишись на канал:\n"
            "👉 @azamatislamgaliev\n\n"
            "После подписки нажми кнопку ниже 👇"
        ),
        "check_btn": "✅ Я подписался",
        "still_not": (
            "❌ Подписка не найдена.\n"
            "Подпишись на @azamatislamgaliev и попробуй снова."
        ),
        "analyzing": "⏳ ИИ анализирует вашу нишу. Это займёт 1–2 минуты...",
        "done": "✅ Анализ готов! Вот твои сегменты ЦА:",
        "restart_btn": "🔄 Новая ниша",
        "restart_msg": "Хорошо, начинаем заново! Нажми кнопку:",
        "start_again_btn": "🚀 Начать анализ",
        "error": "❌ Произошла ошибка. Попробуй ещё раз — /start",
        "answer_prompt": "Напиши свой ответ 👇",
        "min_length": "✏️ Напиши хотя бы 2–3 предложения — так анализ будет точнее.",
        "lang_changed": "Язык изменён на Русский 🇷🇺",
    },
    "uz": {
        "choose_lang": "Выбери язык / Tilni tanlang:",
        "welcome": (
            "👋 Salom! Men sizga maqsadli auditoriyangizni topishga yordam beraman.\n\n"
            "📋 Qanday ishlaydi:\n"
            "1. Nichangiz haqida 8 ta savolga javob berasiz\n"
            "2. AI bozorni tahlil qiladi va segmentlarni topadi\n"
            "3. Marketing bo'yicha ko'rsatmalar bilan tayyor tahlilni olasiz\n\n"
            "Batafsil yozing — qanchalik to'liq bo'lsa, natija shunchalik aniq bo'ladi.\n\n"
            "Boshlash uchun tugmani bosing 👇"
        ),
        "start_btn": "🚀 Tahlilni boshlash",
        "not_subscribed": (
            "⚠️ Botdan foydalanish uchun kanalga obuna bo'ling:\n"
            "👉 @azamatislamgaliev\n\n"
            "Obuna bo'lgandan so'ng quyidagi tugmani bosing 👇"
        ),
        "check_btn": "✅ Obuna bo'ldim",
        "still_not": (
            "❌ Obuna topilmadi.\n"
            "@azamatislamgaliev ga obuna bo'ling va qayta urinib ko'ring."
        ),
        "analyzing": "⏳ AI nichangizni tahlil qilmoqda. Bu 1–2 daqiqa vaqt oladi...",
        "done": "✅ Tahlil tayyor! Mana sizning maqsadli auditoriya segmentlaringiz:",
        "restart_btn": "🔄 Yangi nicha",
        "restart_msg": "Yaxshi, qaytadan boshlaymiz! Tugmani bosing:",
        "start_again_btn": "🚀 Tahlilni boshlash",
        "error": "❌ Xatolik yuz berdi. Qayta urinib ko'ring — /start",
        "answer_prompt": "Javobingizni yozing 👇",
        "min_length": "✏️ Kamida 2–3 ta gap yozing — shunda tahlil aniqroq bo'ladi.",
        "lang_changed": "Til o'zgartirildi: O'zbek tili 🇺🇿",
    }
}

QUESTIONS = {
    "ru": [
        {
            "num": "01",
            "q": "Чем ты занимаешься и что именно продаёшь?",
            "hint": "Опиши своими словами: что это, в каком формате — офлайн или онлайн, услуга или продукт, для кого.",
            "example": "Офлайн-школа игры на фортепиано. Занятия в студии один на один с преподавателем. Берём детей от 5 лет и взрослых любого возраста."
        },
        {
            "num": "02",
            "q": "Как устроен процесс — что получает клиент?",
            "hint": "Опиши шаги от первого контакта до результата. Что входит, сколько длится.",
            "example": "Урок 45 минут, 1–2 раза в неделю. Пробный урок 500 руб. Индивидуальная программа — классика или популярные песни."
        },
        {
            "num": "03",
            "q": "В чём твоё отличие от конкурентов?",
            "hint": "Что есть у тебя, чего нет у других — у частных специалистов, других школ, похожих сервисов?",
            "example": "Единственная школа в районе, где с нуля сразу играют любимые песни — без зубрёжки нот. Плюс удобная парковка."
        },
        {
            "num": "04",
            "q": "Где ты находишься или в каком регионе работаешь?",
            "hint": "Если офлайн — город, район, ориентиры. Если онлайн — на какую аудиторию ориентируешься.",
            "example": "Москва, район Митино. Рядом метро и крупный ТЦ. Работаем с жителями района."
        },
        {
            "num": "05",
            "q": "Какую реальную ситуацию клиента ты решаешь?",
            "hint": "Что происходит в жизни человека ДО того, как он находит тебя. Не эмоцию — конкретную ситуацию.",
            "example": "Родители хотят отдать ребёнка в музыкальную школу, но боятся государственной — там строго, дети плачут и бросают."
        },
        {
            "num": "06",
            "q": "Кто уже является твоим клиентом?",
            "hint": "Если клиенты есть — кто они, зачем пришли. Если нет — так и напиши.",
            "example": "Дети 6–12 лет, которых приводят мамы. Несколько взрослых: женщина 42 года «для души», мужчина 35 лет — на корпоративы."
        },
        {
            "num": "07",
            "q": "Какая у тебя цена и формат оплаты?",
            "hint": "Стоимость, есть ли абонемент, пробный период, рассрочка.",
            "example": "Абонемент 8 уроков — 9 600 руб. Разовый — 1 400 руб. Первый пробный — 500 руб."
        },
        {
            "num": "08",
            "q": "Как сейчас к тебе приходят клиенты?",
            "hint": "Откуда узнают о тебе прямо сейчас. Что работает, что пробовал и не сработало.",
            "example": "В основном сарафанное радио и Яндекс.Карты. Instagram не ведём. Таргет не запускали."
        }
    ],
    "uz": [
        {
            "num": "01",
            "q": "Siz nima bilan shug'ullanasiz va nima sotasiz?",
            "hint": "O'z so'zlaringiz bilan: bu nima, qanday formatda — oflayn yoki onlayn, xizmat yoki mahsulot, kim uchun.",
            "example": "Oflayn fortepiano maktabi. Darslar studiyada o'qituvchi bilan bir-birga. 5 yoshdan bolalar va kattalarga qabul qilamiz."
        },
        {
            "num": "02",
            "q": "Jarayon qanday tashkil etilgan — mijoz nima oladi?",
            "hint": "Birinchi murojaaтdan natijaga qadar bosqichlarni tavsiflang. Nima kiradi, qancha davom etadi.",
            "example": "Dars 45 daqiqa, haftasiga 1–2 marta. Sinov darsi 20 000 so'm. Individual dastur — klassika yoki sevimli qo'shiqlar."
        },
        {
            "num": "03",
            "q": "Raqobatchilardan farqingiz nimada?",
            "hint": "Sizda bor, boshqalarda yo'q narsa — xususiy mutaxassislar, boshqa maktablar, o'xshash xizmatlar.",
            "example": "Hududdagi yagona maktabmizki, noldan boshlagan holda darhol sevimli qo'shiqlarni o'ynash mumkin. Qulay avtoturargoh ham bor."
        },
        {
            "num": "04",
            "q": "Siz qayerda joylashgansiz yoki qaysi mintaqada ishlaysiz?",
            "hint": "Oflayn bo'lsa — shahar, tuman, mo'ljallar. Onlayn bo'lsa — qaysi auditoriyaga yo'naltirilgansiz.",
            "example": "Toshkent, Yunusobod tumani. Yaqinda metro va yirik savdo markazi. Tuman aholisi bilan ishlaymiz."
        },
        {
            "num": "05",
            "q": "Mijozning qaysi real vaziyatini hal qilasiz?",
            "hint": "Siz topishdan OLDIN odamning hayotida nima sodir bo'lishini tasvirlab bering. Aniq vaziyatni.",
            "example": "Ota-onalar farzandini musiqa maktabiga bermoqchi, lekin davlat maktabidan qo'rqishadi — u yerda qattiq, bolalar yig'lab ketishadi."
        },
        {
            "num": "06",
            "q": "Sizning mijozlaringiz kim?",
            "hint": "Agar mijozlar bor bo'lsa — ular kim, nima uchun kelishgan. Yo'q bo'lsa — shunday yozing.",
            "example": "Asosan onalar olib keladigan 6–12 yoshli bolalar. 42 yoshli ayol 'o'zi uchun', 35 yoshli erkak korporativlar uchun."
        },
        {
            "num": "07",
            "q": "Narxingiz va to'lov formatingiz qanday?",
            "hint": "Narx, obuna, sinov muddati, bo'lib to'lash — xarid qaroriga ta'sir qiladigan hamma narsa.",
            "example": "8 darsga abonement — 320 000 so'm. Bir martalik — 55 000 so'm. Birinchi sinov — 20 000 so'm."
        },
        {
            "num": "08",
            "q": "Hozir mijozlar sizga qanday keladi?",
            "hint": "Ular hozir siz haqingizda qayerdan bilib olishadi. Nima ishlaydi, nima sinab ko'rildi va ishlamadi.",
            "example": "Asosan og'izdan-og'izga va Yandex.Xaritalar. Instagramni yuritmaymiz. Targetli reklamani ishlatmadik."
        }
    ]
}

SYSTEM_PROMPT = {
    "ru": """Ты — эксперт по исследованию рынка и сегментации целевой аудитории.
Работаешь исключительно с реальными данными. Никогда ничего не выдумываешь.
Отвечай ТОЛЬКО на русском языке.

ГЛАВНАЯ ЦЕЛЬ: найти реальные группы людей, которых можно достать через таргет, контент, партнёрства, геолокацию, поисковые запросы.

Выдели 3–5 сегментов ЦА. Для каждого:

════════════════════════════════════
СЕГМЕНТ [N] — [НАЗВАНИЕ]
════════════════════════════════════
1. КТО ЭТО — портрет (кто платит, кто пользуется, возраст, статус)
2. ЖИЗНЕННАЯ СИТУАЦИЯ — что происходит прямо сейчас, почему ищут
3. ЗАДАЧА (JTBD) — одна фраза, начни с глагола
4. ГЛАВНАЯ БОЛЬ — конкретно с контекстом
5. ЧТО УЖЕ ПРОБОВАЛИ — альтернативы и почему не подошли
6. ЧТО ОСТАНАВЛИВАЕТ — конкретные возражения
7. ТРИГГЕР — одна фраза, что стало последней каплей
8. ЖЕЛАЕМЫЙ РЕЗУЛЬТАТ — словами самого клиента
9. КАК НАЙТИ ЧЕРЕЗ МАРКЕТИНГ:
   а) Таргет (площадка, интересы, группы)
   б) Поисковые запросы — минимум 5 конкретных
   в) Геолокация — где физически бывает
   г) Партнёрства — с кем договориться
   д) Контент — 3–4 темы

После сегментов:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ИТОГИ И СЛЕДУЮЩИЕ ШАГИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
С КОГО НАЧАТЬ НАБОР: [сегмент + причины]
КТО ДАЁТ СТАБИЛЬНЫЕ ДЕНЬГИ: [сегмент]
ЧТО ЗАПУСТИТЬ ПЕРВЫМ: [канал + посыл в 2 предложения]
КАК ИСПОЛЬЗОВАТЬ: рекламные тексты / контент-план / скрипт / офлайн
ЧЕГО НЕ ХВАТАЕТ: [что изучить дополнительно]

Пиши подробно и конкретно. Никаких абстракций.""",

    "uz": """Siz bozorni o'rganish va maqsadli auditoriyani segmentatsiya qilish bo'yicha ekspertsiz.
Faqat haqiqiy ma'lumotlar bilan ishlaysiz. Hech qachon hech narsa o'ylab topmasligingiz kerak.
FAQAT o'zbek tilida (lotincha) javob bering.

ASOSIY MAQSAD: targetli reklama, kontent, hamkorliklar, geolokatsiya, qidiruv so'rovlari orqali topish mumkin bo'lgan real odamlar guruhlarini topish.

3–5 ta maqsadli auditoriya segmentini ajrating. Har biri uchun:

════════════════════════════════════
SEGMENT [N] — [NOMI]
════════════════════════════════════
1. BU KIM — portret (kim to'laydi, kim foydalanadi, yosh, maqom)
2. HAYOTIY VAZIYAT — hozir nima bo'lyapti, nima uchun qidirmoqda
3. VAZIFA (JTBD) — bir jumla, fe'ldan boshlang
4. ASOSIY OG'RIQ — aniq kontekst bilan
5. NIMA SINAB KO'RISHGAN — muqobillar va nima uchun mos kelmagan
6. NIMA TO'XTATADI — aniq e'tirozlar
7. TRIGGER — oxirgi tomchi bo'lgan bir jumla
8. ISTALGAN NATIJA — mijozning o'z so'zlari bilan
9. MARKETING ORQALI QANDAY TOPISH:
   a) Target (platforma, qiziqishlar, guruhlar)
   b) Qidiruv so'rovlari — kamida 5 ta aniq
   v) Geolokatsiya — jismonan qayerda bo'ladi
   g) Hamkorliklar — kim bilan kelishish mumkin
   d) Kontent — 3–4 ta mavzu

Segmentlardan keyin:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YAKUNLAR VA KEYINGI QADAMLAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KIMDAN BOSHLASH: [segment + sabablar]
KIM BARQAROR PUL KELTIRADI: [segment]
BIRINCHI NIMA ISHGA TUSHIRISH: [kanal + 2 jumlada matn]
QANDAY FOYDALANISH: reklama matni / kontent-reja / skript / oflayn
NIMA YETISHMAYDI: [qo'shimcha o'rganish kerak]

Batafsil va aniq yozing. Hech qanday abstraktsiya yo'q."""
}


def get_lang(context):
    return context.user_data.get("lang", "ru")


def get_step(context):
    return context.user_data.get("step", 0)


def get_answers(context):
    return context.user_data.get("answers", [])


async def check_subscription(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выбери язык / Tilni tanlang:",
        reply_markup=reply_markup
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = get_lang(context)
    t = TEXTS[lang]

    if data.startswith("lang_"):
        chosen_lang = data.split("_")[1]
        context.user_data["lang"] = chosen_lang
        lang = chosen_lang
        t = TEXTS[lang]

        is_subscribed = await check_subscription(query.message.chat.bot, query.from_user.id)
        if not is_subscribed:
            keyboard = [[InlineKeyboardButton(t["check_btn"], callback_data="check_sub")]]
            await query.edit_message_text(
                t["not_subscribed"],
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        keyboard = [[InlineKeyboardButton(t["start_btn"], callback_data="begin")]]
        await query.edit_message_text(
            t["welcome"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "check_sub":
        is_subscribed = await check_subscription(query.message.chat.bot, query.from_user.id)
        if not is_subscribed:
            keyboard = [[InlineKeyboardButton(t["check_btn"], callback_data="check_sub")]]
            await query.edit_message_text(
                t["still_not"],
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        keyboard = [[InlineKeyboardButton(t["start_btn"], callback_data="begin")]]
        await query.edit_message_text(
            t["welcome"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "begin":
        context.user_data["step"] = 0
        context.user_data["answers"] = []
        await send_question(query.message, context, edit=True)

    elif data == "restart":
        context.user_data["step"] = 0
        context.user_data["answers"] = []
        keyboard = [[InlineKeyboardButton(t["start_again_btn"], callback_data="begin")]]
        await query.edit_message_text(
            t["restart_msg"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "change_lang":
        keyboard = [
            [
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")
            ]
        ]
        await query.edit_message_text(
            "Выбери язык / Tilni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def send_question(message, context, edit=False):
    lang = get_lang(context)
    step = get_step(context)
    questions = QUESTIONS[lang]
    t = TEXTS[lang]

    if step >= len(questions):
        return

    q = questions[step]
    total = len(questions)

    progress = "▓" * (step + 1) + "░" * (total - step - 1)
    text = (
        f"*{progress}* {step + 1}/{total}\n\n"
        f"*{q['num']}. {q['q']}*\n\n"
        f"_{q['hint']}_\n\n"
        f"💡 {q['example']}\n\n"
        f"{t['answer_prompt']}"
    )

    if edit:
        await message.edit_text(text, parse_mode="Markdown")
    else:
        await message.reply_text(text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    t = TEXTS[lang]

    if "step" not in context.user_data:
        await update.message.reply_text("Напиши /start чтобы начать.")
        return

    step = get_step(context)
    questions = QUESTIONS[lang]

    if step >= len(questions):
        return

    answer = update.message.text.strip()
    if len(answer) < 20:
        await update.message.reply_text(t["min_length"])
        return

    answers = get_answers(context)
    answers.append(answer)
    context.user_data["answers"] = answers
    context.user_data["step"] = step + 1

    if step + 1 >= len(questions):
        await update.message.reply_text(t["analyzing"])
        await run_analysis(update, context)
    else:
        await send_question(update.message, context, edit=False)


async def run_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    t = TEXTS[lang]
    answers = get_answers(context)
    questions = QUESTIONS[lang]

    pairs = "\n\n".join([
        f"{q['num']}. {q['q']}\nОтвет: {a}"
        for q, a in zip(questions, answers)
    ])

    user_message = f"Данные о нише:\n\n{pairs}\n\nВыполни полный анализ целевой аудитории."

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM_PROMPT[lang],
            messages=[{"role": "user", "content": user_message}]
        )

        result = response.content[0].text

        await update.message.reply_text(t["done"])

        chunk_size = 4000
        for i in range(0, len(result), chunk_size):
            chunk = result[i:i + chunk_size]
            await update.message.reply_text(chunk)

        keyboard = [
            [InlineKeyboardButton(t["restart_btn"], callback_data="restart")],
            [InlineKeyboardButton("🌐 Сменить язык / Tilni o'zgartirish", callback_data="change_lang")]
        ]
        await update.message.reply_text(
            "─────────────────\n@azamatislamgaliev",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        await update.message.reply_text(t["error"])


async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    t = TEXTS[lang]
    context.user_data["step"] = 0
    context.user_data["answers"] = []
    keyboard = [[InlineKeyboardButton(t["start_again_btn"], callback_data="begin")]]
    await update.message.reply_text(
        t["restart_msg"],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")
        ]
    ]
    await update.message.reply_text(
        "Выбери язык / Tilni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("restart", restart_command))
    app.add_handler(CommandHandler("lang", lang_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
