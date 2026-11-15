from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)

from bot.pricing import (
    EXPLANATION_PRICE_STARS,
    FULL_TEST_PRICE_STARS,
    TEST_PRICE_STARS,
    TEST_QUESTIONS,
)

remove_keyboard = ReplyKeyboardRemove()

OPTION_LETTERS = ["A", "B", "C", "D", "E", "F"]

# Color per answer option (cyclic)
OPTION_COLORS = ["🔴", "🔵", "🟢", "🟡", "🟣", "🟠"]

# Color per subject slug
SUBJECT_COLORS = {
    "mathematics": "🔴",
    "physics":     "🔵",
    "english":     "🟢",
    "russian":     "🟡",
    "iq":          "🟣",
}

DIFF_LABELS = {"easy": "🟢 Лёгкая", "medium": "🟡 Средняя", "hard": "🔴 Сложная"}


# ─── User: main reply keyboard ────────────────────────────────────────────────

def main_menu(lang: str = "ru") -> ReplyKeyboardMarkup:
    labels = {
        "ru": [
            "🔥 Начать тест",   "📊 Статистика",
            "🌐 Язык",          "🌟 Поддержать",
            "💡 Помощь",        "💳 Платежи",
        ],
        "uz": [
            "🔥 Testni boshlash", "📊 Statistika",
            "🌐 Til",             "🌟 Qo'llab-quvvatlash",
            "💡 Yordam",          "💳 To'lovlar",
        ],
        "en": [
            "🔥 Start test",  "📊 Statistics",
            "🌐 Language",    "🌟 Support",
            "💡 Help",        "💳 Payments",
        ],
    }
    placeholders = {
        "ru": "Выберите действие…",
        "uz": "Harakatni tanlang…",
        "en": "Choose an action…",
    }
    b = labels.get(lang, labels["ru"])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=b[0]), KeyboardButton(text=b[1])],
            [KeyboardButton(text=b[2]), KeyboardButton(text=b[3])],
            [KeyboardButton(text=b[4]), KeyboardButton(text=b[5])],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=placeholders.get(lang, "Choose an action…"),
    )


def user_main_menu(lang: str = "ru") -> ReplyKeyboardMarkup:
    labels = {
        "ru": ["👤 Профиль", "🎯 Начать тест", "💎 Премиум", "🕘 История", "🎁 Подарок"],
        "uz": ["👤 Profil", "🎯 Test boshlash", "💎 Premium", "🕘 Tarix", "🎁 Sovg'a"],
        "en": ["👤 Profile", "🎯 Start test", "💎 Premium", "🕘 History", "🎁 Gift"],
    }
    buttons = labels.get(lang, labels["ru"])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=buttons[0]), KeyboardButton(text=buttons[1])],
            [KeyboardButton(text=buttons[2]), KeyboardButton(text=buttons[3])],
            [KeyboardButton(text=buttons[4])],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder={"ru": "Выберите действие", "uz": "Harakatni tanlang", "en": "Choose an action"}.get(lang, "Choose an action"),
    )


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 Назад", callback_data="user:main"),
    ]])


def result_questions_keyboard(
    result_id: int,
    total: int,
    unlock_price: int = EXPLANATION_PRICE_STARS,
    lang: str = "ru",
    unlock_subjects: list[tuple[str, str]] | None = None,
) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=str(index + 1), callback_data=f"review:{result_id}:{index}")
        for index in range(total)
    ]
    rows = [buttons[index:index + 5] for index in range(0, len(buttons), 5)]
    labels = {
        "ru": "🔓 Разбор {subject} — {price} ⭐",
        "en": "🔓 {subject} explanations — {price} ⭐",
        "uz": "🔓 {subject} tahlili — {price} ⭐",
    }
    for subject, title in unlock_subjects or []:
        rows.append([InlineKeyboardButton(
            text=labels.get(lang, labels["ru"]).format(subject=title, price=unlock_price)[:64],
            callback_data=f"unlock:{result_id}:{subject}:{unlock_price}",
        )])
    rows.append([
        InlineKeyboardButton(text="💎 Premium", callback_data="user:premium"),
        InlineKeyboardButton(text="🎯 Новый тест", callback_data="goto:test"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def premium_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 1 неделя — 200 ⭐", callback_data="sub:week")],
        [InlineKeyboardButton(text="🟡 1 месяц — 700 ⭐", callback_data="sub:month")],
        [InlineKeyboardButton(text="🔥 3 месяца — 2000 ⭐ · выгодно", callback_data="sub:quarter")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="user:main")],
    ])


