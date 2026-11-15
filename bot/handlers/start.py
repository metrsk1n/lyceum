from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from bot.keyboards import (
    gift_keyboard,
    language_keyboard,
    premium_keyboard,
    profile_keyboard,
    promo_back_keyboard,
    test_choice_keyboard,
    user_main_menu,
)
from bot.locale import t
from bot.states import PromoFlow

router = Router()

USER_MENU_ACTIONS = {
    "👤 Профиль": "profile",
    "🎯 Начать тест": "test",
    "💎 Премиум": "premium",
    "📚 Мои ошибки": "mistakes",
    "🕘 История": "history",
    "🎁 Подарок": "gift",
    "👤 Profil": "profile",
    "🎯 Test boshlash": "test",
    "💎 Premium": "premium",
    "📚 Xatolarim": "mistakes",
    "🕘 Tarix": "history",
    "🎁 Sovg'a": "gift",
    "👤 Profile": "profile",
    "🎯 Start test": "test",
    "📚 My mistakes": "mistakes",
    "🕘 History": "history",
    "🎁 Gift": "gift",
}

# All main menu button texts across all languages — used for FSM auto-cancel
MENU_TEXTS = {
    # RU
    "🔥 Начать тест", "📊 Статистика", "🌐 Язык", "🌟 Поддержать", "💡 Помощь", "💳 Платежи",
    # UZ
    "🔥 Testni boshlash", "📊 Statistika", "🌐 Til",
    "🌟 Qo'llab-quvvatlash", "💡 Yordam", "💳 To'lovlar",
    # EN
    "🔥 Start test", "📊 Statistics", "🌐 Language", "🌟 Support", "💡 Help", "💳 Payments",
    # Cancel
    "❌ Отмена",
    "🕘 История", "🕘 Tarix", "🕘 History",
    "🎁 Подарок", "🎁 Sovg'a", "🎁 Gift",
}


async def _lang(user_id: int) -> str:
    return await db.get_user_language(user_id)


# ─── Cancel / main menu auto-clear ────────────────────────────────────────────
# This router is included FIRST in main.py, so these handlers have priority
# and clear any active FSM state before proceeding.

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username,
    )
    lang = user["language"]
    await message.answer(t(lang, "start"), reply_markup=user_main_menu(lang))


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(message.from_user.id)
    await message.answer(t(lang, "help"))


@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(message.from_user.id)
    await message.answer(t(lang, "start"), reply_markup=user_main_menu(lang))


