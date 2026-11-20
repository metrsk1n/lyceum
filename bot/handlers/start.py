from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import database as db
from bot.keyboards import (
    free_full_mock_keyboard,
    language_keyboard,
    more_keyboard,
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
    "✨ Ещё": "more",
    "👤 Profil": "profile",
    "🎯 Test boshlash": "test",
    "💎 Premium": "premium",
    "📚 Xatolarim": "mistakes",
    "🕘 Tarix": "history",
    "✨ Boshqa": "more",
    "👤 Profile": "profile",
    "🎯 Start test": "test",
    "📚 My mistakes": "mistakes",
    "🕘 History": "history",
    "✨ More": "more",
    "🎁 Подарок": "more",
    "🎁 Sovg'a": "more",
    "🎁 Gift": "more",
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
    "✨ Ещё", "✨ Boshqa", "✨ More",
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

    profile_text = t(
        lang,
        "profile",
        tests=stats["total_tests"],
        correct=stats["correct"],
        accuracy=stats["accuracy"],
        subscription=t(lang, "subscription_active" if has_sub else "subscription_inactive"),
        mistakes=len(mistakes),
    )
    await callback.message.edit_text(profile_text, reply_markup=profile_keyboard(lang))
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
        t(lang, "premium_description"),
        reply_markup=premium_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "user:language")
async def user_profile_language(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(callback.from_user.id)
    await callback.message.edit_text(
        t(lang, "choose_language"),
        reply_markup=language_keyboard(),
    )
    await callback.answer()


def _more_text(free_full_mock_credits: int, lang: str) -> str:
    mock_status = (
        t(lang, "more_credits", credits=free_full_mock_credits)
        if free_full_mock_credits
        else t(lang, "more_no_credits")
    )
    return t(lang, "more_description", mock_status=mock_status)


async def _show_more(message: Message, user_id: int, edit: bool = False) -> None:
    lang = await _lang(user_id)
    access = await db.get_user_access(user_id)
    credits = access["free_full_mock_credits"]
    text = _more_text(credits, lang)
    markup = more_keyboard(credits, lang)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "user:more")