def gift_keyboard(used_mocks: set[str] | None = None) -> InlineKeyboardMarkup:
    used = used_mocks or set()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'✅' if 'english' in used else '🎁'} Бесплатный мок: Английский (100)",
            callback_data="mock:english",
        )],
        [InlineKeyboardButton(
            text=f"{'✅' if 'mathematics' in used else '🎁'} Бесплатный мок: Математика (100)",
            callback_data="mock:mathematics",
        )],
        [InlineKeyboardButton(
            text=f"{'✅' if 'iq' in used else '🎁'} Бесплатный мок: IQ (100)",
            callback_data="mock:iq",
        )],
        [InlineKeyboardButton(text="🏷 Ввести промокод", callback_data="gift:promo")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="user:main")],
    ])


def test_size_keyboard(
    subject: str,
    amount: int,
    full_mock_price: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📝 Тест по предмету ({amount} вопросов) — {TEST_PRICE_STARS} ⭐",
            callback_data=f"testsize:{subject}:regular",
        )],
        [InlineKeyboardButton(
            text=f"🎯 Полный мок · 60 вопросов — {full_mock_price} ⭐",
            callback_data="testsize:all:full",
        )],
        [InlineKeyboardButton(text="⬅️ К предметам", callback_data="goto:test")],
    ])


def promo_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔙 В подарок", callback_data="user:gift"),
    ]])


def paid_test_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎯 Выбрать предмет", callback_data="goto:test"),
    ]])


def paid_full_test_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎯 Начать полный мок (60 вопросов)", callback_data="testsize:all:full"),
    ]])


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский · native", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇺🇿 O'zbek · navi", callback_data="lang:uz"),
        InlineKeyboardButton(text="🇬🇧 English · global", callback_data="lang:en"),
    ]])


