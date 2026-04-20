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

client = Anthropic(api_key=ANTHROPIC_KEY)

TEXTS = {
    "ru": {
        "welcome": (
            "👋 Привет!\n\n"
            "Этот бот поможет тебе найти свою целевую аудиторию.\n\n"
            "🎯 *Что делает бот:*\n"
            "Ты отвечаешь на 8 вопросов о своей нише, а ИИ анализирует рынок и выдаёт подробный разбор сегментов ЦА — с портретами клиентов, их болями, триггерами и готовыми инструкциями по маркетингу.\n\n"
            "📌 *Что получишь:*\n"
            "— Кто твой клиент и как он живёт\n"
            "— Что его останавливает от покупки\n"
            "— Где его найти: таргет, поиск, геолокация\n"
            "— Готовый посыл для рекламы\n\n"
            "Нажми кнопку чтобы начать 👇"
        ),
        "start_btn": "🚀 Начать анализ",
        "analyzing": "⏳ ИИ анализирует твою нишу...\n\nЭто займёт около 1–2 минут. Пожалуйста, подожди.",
        "done": "✅ *Анализ готов!* Вот твои сегменты целевой аудитории:",
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
            "🎯 *Bot nima qiladi:*\n"
            "Siz nichangiz haqida 8 ta savolga javob berasiz, AI bozorni tahlil qiladi va mijozlar segmentlari bo'yicha batafsil tahlil beradi — portretlar, og'riqlar, triggerlar va marketing bo'yicha tayyor ko'rsatmalar bilan.\n\n"
            "📌 *Natijada nima olasiz:*\n"
            "— Mijozingiz kim va qanday yashaydi\n"
            "— Uni sotib olishdan nima to'xtatadi\n"
            "— Uni qayerdan topish: target, qidiruv, geolokatsiya\n"
            "— Reklama uchun tayyor matn\n\n"
            "Boshlash uchun tugmani bosing 👇"
        ),
        "start_btn": "🚀 Tahlilni boshlash",
        "analyzing": "⏳ AI nichangizni tahlil qilmoqda...\n\nBu taxminan 1–2 daqiqa vaqt oladi. Iltimos, kuting.",
        "done": "✅ *Tahlil tayyor!* Mana sizning maqsadli auditoriya segmentlaringiz:",
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
        {
            "num": "01",
            "q": "Чем ты занимаешься и что именно продаёшь?",
            "hint": "Опиши своими словами: что это, в каком формате — офлайн или онлайн, услуга или продукт, для кого.",
            "example": "💡 Пример: Офлайн-школа игры на фортепиано. Занятия в студии один на один с преподавателем. Берём детей от 5 лет и взрослых любого возраста."
        },
        {
            "num": "02",
            "q": "Как устроен процесс — что получает клиент?",
            "hint": "Опиши шаги от первого контакта до результата. Что входит, сколько длится.",
            "example": "💡 Пример: Урок 45 минут, 1–2 раза в неделю. Пробный урок 50 000 сум. Индивидуальная программа — классика или популярные песни."
        },
        {
            "num": "03",
            "q": "В чём твоё отличие от конкурентов?",
            "hint": "Что есть у тебя, чего нет у других — у частных специалистов, других школ, похожих сервисов?",
            "example": "💡 Пример: Единственная школа в районе, где с нуля сразу играют любимые песни — без зубрёжки нот. Плюс удобная парковка."
        },
        {
            "num": "04",
            "q": "Где ты находишься или в каком регионе работаешь?",
            "hint": "Если офлайн — город, район, ориентиры. Если онлайн — на какую аудиторию ориентируешься.",
            "example": "💡 Пример: Ташкент, Юнусабадский район. Рядом метро и крупный ТЦ. Работаем с жителями района."
        },
        {
            "num": "05",
            "q": "Какую реальную ситуацию клиента ты решаешь?",
            "hint": "Что происходит в жизни человека ДО того, как он находит тебя. Не эмоцию — конкретную ситуацию.",
            "example": "💡 Пример: Родители хотят отдать ребёнка в музыкальную школу, но боятся государственной — там строго, дети плачут и бросают."
        },
        {
            "num": "06",
            "q": "Кто уже является твоим клиентом?",
            "hint": "Если клиенты есть — кто они, зачем пришли. Если нет — так и напиши.",
            "example": "💡 Пример: Дети 6–12 лет, которых приводят мамы. Несколько взрослых: женщина 42 года «для души», мужчина 35 лет — на корпоративы."
        },
        {
            "num": "07",
            "q": "Какая у тебя цена и формат оплаты?",
            "hint": "Стоимость в сумах, есть ли абонемент, пробный период, рассрочка.",
            "example": "💡 Пример: Абонемент 8 уроков — 800 000 сум. Разовый — 120 000 сум. Первый пробный — 50 000 сум."
        },
        {
            "num": "08",
            "q": "Как сейчас к тебе приходят клиенты?",
            "hint": "Откуда узнают о тебе прямо сейчас. Что работает, что пробовал и не сработало.",
            "example": "💡 Пример: В основном сарафанное радио и Яндекс.Карты. Instagram не ведём. Таргет не запускали."
        }
    ],
    "uz": [
        {
            "num": "01",
            "q": "Siz nima bilan shug'ullanasiz va nima sotasiz?",
            "hint": "O'z so'zlaringiz bilan: bu nima, qanday formatda — oflayn yoki onlayn, xizmat yoki mahsulot, kim uchun.",
            "example": "💡 Misol: Oflayn fortepiano maktabi. Darslar studiyada o'qituvchi bilan bir-birga. 5 yoshdan bolalar va kattalarga qabul qilamiz."
        },
        {
            "num": "02",
            "q": "Jarayon qanday tashkil etilgan — mijoz nima oladi?",
            "hint": "Birinchi murojaaтdan natijaga qadar bosqichlarni tavsiflang.",
            "example": "💡 Misol: Dars 45 daqiqa, haftasiga 1–2 marta. Sinov darsi 50 000 so'm. Individual dastur — klassika yoki sevimli qo'shiqlar."
        },
        {
            "num": "03",
            "q": "Raqobatchilardan farqingiz nimada?",
            "hint": "Sizda bor, boshqalarda yo'q narsa — xususiy mutaxassislar, boshqa maktablar, o'xshash xizmatlar.",
            "example": "💡 Misol: Hududdagi yagona maktabmizki, noldan boshlagan holda darhol sevimli qo'shiqlarni o'ynash mumkin."
        },
        {
            "num": "04",
            "q": "Siz qayerda joylashgansiz yoki qaysi mintaqada ishlaysiz?",
            "hint": "Oflayn bo'lsa — shahar, tuman, mo'ljallar. Onlayn bo'lsa — qaysi auditoriyaga yo'naltirilgansiz.",
            "example": "💡 Misol: Toshkent, Yunusobod tumani. Yaqinda metro va savdo markazi."
        },
        {
            "num": "05",
            "q": "Mijozning qaysi real vaziyatini hal qilasiz?",
            "hint": "Siz topishdan OLDIN odamning hayotida nima sodir bo'lishini tasvirlab bering.",
            "example": "💡 Misol: Ota-onalar farzandini musiqa maktabiga bermoqchi, lekin davlat maktabidan qo'rqishadi."
        },
        {
            "num": "06",
            "q": "Sizning mijozlaringiz kim?",
            "hint": "Agar mijozlar bor bo'lsa — ular kim, nima uchun kelishgan. Yo'q bo'lsa — shunday yozing.",
            "example": "💡 Misol: Asosan onalar olib keladigan 6–12 yoshli bolalar. 42 yoshli ayol 'o'zi uchun', 35 yoshli erkak korporativlar uchun."
        },
        {
            "num": "07",
            "q": "Narxingiz va to'lov formatingiz qanday?",
            "hint": "So'mdagi narx, obuna, sinov muddati, bo'lib to'lash.",
            "example": "💡 Misol: 8 darsga abonement — 800 000 so'm. Bir martalik — 120 000 so'm. Sinov darsi — 50 000 so'm."
        },
        {
            "num": "08",
            "q": "Hozir mijozlar sizga qanday keladi?",
            "hint": "Ular hozir siz haqingizda qayerdan bilib olishadi. Nima ishlaydi, nima ishlamadi.",
            "example": "💡 Misol: Asosan og'izdan-og'izga va Yandex.Xaritalar. Instagramni yuritmaymiz."
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
Faqat haqiqiy ma'lumotlar bilan ishlaysiz. Hech qachon hech narsa o'ylab topmaysiz.
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
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "begin":
        context.user_data["step"] = 0
        context.user_data["answers"] = []
        await query.edit_message_text(
            "✅ Начинаем!\n\nОтвечай развёрнуто — чем подробнее, тем точнее результат."
            if lang == "ru" else
            "✅ Boshlaymiz!\n\nBatafsil yozing — qanchalik to'liq bo'lsa, natija shunchalik aniq bo'ladi."
        )
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
        f"*{q['num']}. {q['q']}*\n\n"
        f"_{q['hint']}_\n\n"
        f"{q['example']}\n\n"
        f"{t['answer_prompt']}"
    )

    await message.reply_text(text, parse_mode="Markdown")


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

    user_msg = f"Данные о нише:\n\n{pairs}\n\nВыполни полный анализ целевой аудитории."

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM_PROMPT[lang],
            messages=[{"role": "user", "content": user_msg}]
        )

        result = response.content[0].text

        await update.message.reply_text(t["done"], parse_mode="Markdown")

        chunk_size = 4000
        for i in range(0, len(result), chunk_size):
            await update.message.reply_text(result[i:i + chunk_size])

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