async def user_more(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_more(callback.message, callback.from_user.id, edit=True)
    await callback.answer()


@router.callback_query(F.data == "user:free_mocks")
async def user_free_mocks(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(callback.from_user.id)
    access = await db.get_user_access(callback.from_user.id)
    credits = access["free_full_mock_credits"]
    if not credits:
        await callback.answer(t(lang, "free_mock_no_credit"), show_alert=True)
        return
    await callback.message.edit_text(
        t(lang, "free_mock_available", credits=credits),
        reply_markup=free_full_mock_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "user:promo_history")
async def user_promo_history(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    lang = await _lang(callback.from_user.id)
    redemptions = await db.get_user_promo_redemptions(callback.from_user.id)
    labels = {
        "tests": t(lang, "promo_reward_tests"),
        "full_tests": t(lang, "promo_reward_full_tests"),
        "free_full_mocks": t(lang, "promo_reward_free_full_mocks"),
        "explanations": t(lang, "promo_reward_explanations"),
        "discount": t(lang, "promo_reward_discount"),
    }
    lines = [t(lang, "promo_history_title")]
    if not redemptions:
        lines.append(t(lang, "promo_history_empty"))
    else:
        for item in redemptions:
            reward = (
                t(lang, "promo_discount_value", value=item["value"])
                if item["reward_type"] == "discount"
                else f"{item['value']} {labels.get(item['reward_type'], item['reward_type'])}"
            )
            lines.append(
                t(lang, "promo_history_item", code=item["code"], reward=reward, date=item["redeemed_at"])
            )
    access = await db.get_user_access(callback.from_user.id)
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=more_keyboard(access["free_full_mock_credits"], lang),
    )
    await callback.answer()


@router.callback_query(F.data == "gift:promo")
async def promo_code_start(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await _lang(callback.from_user.id)
    await state.set_state(PromoFlow.waiting_code)
    await callback.message.answer(
        t(lang, "promo_enter"),
        reply_markup=promo_back_keyboard(lang),
    )
    await callback.answer()


@router.message(PromoFlow.waiting_code, F.text)
async def redeem_promo_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()
    result = await db.redeem_promo_code(message.from_user.id, code)
    await state.clear()
    lang = await _lang(message.from_user.id)
    access = await db.get_user_access(message.from_user.id)
    markup = more_keyboard(access["free_full_mock_credits"], lang)
    if not result:
        await message.answer(t(lang, "promo_not_found"), reply_markup=markup)
        return
    errors = {
        "expired": t(lang, "promo_expired"),
        "limit": t(lang, "promo_limit"),
        "used": t(lang, "promo_used"),
        "discount_pending": t(lang, "promo_discount_pending"),
        "invalid": t(lang, "promo_invalid"),
    }
    if "error" in result:
        await message.answer(errors.get(result["error"], t(lang, "promo_failed")), reply_markup=markup)
        return
    reward_messages = {
        "tests": t(lang, "promo_activated_tests", value=result["value"]),
        "full_tests": t(lang, "promo_activated_full_tests", value=result["value"]),
        "free_full_mocks": t(lang, "promo_activated_free_full_mocks", value=result["value"]),
        "explanations": t(lang, "promo_activated_explanations", value=result["value"]),
        "discount": t(lang, "promo_activated_discount", value=result["value"]),
    }
    await message.answer(reward_messages[result["reward_type"]], reply_markup=markup)


@router.callback_query(F.data == "user:mistakes")
async def user_mistakes(callback: CallbackQuery) -> None:
    lang = await _lang(callback.from_user.id)
    mistakes = await db.get_user_mistakes(callback.from_user.id, limit=10)
    if not mistakes:
        await callback.message.edit_text(t(lang, "mistakes_empty"), reply_markup=profile_keyboard(lang))
        await callback.answer()
        return

    lines = [t(lang, "mistakes_title")]
    for idx, item in enumerate(mistakes[:10], start=1):
        lines.append(f"{idx}. {item['question']}\n")
        lines.append(t(lang, "mistake_answer", answer=item["correct_text"]))
    await callback.message.edit_text("".join(lines), reply_markup=profile_keyboard(lang))
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
        text = t(
            lang,
            "profile",
            tests=stats["total_tests"],
            correct=stats["correct"],
            accuracy=stats["accuracy"],
            subscription=t(lang, "subscription_active" if has_sub else "subscription_inactive"),
            mistakes=len(mistakes),
        )
        await message.answer(text, reply_markup=profile_keyboard(lang))
    elif action == "test":
        subjects = await db.get_subjects()
        await message.answer(
            t(lang, "choose_subject") if subjects else t(lang, "no_questions"),
            reply_markup=test_choice_keyboard(lang) if subjects else None,
        )
    elif action == "premium":
        await message.answer(
            t(lang, "premium_description"),
            reply_markup=premium_keyboard(lang),
        )
    elif action == "more":
        await _show_more(message, user_id)
    elif action == "mistakes":
        mistakes = await db.get_user_mistakes(user_id, limit=10)
        if not mistakes:
            await message.answer(t(lang, "mistakes_empty"), reply_markup=profile_keyboard(lang))
            return
        lines = [t(lang, "mistakes_title")]
        for index, item in enumerate(mistakes, start=1):
            lines.append(f"{index}. {item['question']}\n")
            lines.append(t(lang, "mistake_answer", answer=item["correct_text"]))
        await message.answer("".join(lines), reply_markup=profile_keyboard(lang))
    elif action == "history":
        results = await db.get_user_results(user_id, limit=10)
        if not results:
            await message.answer(t(lang, "test_history_empty"))
            return
        subjects = {
            "mathematics": {"ru": "Математика", "en": "Mathematics", "uz": "Matematika"}.get(lang, "Matematika"),
            "english": {"ru": "Английский", "en": "English", "uz": "Ingliz tili"}.get(lang, "Английский"),
            "iq": "IQ",
        }
        subjects.update({
            item["slug"]: item["title"]
            for item in await db.get_subjects()
            if item["slug"] not in subjects
        })
        lines = [t(lang, "test_history_title")]
        for result in results:
            subject = subjects.get(result["subject"], result["subject"])
            percent = round(result["score"] / result["total"] * 100) if result["total"] else 0
            lines.append(
                t(
                    lang,
                    "test_history_item",
                    subject=subject,
                    score=result["score"],
                    total=result["total"],
                    percent=percent,
                    date=str(result["finished_at"])[:10],
                )
            )
        from bot.keyboards import result_history_keyboard
        await message.answer("\n".join(lines), reply_markup=result_history_keyboard(results, lang))


@router.callback_query(F.data.startswith("history:"))
async def show_history_result(callback: CallbackQuery) -> None:
    lang = await _lang(callback.from_user.id)
    try:
        result_id = int(callback.data.split(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer(t(lang, "result_not_found"), show_alert=True)
        return

    result = await db.get_result_for_user(result_id, callback.from_user.id)
    if result is None:
        await callback.answer(t(lang, "result_not_found"), show_alert=True)
        return

    subjects = {
        "mathematics": {"ru": "Математика", "en": "Mathematics", "uz": "Matematika"}.get(lang, "Математика"),
        "english": {"ru": "Английский", "en": "English", "uz": "Ingliz tili"}.get(lang, "Английский"),
        "iq": "IQ",
    }
    subjects.update({
        item["slug"]: item["title"]
        for item in await db.get_subjects()
        if item["slug"] not in subjects
    })
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
        t(lang, "history_result_title", subject=subject, date=str(result["finished_at"])[:10]),
        t(lang, "test_result_score", score=result["score"], total=result["total"], percent=percent),
        "",
    ]
    for index, answer in enumerate(result["answers"], start=1):
        selected_letter = answer.get("selected_letter", "")
        if not selected_letter:
            selected_letter = "АБВГДЕЖЗ"[answer.get("selected", 0)]
        status = "✅" if answer.get("is_correct") else "❌"
        lines.append(f"{index}. {selected_letter} — {status}")
    lines.append("\n" + t(lang, "history_review_prompt"))
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
    if lang not in {"ru", "uz", "en"}:
        current_lang = await _lang(callback.from_user.id)
        await callback.answer(t(current_lang, "language_invalid"), show_alert=True)
        return
    await state.clear()
    await db.set_user_language(callback.from_user.id, lang)
    await callback.message.edit_text(t(lang, "language_set"))
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