def subject_keyboard(subjects: list[dict]) -> InlineKeyboardMarkup:
    """Subjects with colored emoji per slug."""
    rows = []
    for i in range(0, len(subjects), 2):
        s = subjects[i]
        clr = SUBJECT_COLORS.get(s["slug"], "⚪")
        label1 = f"{clr} {s['title']}"
        btn1 = InlineKeyboardButton(
            text=label1,
            callback_data=f"subject:{s['slug']}",
        )
        row = [btn1]
        if i + 1 < len(subjects):
            s2 = subjects[i + 1]
            clr2 = SUBJECT_COLORS.get(s2["slug"], "⚪")
            label2 = f"{clr2} {s2['title']}"
            btn2 = InlineKeyboardButton(
                text=label2,
                callback_data=f"subject:{s2['slug']}",
            )
            row.append(btn2)
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def test_choice_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    localized_labels = {
        "ru": ("Математика", "Английский", "IQ", "Полный мок"),
        "en": ("Mathematics", "English", "IQ", "Full mock"),
        "uz": ("Matematika", "Ingliz tili", "IQ", "To'liq mock"),
    }
    labels = localized_labels.get(lang, localized_labels["ru"])
    question_word = {"ru": "вопросов", "en": "questions", "uz": "savol"}.get(lang, "questions")
    subject_slugs = ("mathematics", "english", "iq")
    for slug, title in zip(subject_slugs, labels):
        color = SUBJECT_COLORS.get(slug, "⚪")
        rows.append([InlineKeyboardButton(
            text=f"{color} {title} · {TEST_QUESTIONS} {question_word} — {TEST_PRICE_STARS} ⭐",
            callback_data=f"testsize:{slug}:regular",
        )])
    rows.append([InlineKeyboardButton(
        text=f"🎯 {labels[3]} · 60 {question_word} — {FULL_TEST_PRICE_STARS} ⭐",
        callback_data="testsize:all:full",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def result_history_keyboard(results: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for result in results:
        date = str(result.get("finished_at", ""))[:10]
        label = f"{date} · {result['score']}/{result['total']}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"history:{result['id']}")])
    rows.append([InlineKeyboardButton(text="🔙 В меню", callback_data="user:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def answer_keyboard(question_id: int, options: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i, opt in enumerate(options):
        letter = OPTION_LETTERS[i] if i < len(OPTION_LETTERS) else str(i + 1)
        color  = OPTION_COLORS[i]  if i < len(OPTION_COLORS)  else "⚪"
        rows.append([InlineKeyboardButton(
            text=f"{color} {letter}) {opt}",
            callback_data=f"ans:{question_id}:{i}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def result_keyboard(lang: str) -> InlineKeyboardMarkup:
    labels = {"ru": "🔄 Новый тест", "uz": "🔄 Yangi test", "en": "🔄 New test"}
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=labels.get(lang, "🔄 Новый тест"), callback_data="goto:test"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="goto:stats"),
    ]])


def donation_confirm_keyboard(lang: str, amount: int) -> InlineKeyboardMarkup:
    labels = {
        "ru": f"🌟 Отправить {amount} Stars",
        "uz": f"🌟 {amount} Stars yuborish",
        "en": f"🌟 Send {amount} Stars",
    }
    cancel = {"ru": "❌ Отмена", "uz": "❌ Bekor qilish", "en": "❌ Cancel"}
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=labels.get(lang, f"🌟 {amount} Stars"), callback_data=f"donate_confirm:{amount}")],
        [InlineKeyboardButton(text=cancel.get(lang, "❌ Cancel"), callback_data="donate_cancel")],
    ])


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Нажмите для отмены",
    )


# ─── Admin panel keyboards ─────────────────────────────────────────────────────

def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Вопросы",       callback_data="adm:q"),
         InlineKeyboardButton(text="📚 Предметы",      callback_data="adm:subj")],
        [InlineKeyboardButton(text="👥 Пользователи",  callback_data="adm:users"),
         InlineKeyboardButton(text="📊 Статистика",    callback_data="adm:stats")],
        [InlineKeyboardButton(text="💳 Платежи",       callback_data="adm:pay"),
         InlineKeyboardButton(text="⭐ Донаты",         callback_data="adm:don")],
        [InlineKeyboardButton(text="📥 Загрузить",     callback_data="adm:import"),
         InlineKeyboardButton(text="📦 Шаблон",        callback_data="adm:template")],
        [InlineKeyboardButton(text="📣 Рассылка",      callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="🏷 Промокоды",     callback_data="adm:promos")],
        [InlineKeyboardButton(text="⚙️ Настройки",     callback_data="adm:settings")],
    ])


def admin_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Отправить всем", callback_data="adm:broadcast_send"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="adm:broadcast_cancel"),
    ]])