@router.callback_query(F.data == "user:main")
async def user_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(callback.from_user.id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(t(lang, "start"), reply_markup=user_main_menu(lang))
    await callback.answer()


@router.callback_query(F.data == "user:profile")
async def user_profile(callback: CallbackQuery) -> None:
    lang = await _lang(callback.from_user.id)
    stats = await db.get_user_stats(callback.from_user.id)
    has_sub = await db.user_has_active_subscription(callback.from_user.id)
    mistakes = await db.get_user_mistakes(callback.from_user.id, limit=5)

    profile_text = (
        "👤 <b>Профиль</b>\n\n"
        f"📊 Всего тестов: <b>{stats['total_tests']}</b>\n"
        f"✅ Правильных ответов: <b>{stats['correct']}</b>\n"
        f"📈 Точность: <b>{stats['accuracy']}%</b>\n"
        f"💎 Подписка: <b>{'активна' if has_sub else 'не активна'}</b>\n\n"
        f"❌ Ошибок: <b>{len(mistakes)}</b>"
    )
    await callback.message.edit_text(profile_text, reply_markup=profile_keyboard())
    await callback.answer()


@router.callback_query(F.data == "user:start_test")
async def user_start_test(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(callback.from_user.id)
    subjects = await db.get_subjects()
    if not subjects:
        await callback.message.edit_text(t(lang, "no_questions"))
        await callback.answer()
        return
    await callback.message.edit_text(
        t(lang, "choose_subject"),
        reply_markup=test_choice_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "user:premium")
async def user_premium(callback: CallbackQuery) -> None:
    lang = await _lang(callback.from_user.id)
    await callback.message.edit_text(
        "💎 <b>Подписка Premium</b>\n\n"
        "До 5 тестов в день и подробные разборы без доплаты, пока подписка активна. "
        "Также доступны история ошибок и расширенный режим подготовки.",
        reply_markup=premium_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "user:gift")
async def user_gift(callback: CallbackQuery) -> None:
    used_mocks = await db.get_free_mock_status(callback.from_user.id)
    remaining = 3 - len(used_mocks)
    await callback.message.edit_text(
        f"🎁 <b>Бесплатные предметные моки</b>\n\n"
        f"Доступно: {remaining} из 3 бесплатных предметных моков. Каждый содержит "
        f"100 фиксированных вопросов по одному предмету и доступен один раз.\n"
        f"Платные тарифы: тест на 20 вопросов по выбранному предмету — 25 ⭐; "
        f"полный мок по математике, английскому и IQ (по 20 вопросов) — 60 ⭐.",
        reply_markup=gift_keyboard(used_mocks),
    )
    await callback.answer()


@router.callback_query(F.data == "gift:claim")
async def claim_gift(callback: CallbackQuery) -> None:
    await callback.answer("Бесплатные моки доступны в меню «Подарок».", show_alert=True)


@router.callback_query(F.data == "gift:promo")
async def promo_code_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PromoFlow.waiting_code)
    await callback.message.answer("Введите промокод одним сообщением:", reply_markup=promo_back_keyboard())
    await callback.answer()


@router.message(PromoFlow.waiting_code, F.text)
async def redeem_promo_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()
    result = await db.redeem_promo_code(message.from_user.id, code)
    await state.clear()
    if not result:
        await message.answer("Промокод не найден или отключён.", reply_markup=gift_keyboard())
        return
    errors = {
        "expired": "Срок действия промокода истёк.",
        "limit": "Лимит активаций этого промокода исчерпан.",
        "used": "Вы уже активировали этот промокод.",
        "discount_pending": "Сначала используйте уже активированную скидку на подписку.",
        "invalid": "Тип промокода не поддерживается.",
    }
    if "error" in result:
        await message.answer(errors.get(result["error"], "Не удалось активировать промокод."), reply_markup=gift_keyboard())
        return
    reward_messages = {
        "tests": f"✅ Промокод активирован: начислено {result['value']} тестов.",
        "full_tests": f"✅ Промокод активирован: начислено {result['value']} полных моков.",
        "explanations": f"✅ Промокод активирован: начислено {result['value']} разборов.",
        "discount": f"✅ Скидка {result['value']}% применится к следующей покупке подписки.",
    }
    await message.answer(reward_messages[result["reward_type"]], reply_markup=gift_keyboard())


@router.callback_query(F.data == "user:mistakes")
async def user_mistakes(callback: CallbackQuery) -> None:
    lang = await _lang(callback.from_user.id)
    mistakes = await db.get_user_mistakes(callback.from_user.id, limit=10)
    if not mistakes:
        await callback.message.edit_text("📚 У вас пока нет ошибок. Отличная работа!", reply_markup=profile_keyboard())
        await callback.answer()
        return

    lines = ["📚 <b>Мои ошибки</b>\n"]
    for idx, item in enumerate(mistakes[:10], start=1):
        lines.append(f"{idx}. {item['question']}\n")
        lines.append(f"   ✅ Правильный ответ: {item['correct_text']}\n\n")
    await callback.message.edit_text("".join(lines), reply_markup=profile_keyboard())
    await callback.answer()


@router.message(F.text.in_(USER_MENU_ACTIONS))
async def handle_user_menu_button(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id
    lang = await _lang(user_id)
    action = USER_MENU_ACTIONS[message.text]

    if action == "profile":
        stats = await db.get_user_stats(user_id)
        has_sub = await db.user_has_active_subscription(user_id)
        mistakes = await db.get_user_mistakes(user_id, limit=5)
        text = (
            "👤 <b>Профиль</b>\n\n"
            f"📊 Всего тестов: <b>{stats['total_tests']}</b>\n"
            f"✅ Правильных ответов: <b>{stats['correct']}</b>\n"
            f"📈 Точность: <b>{stats['accuracy']}%</b>\n"
            f"💎 Подписка: <b>{'активна' if has_sub else 'не активна'}</b>\n\n"
            f"❌ Ошибок: <b>{len(mistakes)}</b>"
        )
        await message.answer(text, reply_markup=profile_keyboard())
    elif action == "test":
        subjects = await db.get_subjects()
        await message.answer(
            t(lang, "choose_subject") if subjects else t(lang, "no_questions"),
            reply_markup=test_choice_keyboard(lang) if subjects else None,
        )
    elif action == "premium":
        await message.answer(
            "💎 <b>Подписка Premium</b>\n\n"
            "До 5 тестов в день и подробные разборы без доплаты, пока подписка активна. "
            "Также доступны история ошибок и расширенный режим подготовки.",
            reply_markup=premium_keyboard(),
        )
    elif action == "gift":
        used_mocks = await db.get_free_mock_status(user_id)
        remaining = 3 - len(used_mocks)
        await message.answer(
            f"🎁 <b>Бесплатные предметные моки</b>\n\n"
            f"Доступно: {remaining} из 3 бесплатных предметных моков. Каждый содержит "
            f"100 фиксированных вопросов по одному предмету и доступен один раз.\n"
            f"Платные тарифы: тест на 20 вопросов по выбранному предмету — 25 ⭐; "
            f"полный мок по математике, английскому и IQ (по 20 вопросов) — 60 ⭐.",
            reply_markup=gift_keyboard(used_mocks),
        )
    elif action == "mistakes":
        mistakes = await db.get_user_mistakes(user_id, limit=10)
        if not mistakes:
            await message.answer("📚 У вас пока нет ошибок. Отличная работа!", reply_markup=profile_keyboard())
            return
        lines = ["📚 <b>Мои ошибки</b>\n"]
        for index, item in enumerate(mistakes, start=1):
            lines.append(f"{index}. {item['question']}\n   ✅ Правильный ответ: {item['correct_text']}\n\n")
        await message.answer("".join(lines), reply_markup=profile_keyboard())
    elif action == "history":
        results = await db.get_user_results(user_id, limit=10)
        if not results:
            await message.answer("🕘 История тестов пока пуста.")
            return
        subjects = {item["slug"]: item["title"] for item in await db.get_subjects()}
        lines = ["🕘 <b>История тестов</b>\n"]
        for result in results:
            subject = subjects.get(result["subject"], result["subject"])
            percent = round(result["score"] / result["total"] * 100) if result["total"] else 0
            lines.append(
                f"📊 {subject}: <b>{result['score']}/{result['total']} ({percent}%)</b> · "
                f"{str(result['finished_at'])[:10]}"
            )
        from bot.keyboards import result_history_keyboard
        await message.answer("\n".join(lines), reply_markup=result_history_keyboard(results))


@router.callback_query(F.data.startswith("history:"))
async def show_history_result(callback: CallbackQuery) -> None:
    try:
        result_id = int(callback.data.split(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Результат не найден.", show_alert=True)
        return

    result = await db.get_result_for_user(result_id, callback.from_user.id)
    if result is None:
        await callback.answer("Результат не найден.", show_alert=True)
        return

    lang = await _lang(callback.from_user.id)
    subjects = {item["slug"]: item["title"] for item in await db.get_subjects()}
    subject = subjects.get(
        result["subject"],
        {
            "ru": "Полный мок · математика, английский и IQ",
            "en": "Full mock · Mathematics, English, and IQ",
            "uz": "To'liq mock · Matematika, Ingliz tili va IQ",
        }.get(lang, "Полный мок")
        if result["subject"] == "full_mock"
        else result["subject"],
    )
    percent = round(result["score"] / result["total"] * 100) if result["total"] else 0
    lines = [
        f"📊 <b>{subject}</b> · {str(result['finished_at'])[:10]}",
        f"Результат: <b>{result['score']}/{result['total']} ({percent}%)</b>",
        "",
    ]
    for index, answer in enumerate(result["answers"], start=1):
        selected_letter = answer.get("selected_letter", "")
        if not selected_letter:
            selected_letter = "АБВГДЕЖЗ"[answer.get("selected", 0)]
        status = "✅" if answer.get("is_correct") else "❌"
        lines.append(f"{index}. {selected_letter} — {status}")
    lines.append("\nВыберите номер, чтобы открыть разбор:")
    from bot.keyboards import result_questions_keyboard
    from bot.pricing import EXPLANATION_PRICE_STARS
    result_subjects = list(dict.fromkeys(
        answer.get("subject") or result["subject"]
        for answer in result["answers"]
        if result["subject"] != "full_mock" or answer.get("subject") in {"mathematics", "english", "iq"}
    ))
    titles = {slug: title for slug, title in subjects.items()}
    titles.update({
        "mathematics": {"ru": "Математика", "en": "Mathematics", "uz": "Matematika"}.get(lang, "Математика"),
        "english": {"ru": "Английский", "en": "English", "uz": "Ingliz tili"}.get(lang, "Английский"),
        "iq": "IQ",
    })
    unlock_subjects = (
        []
        if await db.user_has_active_subscription(callback.from_user.id)
        else [(slug, titles.get(slug, slug)) for slug in result_subjects]
    )
    await callback.message.answer(
        "\n".join(lines),
        reply_markup=result_questions_keyboard(
            result_id,
            len(result["answers"]),
            EXPLANATION_PRICE_STARS,
            lang,
            unlock_subjects,
        ),
    )
    await callback.answer()


# ─── Language ─────────────────────────────────────────────────────────────────

@router.message(Command("language"))
@router.message(F.text.in_({"🌐 Язык", "🌐 Language", "🌐 Til"}))
async def show_language(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(message.from_user.id)
    await message.answer(t(lang, "choose_language"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.split(":")[1]
    await state.clear()
    await db.set_user_language(callback.from_user.id, lang)
    await callback.message.edit_text(t(lang, "choose_language"), reply_markup=language_keyboard())
    await callback.answer(t(lang, "language_set"))
    await callback.message.answer(t(lang, "start"), reply_markup=user_main_menu(lang))


# ─── Help ─────────────────────────────────────────────────────────────────────

@router.message(F.text.in_({"💡 Помощь", "💡 Help", "💡 Yordam"}))
async def show_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(message.from_user.id)
    await message.answer(t(lang, "help"))


# ─── Test start ───────────────────────────────────────────────────────────────

@router.message(F.text.in_({"🔥 Начать тест", "🔥 Start test", "🔥 Testni boshlash"}))
async def show_subjects(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(message.from_user.id)
    subjects = await db.get_subjects()
    if not subjects:
        await message.answer(t(lang, "no_questions"))
        return
    await message.answer(
        t(lang, "choose_subject"),
        reply_markup=test_choice_keyboard(lang),
    )


# ─── Stats shortcut ───────────────────────────────────────────────────────────

@router.message(F.text.in_({"📊 Статистика", "📊 Statistics", "📊 Statistika"}))
async def show_stats_redirect(message: Message, state: FSMContext) -> None:
    await state.clear()
    from bot.handlers.statistics import _show_stats
    await _show_stats(message)


# ─── Navigation callbacks ─────────────────────────────────────────────────────

@router.callback_query(F.data == "goto:test")
async def goto_test(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(callback.from_user.id)
    subjects = await db.get_subjects()
    await callback.message.answer(
        t(lang, "choose_subject") if subjects else t(lang, "no_questions"),
        reply_markup=test_choice_keyboard(lang) if subjects else None,
    )
    await callback.answer()


@router.callback_query(F.data == "goto:stats")
async def goto_stats(callback: CallbackQuery) -> None:
    lang = await _lang(callback.from_user.id)
    stats = await db.get_user_stats(callback.from_user.id)
    if not stats["total_tests"]:
        await callback.message.answer(t(lang, "stats_empty"))
    else:
        await callback.message.answer(t(lang, "stats",
            tests=stats["total_tests"], questions=stats["total_q"],
            correct=stats["correct"], accuracy=stats["accuracy"], best=stats["best"],
        ))
    await callback.answer()


@router.callback_query(F.data == "adm:noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()