def admin_promos_keyboard(
    promos: list[dict] | None = None,
    page: int = 0,
    total_pages: int = 1,
) -> InlineKeyboardMarkup:
    rows = []
    for promo in promos or []:
        rows.append([
            InlineKeyboardButton(
                text=f"📊 {promo['code']}",
                callback_data=f"adm:promo:{promo['code']}:0:{page}",
            ),
            InlineKeyboardButton(
                text="🔴 Выкл." if promo["is_active"] else "🟢 Вкл.",
                callback_data=f"adm:promo_toggle:{promo['code']}:{page}",
            ),
        ])
    if total_pages > 1:
        navigation = []
        if page > 0:
            navigation.append(InlineKeyboardButton(
                text="⬅️",
                callback_data=f"adm:promos:{page - 1}",
            ))
        navigation.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="adm:noop"))
        if page + 1 < total_pages:
            navigation.append(InlineKeyboardButton(
                text="➡️",
                callback_data=f"adm:promos:{page + 1}",
            ))
        rows.append(navigation)
    rows.extend([
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="adm:promo_add")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm:main")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_promo_stats_keyboard(
    code: str,
    page: int,
    total_pages: int,
    promo_list_page: int = 0,
) -> InlineKeyboardMarkup:
    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton(
            text="⬅️",
            callback_data=f"adm:promo:{code}:{page - 1}",
        ))
    navigation.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="adm:noop"))
    if page + 1 < total_pages:
        navigation.append(InlineKeyboardButton(
            text="➡️",
            callback_data=f"adm:promo:{code}:{page + 1}",
        ))
    return InlineKeyboardMarkup(inline_keyboard=[
        navigation,
        [InlineKeyboardButton(
            text="🔙 К промокодам",
            callback_data=f"adm:promos:{promo_list_page}" if promo_list_page else "adm:promos",
        )],
    ])


def admin_questions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить",   callback_data="adm:q_add"),
         InlineKeyboardButton(text="✏️ Изменить",  callback_data="adm:q_edit_start")],
        [InlineKeyboardButton(text="🗑 Удалить",   callback_data="adm:q_del_start"),
         InlineKeyboardButton(text="🔎 Поиск",     callback_data="adm:q_search")],
        [InlineKeyboardButton(text="📋 Список",    callback_data="adm:q_list:0"),
         InlineKeyboardButton(text="📥 Импорт",   callback_data="adm:import")],
        [InlineKeyboardButton(text="📦 Шаблон",    callback_data="adm:template"),
         InlineKeyboardButton(text="🔙 Назад",     callback_data="adm:main")],
    ])


def admin_q_list_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm:q_list:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="adm:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm:q_list:{page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        nav,
        [InlineKeyboardButton(text="🔎 Поиск", callback_data="adm:q_search"),
         InlineKeyboardButton(text="🔙 Назад", callback_data="adm:q")],
    ])


def admin_q_view_keyboard(question_id: int) -> InlineKeyboardMarkup:
    qid = question_id
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Текст",     callback_data=f"adm:qf:{qid}:question"),
         InlineKeyboardButton(text="🔤 Варианты",  callback_data=f"adm:qf:{qid}:options")],
        [InlineKeyboardButton(text="✅ Ответ",     callback_data=f"adm:qf:{qid}:correct"),
         InlineKeyboardButton(text="💡 Объяснение", callback_data=f"adm:qf:{qid}:explanation")],
        [InlineKeyboardButton(text="📚 Предмет",   callback_data=f"adm:qf:{qid}:subject"),
         InlineKeyboardButton(text="🎯 Сложность", callback_data=f"adm:qf:{qid}:difficulty")],
        [InlineKeyboardButton(text="🗑 Удалить",   callback_data=f"adm:q_del_confirm:{qid}"),
         InlineKeyboardButton(text="🔙 Назад",     callback_data="adm:q_list:0")],
    ])


def admin_q_delete_confirm_keyboard(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"adm:q_del:{question_id}"),
        InlineKeyboardButton(text="❌ Отмена",      callback_data=f"adm:q_view:{question_id}"),
    ]])


def admin_subjects_keyboard(subjects: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for s in subjects:
        clr = SUBJECT_COLORS.get(s["slug"], "⚪")
        status = "✅" if s["is_active"] else "❌"
        rows.append([
            InlineKeyboardButton(text=f"{status} {clr} {s['title']}", callback_data=f"adm:stog:{s['id']}"),
            InlineKeyboardButton(text="✏️", callback_data=f"adm:sedit:{s['id']}"),
            InlineKeyboardButton(text="🗑",  callback_data=f"adm:sdel_c:{s['id']}"),
        ])
    rows.append([InlineKeyboardButton(text="➕ Добавить предмет", callback_data="adm:subj_add")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_users_list_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm:u_list:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="adm:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm:u_list:{page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        nav,
        [InlineKeyboardButton(text="🔎 Найти по ID", callback_data="adm:u_search"),
         InlineKeyboardButton(text="🔙 Назад",       callback_data="adm:users")],
    ])


def admin_stats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Сегодня",   callback_data="adm:stats:1"),
            InlineKeyboardButton(text="🟡 7 дней",    callback_data="adm:stats:7"),
            InlineKeyboardButton(text="🟠 30 дней",   callback_data="adm:stats:30"),
            InlineKeyboardButton(text="🔵 Всё время", callback_data="adm:stats:0"),
        ],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm:main")],
    ])


def admin_payments_keyboard(filter_type: str, page: int, total_pages: int) -> InlineKeyboardMarkup:
    filters = [("all", "🔵 Все"), ("paid", "🟢 Оплачен."), ("unlock", "🟡 Разблок.")]
    filter_row = [
        InlineKeyboardButton(
            text=("▶ " if f == filter_type else "") + label,
            callback_data=f"adm:pay:{f}:0",
        )
        for f, label in filters
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm:pay:{filter_type}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{max(total_pages, 1)}", callback_data="adm:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm:pay:{filter_type}:{page + 1}"))
    rows = [filter_row]
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_donations_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm:don:{page - 1}"))
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="adm:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm:don:{page + 1}"))
    rows = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_settings_keyboard(current: dict, defaults: dict) -> InlineKeyboardMarkup:
    keys = [
        ("donation_min_stars",  "🟢 Мин. донат Stars"),
        ("donation_max_stars",  "🔴 Макс. донат Stars"),
    ]
    rows = []
    for key, label in keys:
        val = current.get(key, str(defaults.get(key, "—")))
        rows.append([InlineKeyboardButton(text=f"{label}: {val}", callback_data=f"adm:set:{key}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_import_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Импортировать", callback_data="adm:import_ok"),
        InlineKeyboardButton(text="❌ Отмена",        callback_data="adm:import_cancel"),
    ]])


# ─── Admin: add question FSM keyboards ────────────────────────────────────────

def admin_aq_lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 RU", callback_data="aq:lang:ru"),
            InlineKeyboardButton(text="🇺🇿 UZ", callback_data="aq:lang:uz"),
            InlineKeyboardButton(text="🇬🇧 EN", callback_data="aq:lang:en"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="adm:main")],
    ])


def admin_aq_subject_keyboard(subjects: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(subjects), 2):
        s = subjects[i]
        clr = SUBJECT_COLORS.get(s["slug"], "⚪")
        row = [InlineKeyboardButton(text=f"{clr} {s['title']}", callback_data=f"aq:subj:{s['slug']}")]
        if i + 1 < len(subjects):
            s2 = subjects[i + 1]
            clr2 = SUBJECT_COLORS.get(s2["slug"], "⚪")
            row.append(InlineKeyboardButton(text=f"{clr2} {s2['title']}", callback_data=f"aq:subj:{s2['slug']}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_aq_correct_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i, opt in enumerate(options):
        letter = OPTION_LETTERS[i] if i < len(OPTION_LETTERS) else str(i + 1)
        color  = OPTION_COLORS[i]  if i < len(OPTION_COLORS)  else "⚪"
        rows.append([InlineKeyboardButton(
            text=f"{color} {letter}) {opt[:40]}",
            callback_data=f"aq:ans:{i}",
        )])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="adm:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_aq_difficulty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Лёгкая",  callback_data="aq:diff:easy"),
            InlineKeyboardButton(text="🟡 Средняя", callback_data="aq:diff:medium"),
            InlineKeyboardButton(text="🔴 Сложная", callback_data="aq:diff:hard"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="adm:main")],
    ])


def admin_aq_save_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Сохранить", callback_data="aq:save"),
        InlineKeyboardButton(text="❌ Отмена",    callback_data="adm:main"),
    ]])
