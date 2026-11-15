from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
from datetime import datetime
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import database as db
from bot.bulk_import import (
    build_template_csv,
    build_template_json,
    build_template_xlsx,
    parse_import_payload,
)
from bot.keyboards import (
    admin_aq_correct_keyboard, admin_aq_difficulty_keyboard,
    admin_aq_lang_keyboard, admin_aq_save_keyboard,
    admin_aq_subject_keyboard, admin_donations_keyboard,
    admin_broadcast_confirm_keyboard, admin_import_confirm_keyboard, admin_main_keyboard,
    admin_payments_keyboard, admin_promos_keyboard, admin_promo_stats_keyboard,
    admin_q_delete_confirm_keyboard,
    admin_q_list_keyboard, admin_q_view_keyboard,
    admin_questions_keyboard, admin_settings_keyboard,
    admin_stats_keyboard, admin_subjects_keyboard,
    admin_users_list_keyboard, cancel_keyboard, main_menu,
)
from bot.states import AdminFlow
from config import settings

logger = logging.getLogger(__name__)
router = Router()

PAGE_SIZE = 10
PROMO_PAGE_SIZE = 20
PROMO_REDEMPTIONS_PAGE_SIZE = 15

# Temp storage for pending JSON imports (user_id → validated items list)
_pending_imports: dict[int, list[dict]] = {}

DIFF_LABELS = {"easy": "🟢 Лёгкая", "medium": "🟡 Средняя", "hard": "🔴 Сложная"}
OPTION_LETTERS = ["A", "B", "C", "D", "E", "F"]


# ─── Access control ───────────────────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


async def _deny(callback: CallbackQuery) -> None:
    await callback.answer("⛔ Доступ запрещён.", show_alert=True)


def _admin_user_card(info: dict) -> tuple[str, InlineKeyboardMarkup]:
    user_id = info["id"]
    name = escape(info.get("first_name") or info.get("username") or str(user_id))
    username = escape(info.get("username") or "—")
    status = "⛔ Заблокирован" if info.get("is_banned") else "✅ Активен"
    text = (
        f"👤 <b>Пользователь</b>\n\n"
        f"ID: <code>{user_id}</code>\n"
        f"Имя: {name}\n"
        f"Username: @{username}\n"
        f"Статус: {status}\n"
        f"Язык: {info['language'].upper()}\n"
        f"Регистрация: {info['created_at'][:10]}\n\n"
        f"📝 Тестов пройдено: <b>{info['test_count']}</b>\n"
        f"📊 Средний результат: <b>{info['avg_score']}%</b>\n"
        f"💳 Платежей: <b>{info['payment_count']}</b>\n"
        f"⭐ Потрачено Stars: <b>{info['stars_spent']}</b>"
    )
    button_label = "✅ Разблокировать" if info.get("is_banned") else "⛔ Заблокировать"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=button_label,
            callback_data=f"adm:user_ban:{user_id}",
        )],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm:users")],
    ])
    return text, keyboard


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _question_preview(q: dict) -> str:
    opts = q.get("options", [])
    opt_lines = "\n".join(f"{OPTION_LETTERS[i]}) {o}" for i, o in enumerate(opts) if i < len(OPTION_LETTERS))
    correct_idxs = q.get("correct", [0])
    correct_letters = ", ".join(OPTION_LETTERS[i] for i in correct_idxs if i < len(OPTION_LETTERS))
    diff = DIFF_LABELS.get(q.get("difficulty", "medium"), q.get("difficulty", ""))
    expl = q.get("explanation") or "—"
    return (
        f"📋 <b>Вопрос #{q.get('id', '?')}</b>\n\n"
        f"📚 Предмет: <b>{q.get('subject', '—')}</b>  |  🌐 Язык: <b>{q.get('language', '—')}</b>\n"
        f"🎯 Сложность: <b>{diff}</b>\n\n"
        f"❓ {q.get('question', '')}\n\n"
        f"{opt_lines}\n\n"
        f"✅ Правильный ответ: <b>{correct_letters}</b>\n"
        f"💡 {expl}"
    )


def _total_pages(total: int, page_size: int = PAGE_SIZE) -> int:
    return max(1, (total + page_size - 1) // page_size)


def build_import_success_text(items: list[dict], imported_count: int | None = None) -> str:
    total = imported_count if imported_count is not None else len(items)
    names = []
    for item in items[:10]:
        question = item.get("question") or item.get("question_text") or "Без названия"
        names.append(f"• {escape(str(question).strip()[:120])}")
    if len(items) > 10:
        names.append(f"• ... ещё {len(items) - 10} вопросов")

    body = "\n".join(names) if names else "• Нет данных"
    return (
        f"✅ <b>Успешно добавлены {total} вопрос(а)</b>\n\n"
        f"{body}"
    )


async def _send_template_documents(target: Message) -> None:
    await target.answer_document(
        BufferedInputFile(build_template_json(), filename="questions_template.json"),
        caption="📄 JSON-шаблон",
    )
    await target.answer_document(
        BufferedInputFile(build_template_csv(), filename="questions_template.csv"),
        caption="📄 CSV-шаблон",
    )
    try:
        await target.answer_document(
            BufferedInputFile(build_template_xlsx(), filename="questions_template.xlsx"),
            caption="📄 XLSX-шаблон",
        )
    except RuntimeError as exc:
        logger.warning("Could not generate XLSX template: %s", exc)


# ─── Main panel ───────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await state.clear()
    total_u = await db.count_users()
    total_q = await db.count_questions()
    text = (
        f"⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"👥 Пользователей: <b>{total_u}</b>  |  ❓ Вопросов: <b>{total_q}</b>\n\n"
        "Выберите раздел:"
    )
    await message.answer(text, reply_markup=admin_main_keyboard())


@router.message(Command("get_template"))
async def admin_get_template_command(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await _send_template_documents(message)


@router.callback_query(F.data == "adm:template")
async def admin_template_callback(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await _send_template_documents(callback.message)
    await callback.answer()


@router.callback_query(F.data == "adm:main")
async def admin_main_cb(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    total_u = await db.count_users()
    total_q = await db.count_questions()
    text = (
        f"⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"👥 Пользователей: <b>{total_u}</b>  |  ❓ Вопросов: <b>{total_q}</b>\n\n"
        "Выберите раздел:"
    )
    await callback.message.edit_text(text, reply_markup=admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(AdminFlow.broadcast_waiting)
    await callback.message.edit_text(
        "📣 <b>Рассылка пользователям</b>\n\n"
        "Отправьте одним сообщением текст, фото, видео или другой материал. "
        "Перед рассылкой можно будет подтвердить или отменить отправку.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔙 Отмена", callback_data="adm:broadcast_cancel"),
        ]]),
    )
    await callback.answer()


@router.message(AdminFlow.broadcast_waiting)
async def admin_broadcast_receive(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    await state.update_data(
        broadcast_chat_id=message.chat.id,
        broadcast_message_id=message.message_id,
    )
    await state.set_state(AdminFlow.broadcast_confirm)
    await message.answer(
        "Сообщение получено. Подтвердите отправку всем незаблокированным пользователям.",
        reply_markup=admin_broadcast_confirm_keyboard(),
    )


@router.callback_query(F.data == "adm:broadcast_cancel")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.", reply_markup=admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "adm:broadcast_send", AdminFlow.broadcast_confirm)
async def admin_broadcast_send(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    data = await state.get_data()
    source_chat_id = data.get("broadcast_chat_id")
    source_message_id = data.get("broadcast_message_id")
    if source_chat_id is None or source_message_id is None:
        await state.clear()
        await callback.answer("Сообщение рассылки не найдено. Начните заново.", show_alert=True)
        return

    await state.clear()
    recipients = await db.get_all_user_ids()
    await callback.answer("Рассылка запущена")
    await callback.message.edit_text(f"📣 Рассылка началась: 0/{len(recipients)}")
    delivered = 0
    failed = 0
    for user_id in recipients:
        try:
            await callback.bot.copy_message(
                chat_id=user_id,
                from_chat_id=source_chat_id,
                message_id=source_message_id,
            )
            delivered += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await callback.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                )
                delivered += 1
            except Exception as retry_exc:
                failed += 1
                logger.info("Broadcast retry failed (%s)", type(retry_exc).__name__)
        except Exception as exc:
            failed += 1
            logger.info("Broadcast delivery failed (%s)", type(exc).__name__)
        await asyncio.sleep(0.05)

    await callback.message.edit_text(
        f"✅ Рассылка завершена.\n\nДоставлено: <b>{delivered}</b>\nНе доставлено: <b>{failed}</b>",
        reply_markup=admin_main_keyboard(),
    )


@router.callback_query(F.data == "adm:promos")
@router.callback_query(F.data.startswith("adm:promos:"))
async def admin_promos_list(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    try:
        page = max(0, int(callback.data.rsplit(":", 1)[1])) if callback.data != "adm:promos" else 0
    except ValueError:
        await callback.answer("Некорректная страница.", show_alert=True)
        return
    total = await db.count_promo_codes()
    total_pages = max(1, (total + PROMO_PAGE_SIZE - 1) // PROMO_PAGE_SIZE)
    page = min(page, total_pages - 1)
    promos = await db.list_promo_codes(limit=PROMO_PAGE_SIZE, offset=page * PROMO_PAGE_SIZE)
    labels = {
        "tests": "Тесты",
        "full_tests": "Полные моки",
        "explanations": "Разборы",
        "discount": "Скидка",
    }
    lines = ["🏷 <b>Промокоды</b>\n"]
    if not promos:
        lines.append("Промокодов пока нет.")
    for promo in promos:
        limit = str(promo["max_uses"]) if promo["max_uses"] else "∞"
        expiry = promo["expires_at"] or "без срока"
        active = "активен" if promo["is_active"] else "выключен"
        lines.append(
            f"<code>{promo['code']}</code> · {labels.get(promo['reward_type'], promo['reward_type'])} "
            f"{promo['value']} · {promo['uses_count']}/{limit} · {expiry} · {active}"
        )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_promos_keyboard(promos, page, total_pages),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:promo_toggle:"))
async def admin_promo_toggle(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    try:
        _, _, code, page_text = callback.data.split(":")
        page = max(0, int(page_text))
    except (AttributeError, ValueError):
        await callback.answer("Некорректный запрос.", show_alert=True)
        return
    if not await db.toggle_promo_code(code):
        await callback.answer("Промокод не найден.", show_alert=True)
        return
    total = await db.count_promo_codes()
    total_pages = max(1, (total + PROMO_PAGE_SIZE - 1) // PROMO_PAGE_SIZE)
    page = min(page, total_pages - 1)
    promos = await db.list_promo_codes(
        limit=PROMO_PAGE_SIZE,
        offset=page * PROMO_PAGE_SIZE,
    )
    labels = {
        "tests": "Тесты",
        "full_tests": "Полные моки",
        "explanations": "Разборы",
        "discount": "Скидка",
    }
    lines = ["🏷 <b>Промокоды</b>\n"]
    for promo in promos:
        limit = str(promo["max_uses"]) if promo["max_uses"] else "∞"
        expiry = promo["expires_at"] or "без срока"
        active = "активен" if promo["is_active"] else "выключен"
        lines.append(
            f"<code>{promo['code']}</code> · {labels.get(promo['reward_type'], promo['reward_type'])} "
            f"{promo['value']} · {promo['uses_count']}/{limit} · {expiry} · {active}"
        )
    await callback.message.edit_text(
        "\n".join(lines) if promos else "Промокодов пока нет.",
        reply_markup=admin_promos_keyboard(promos, page, total_pages),
    )
    await callback.answer("Статус промокода изменён.")


@router.callback_query(F.data.startswith("adm:promo:"))
async def admin_promo_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    try:
        parts = callback.data.split(":")
        if len(parts) not in {4, 5}:
            raise ValueError("unexpected callback format")
        code, page_text = parts[2:4]
        page = max(0, int(page_text))
        promo_list_page = max(0, int(parts[4])) if len(parts) == 5 else 0
    except (AttributeError, ValueError):
        await callback.answer("Некорректный промокод.", show_alert=True)
        return

    total, redemptions = await db.get_promo_redemptions(
        code,
        limit=PROMO_REDEMPTIONS_PAGE_SIZE,
        offset=page * PROMO_REDEMPTIONS_PAGE_SIZE,
    )
    total_pages = max(1, (total + PROMO_REDEMPTIONS_PAGE_SIZE - 1) // PROMO_REDEMPTIONS_PAGE_SIZE)
    page = min(page, total_pages - 1)
    if not redemptions and page:
        total, redemptions = await db.get_promo_redemptions(
            code,
            limit=PROMO_REDEMPTIONS_PAGE_SIZE,
            offset=page * PROMO_REDEMPTIONS_PAGE_SIZE,
        )

    lines = [f"🏷 <b>Статистика промокода <code>{escape(code)}</code></b>"]
    lines.append(f"Всего активаций / пользователей: <b>{total}</b>\n")
    if redemptions:
        for index, user in enumerate(redemptions, start=page * PROMO_REDEMPTIONS_PAGE_SIZE + 1):
            name = escape(user.get("first_name") or "Без имени")
            username = f"@{escape(user['username'])}" if user.get("username") else "username не задан"
            lines.append(
                f"{index}. {name} · {username} · ID <code>{user['user_id']}</code> "
                f"· {escape(user['redeemed_at'])}"
            )
    else:
        lines.append("Пока никто не активировал этот промокод.")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_promo_stats_keyboard(code, page, total_pages, promo_list_page),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:promo_add")
async def admin_promo_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(AdminFlow.promo_waiting)
    await callback.message.answer(
        "Отправьте промокод одной строкой:\n"
        "<code>КОД tests|full_tests|explanations|discount КОЛИЧЕСТВО [ЛИМИТ] [YYYY-MM-DD]</code>\n\n"
        "Например: <code>JUNE tests 3 100 2026-12-31</code>. "
        "Тип <code>full_tests</code> начисляет полный мок за 60 ⭐. "
        "Лимит и срок можно не указывать; лимит 0 означает без ограничений. "
        "Скидка задаётся в процентах, максимум 90%."
    )
    await callback.answer()


@router.message(AdminFlow.promo_waiting, F.text)
async def admin_promo_add(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    parts = (message.text or "").split()
    if not 3 <= len(parts) <= 5:
        await message.answer("Формат: <code>КОД тип количество [лимит] [YYYY-MM-DD]</code>")
        return

    code, reward_type = parts[0].upper(), parts[1].lower()
    if not re.fullmatch(r"[A-Z0-9_-]{3,32}", code):
        await message.answer("Код: 3–32 символа, латинские буквы, цифры, _ или -.")
        return
    if reward_type not in {"tests", "full_tests", "explanations", "discount"}:
        await message.answer("Тип: tests, full_tests, explanations или discount.")
        return

    try:
        value = int(parts[2])
        max_uses = int(parts[3]) if len(parts) >= 4 else 0
        expires_at = None
        if len(parts) == 5:
            expires_at = datetime.strptime(parts[4], "%Y-%m-%d").replace(hour=23, minute=59, second=59).isoformat()
    except ValueError:
        await message.answer("Количество, лимит или дата указаны неверно.")
        return

    if value < 1 or max_uses < 0 or (reward_type == "discount" and value > 90):
        await message.answer("Количество должно быть больше 0, лимит неотрицательным, скидка — 1–90%.")
        return
    try:
        await db.create_promo_code(code, reward_type, value, max_uses, expires_at, message.from_user.id)
    except sqlite3.IntegrityError:
        await message.answer("Такой промокод уже существует.")
        return

    await state.clear()
    total = await db.count_promo_codes()
    total_pages = max(1, (total + PROMO_PAGE_SIZE - 1) // PROMO_PAGE_SIZE)
    promos = await db.list_promo_codes(limit=PROMO_PAGE_SIZE, offset=0)
    await message.answer(
        f"✅ Промокод <code>{code}</code> создан.",
        reply_markup=admin_promos_keyboard(promos, total_pages=total_pages),
    )


# ─── QUESTIONS ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:q")
async def admin_questions_menu_cb(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    total = await db.count_questions()
    await callback.message.edit_text(
        f"📝 <b>Управление вопросами</b>\n\nВсего вопросов: <b>{total}</b>",
        reply_markup=admin_questions_keyboard(),
    )
    await callback.answer()


# ── List (paginated) ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:q_list:"))
async def admin_questions_list_cb(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    page = int(callback.data.split(":")[-1])
    total = await db.count_questions()
    pages = _total_pages(total)
    page = max(0, min(page, pages - 1))
    questions = await db.list_questions(limit=PAGE_SIZE, offset=page * PAGE_SIZE)

    lines = [f"📋 <b>Вопросы {page * PAGE_SIZE + 1}–{min((page + 1) * PAGE_SIZE, total)} из {total}</b>\n"]
    for q in questions:
        diff = DIFF_LABELS.get(q.get("difficulty", ""), "")
        preview = q["question"][:55] + ("…" if len(q["question"]) > 55 else "")
        lines.append(f"<code>#{q['id']}</code> [{q['language']}] {q['subject']} — {diff}\n  {preview}")

    await callback.message.edit_text(
        "\n".join(lines) or "Вопросов нет.",
        reply_markup=admin_q_list_keyboard(page, pages),
    )
    await callback.answer()


# ── View / field editing ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:q_view:"))
async def admin_view_question_cb(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    q_id = int(callback.data.split(":")[-1])
    q = await db.get_question_by_id(q_id)
    if not q:
        await callback.answer("❌ Вопрос не найден", show_alert=True)
        return
    await callback.message.edit_text(_question_preview(q), reply_markup=admin_q_view_keyboard(q_id))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:qf:"))
async def admin_edit_field_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    _, _, q_id_str, field = callback.data.split(":")
    q_id = int(q_id_str)
    q = await db.get_question_by_id(q_id)
    if not q:
        await callback.answer("❌ Вопрос не найден", show_alert=True)
        return

    await state.set_state(AdminFlow.eq_value)
    await state.update_data(eq_id=q_id, eq_field=field)

    prompts = {
        "question": "✏️ Введите новый текст вопроса:",
        "options": "🔤 Введите новые варианты — каждый с новой строки:",
        "correct": "✅ Введите номер(а) правильного ответа через запятую (1-based):",
        "explanation": "💡 Введите новое объяснение (или «-» чтобы убрать):",
        "subject": "📚 Введите новый slug предмета:",
        "difficulty": "🎯 Введите сложность: easy / medium / hard",
    }
    await callback.message.answer(prompts.get(field, "Введите новое значение:"), reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminFlow.eq_value)
async def admin_edit_field_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    q_id = data["eq_id"]
    field = data["eq_field"]
    value = (message.text or "").strip()

    try:
        if field == "options":
            parsed = [line.strip() for line in value.splitlines() if line.strip()]
            if len(parsed) < 2:
                await message.answer("❌ Минимум 2 варианта.")
                return
            await db.update_question(q_id, options=parsed)
        elif field == "correct":
            parts = [int(x.strip()) - 1 for x in value.split(",")]
            await db.update_question(q_id, correct=parts)
        elif field == "explanation":
            await db.update_question(q_id, explanation=None if value == "-" else value)
        elif field == "difficulty":
            if value not in ("easy", "medium", "hard"):
                await message.answer("❌ Введите: easy, medium или hard")
                return
            await db.update_question(q_id, difficulty=value)
        else:
            await db.update_question(q_id, **{field: value})
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        return

    await state.clear()
    q = await db.get_question_by_id(q_id)
    await message.answer(f"✅ Вопрос #{q_id} обновлён!")
    if q:
        await message.answer(_question_preview(q), reply_markup=admin_q_view_keyboard(q_id))
    await message.answer("⚙️ Админ-панель:", reply_markup=admin_main_keyboard())


# ── Delete ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:q_del_confirm:"))
async def admin_delete_confirm_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    q_id = int(callback.data.split(":")[-1])
    q = await db.get_question_by_id(q_id)
    if not q:
        await callback.answer("❌ Вопрос не найден", show_alert=True)
        return
    preview = q["question"][:80]
    await callback.message.edit_text(
        f"⚠️ <b>Удалить вопрос #{q_id}?</b>\n\n{preview}\n\n<i>Это действие нельзя отменить.</i>",
        reply_markup=admin_q_delete_confirm_keyboard(q_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:q_del:"))
async def admin_delete_question_cb(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    q_id = int(callback.data.split(":")[-1])
    await db.delete_question(q_id)
    await state.clear()
    total = await db.count_questions()
    await callback.message.edit_text(
        f"🗑 Вопрос #{q_id} удалён.\n\nВсего вопросов: <b>{total}</b>",
        reply_markup=admin_questions_keyboard(),
    )
    await callback.answer("✅ Удалено")


# ── FSM: Enter question ID for edit ──────────────────────────────────────────

@router.callback_query(F.data == "adm:q_edit_start")
async def admin_q_edit_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(AdminFlow.eq_id)
    await callback.message.answer("✏️ Введите ID вопроса:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminFlow.eq_id)
async def admin_q_edit_id(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        q_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Введите числовой ID:")
        return
    q = await db.get_question_by_id(q_id)
    if not q:
        await message.answer(f"❌ Вопрос #{q_id} не найден. Попробуйте ещё раз:")
        return
    await state.clear()
    await message.answer(_question_preview(q), reply_markup=admin_q_view_keyboard(q_id))
    await message.answer("⚙️ Выберите поле для редактирования.")


# ── FSM: Enter question ID for delete ─────────────────────────────────────────

@router.callback_query(F.data == "adm:q_del_start")
async def admin_q_del_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(AdminFlow.dq_id)
    await callback.message.answer("🗑 Введите ID вопроса для удаления:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminFlow.dq_id)
async def admin_q_del_id(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        q_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Введите числовой ID:")
        return
    q = await db.get_question_by_id(q_id)
    if not q:
        await message.answer(f"❌ Вопрос #{q_id} не найден.")
        await state.clear()
        return
    await state.clear()
    await message.answer(
        f"⚠️ <b>Удалить вопрос #{q_id}?</b>\n\n{q['question'][:80]}\n\n<i>Нельзя отменить.</i>",
        reply_markup=admin_q_delete_confirm_keyboard(q_id),
    )


# ── FSM: Search questions ─────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:q_search")
async def admin_search_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(AdminFlow.sq_query)
    await callback.message.answer(
        "🔎 Введите поисковый запрос:\n<i>ID, текст вопроса или предмет</i>",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminFlow.sq_query)
async def admin_search_execute(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    query = (message.text or "").strip()
    if not query:
        await message.answer("❌ Введите запрос:")
        return
    await state.clear()

    total = await db.count_search_questions(query)
    results = await db.search_questions_db(query, limit=PAGE_SIZE, offset=0)

    if not results:
        await message.answer(
            f"🔎 По запросу «{query}» ничего не найдено.",
            reply_markup=admin_main_keyboard(),
        )
        return

    lines = [f"🔎 <b>Результаты поиска</b> «{query}» — {total} шт.\n"]
    for q in results:
        diff = DIFF_LABELS.get(q.get("difficulty", ""), "")
        preview = q["question"][:60] + ("…" if len(q["question"]) > 60 else "")
        lines.append(f"<code>#{q['id']}</code> [{q['language']}] {q['subject']} {diff}\n  {preview}")

    await message.answer("\n".join(lines))
    if len(results) == 1:
        q = results[0]
        await message.answer(_question_preview(q), reply_markup=admin_q_view_keyboard(q["id"]))
    else:
        await message.answer("⚙️ Нажмите на ID чтобы открыть вопрос, или:", reply_markup=admin_questions_keyboard())


# ── FSM: Add question ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:q_add")
async def admin_add_q_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(AdminFlow.aq_lang)
    await callback.message.answer("➕ <b>Добавление вопроса</b>\n\nШаг 1/7 — Выберите язык:", reply_markup=admin_aq_lang_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("aq:lang:"), AdminFlow.aq_lang)
async def aq_set_lang(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    lang_code = callback.data.split(":")[-1]
    await state.update_data(aq_lang=lang_code)
    await state.set_state(AdminFlow.aq_subject)
    subjects = await db.all_subjects()
    await callback.message.edit_text(
        f"Шаг 2/7 — Выберите предмет:\n<i>Язык: {lang_code.upper()}</i>",
        reply_markup=admin_aq_subject_keyboard(subjects),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("aq:subj:"), AdminFlow.aq_subject)
async def aq_set_subject(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    subject = callback.data.split(":")[-1]
    await state.update_data(aq_subject=subject)
    await state.set_state(AdminFlow.aq_text)
    await callback.message.edit_text(
        f"Шаг 3/7 — Введите текст вопроса:\n<i>Предмет: {subject}</i>"
    )
    await callback.answer()


@router.message(AdminFlow.aq_text)
async def aq_set_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    await state.update_data(aq_text=(message.text or "").strip())
    await state.set_state(AdminFlow.aq_options)
    await message.answer(
        "Шаг 4/7 — Введите варианты ответа, каждый с новой строки:\n\n"
        "<i>Пример:\nВариант А\nВариант Б\nВариант В\nВариант Г</i>"
    )


@router.message(AdminFlow.aq_options)
async def aq_set_options(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    options = [line.strip() for line in (message.text or "").splitlines() if line.strip()]
    if len(options) < 2:
        await message.answer("❌ Минимум 2 варианта ответа. Введите снова:")
        return
    await state.update_data(aq_options=options)
    await state.set_state(AdminFlow.aq_correct)
    await message.answer(
        "Шаг 5/7 — Выберите правильный ответ:",
        reply_markup=admin_aq_correct_keyboard(options),
    )


@router.callback_query(F.data.startswith("aq:ans:"), AdminFlow.aq_correct)
async def aq_set_correct(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    idx = int(callback.data.split(":")[-1])
    await state.update_data(aq_correct=[idx])
    await state.set_state(AdminFlow.aq_explanation)
    data = await state.get_data()
    opts = data.get("aq_options", [])
    letter = OPTION_LETTERS[idx] if idx < len(OPTION_LETTERS) else str(idx + 1)
    await callback.message.edit_text(
        f"Правильный ответ: <b>{letter}) {opts[idx] if idx < len(opts) else ''}</b>\n\n"
        "Шаг 6/7 — Введите объяснение (или «-» чтобы пропустить):"
    )
    await callback.answer()


@router.message(AdminFlow.aq_explanation)
async def aq_set_explanation(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    text = (message.text or "").strip()
    explanation = None if text == "-" else text
    await state.update_data(aq_explanation=explanation)
    await state.set_state(AdminFlow.aq_difficulty)
    await message.answer("Шаг 7/7 — Выберите сложность:", reply_markup=admin_aq_difficulty_keyboard())


@router.callback_query(F.data.startswith("aq:diff:"), AdminFlow.aq_difficulty)
async def aq_set_difficulty(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    difficulty = callback.data.split(":")[-1]
    await state.update_data(aq_difficulty=difficulty)
    data = await state.get_data()

    # Build preview
    opts = data.get("aq_options", [])
    correct = data.get("aq_correct", [0])
    correct_letters = ", ".join(OPTION_LETTERS[i] for i in correct if i < len(OPTION_LETTERS))
    opt_lines = "\n".join(f"{OPTION_LETTERS[i]}) {o}" for i, o in enumerate(opts) if i < len(OPTION_LETTERS))
    expl = data.get("aq_explanation") or "—"
    preview = (
        f"📋 <b>Предпросмотр</b>\n\n"
        f"📚 Предмет: <b>{data.get('aq_subject')}</b>  🌐 Язык: <b>{data.get('aq_lang', '').upper()}</b>\n"
        f"🎯 Сложность: <b>{DIFF_LABELS.get(difficulty, difficulty)}</b>\n\n"
        f"❓ {data.get('aq_text')}\n\n"
        f"{opt_lines}\n\n"
        f"✅ Правильный ответ: <b>{correct_letters}</b>\n"
        f"💡 {expl}\n\n"
        "<b>Сохранить?</b>"
    )
    await callback.message.edit_text(preview, reply_markup=admin_aq_save_keyboard())
    await callback.answer()


@router.callback_query(F.data == "aq:save")
async def aq_save(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    data = await state.get_data()
    q_id = await db.add_question(
        subject=data.get("aq_subject", "other"),
        language=data.get("aq_lang", "ru"),
        question=data.get("aq_text", ""),
        options=data.get("aq_options", []),
        correct=data.get("aq_correct", [0]),
        explanation=data.get("aq_explanation"),
        difficulty=data.get("aq_difficulty", "medium"),
    )
    await state.clear()
    await callback.message.edit_text(
        f"✅ Вопрос <b>#{q_id}</b> успешно сохранён!",
        reply_markup=admin_questions_keyboard(),
    )
    await callback.answer("✅ Сохранено!")


# ─── SUBJECTS ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:subj")
async def admin_subjects_cb(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    subjects = await db.all_subjects()
    await callback.message.edit_text(
        "📚 <b>Предметы</b>\n\n✅ — активен  |  ❌ — отключён\nНажмите для вкл/выкл или используйте кнопки:",
        reply_markup=admin_subjects_keyboard(subjects),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:stog:"))
async def admin_toggle_subject_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    subj_id = int(callback.data.split(":")[-1])
    await db.toggle_subject(subj_id)
    subjects = await db.all_subjects()
    await callback.message.edit_reply_markup(reply_markup=admin_subjects_keyboard(subjects))
    await callback.answer("✅ Изменено")


@router.callback_query(F.data == "adm:subj_add")
async def admin_add_subject_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(AdminFlow.subj_add_slug)
    await callback.message.answer("➕ Введите slug предмета (только латиница, без пробелов):\n<i>Пример: russian_lit</i>", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminFlow.subj_add_slug)
async def admin_add_subject_slug(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    slug = (message.text or "").strip().lower().replace(" ", "_")
    if not slug.replace("_", "").isalpha():
        await message.answer("❌ Slug должен содержать только латинские буквы и _")
        return
    await state.update_data(subj_slug=slug)
    await state.set_state(AdminFlow.subj_add_title)
    await message.answer(f"Slug: <code>{slug}</code>\n\nТеперь введите название предмета:")


@router.message(AdminFlow.subj_add_title)
async def admin_add_subject_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    title = (message.text or "").strip()
    await db.add_subject(data["subj_slug"], title)
    await state.clear()
    subjects = await db.all_subjects()
    await message.answer(f"✅ Предмет «{title}» добавлен!", reply_markup=admin_main_keyboard())
    await message.answer("📚 <b>Предметы</b>:", reply_markup=admin_subjects_keyboard(subjects))


@router.callback_query(F.data.startswith("adm:sedit:"))
async def admin_edit_subject_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    subj_id = int(callback.data.split(":")[-1])
    await state.set_state(AdminFlow.subj_edit_title)
    await state.update_data(subj_edit_id=subj_id)
    await callback.message.answer("✏️ Введите новое название предмета:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminFlow.subj_edit_title)
async def admin_edit_subject_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    title = (message.text or "").strip()
    await db.update_subject_title(data["subj_edit_id"], title)
    await state.clear()
    subjects = await db.all_subjects()
    await message.answer(f"✅ Название обновлено: «{title}»")
    await message.answer("📚 <b>Предметы</b>:", reply_markup=admin_subjects_keyboard(subjects))


@router.callback_query(F.data.startswith("adm:sdel_c:"))
async def admin_delete_subject_confirm(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    subj_id = int(callback.data.split(":")[-1])
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"adm:sdel:{subj_id}"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="adm:subj")],
    ])
    await callback.message.answer(f"⚠️ Удалить предмет #{subj_id}?\nВопросы с этим предметом останутся в базе.", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:sdel:"))
async def admin_delete_subject_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    subj_id = int(callback.data.split(":")[-1])
    deleted, cnt = await db.delete_subject_safe(subj_id)
    if not deleted:
        await callback.answer(f"❌ Нельзя удалить: {cnt} активных вопросов", show_alert=True)
        return
    subjects = await db.all_subjects()
    await callback.message.edit_text("🗑 Предмет удалён.\n\n📚 <b>Предметы</b>:", reply_markup=admin_subjects_keyboard(subjects))
    await callback.answer("✅ Удалено")


# ─── USERS ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:users")
async def admin_users_menu_cb(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    total = await db.count_users()
    new_today = await db.count_new_today()
    active_today = await db.count_active_today()
    text = (
        f"👥 <b>Пользователи</b>\n\n"
        f"Всего: <b>{total}</b>\n"
        f"Новых сегодня: <b>{new_today}</b>\n"
        f"Активных сегодня: <b>{active_today}</b>"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список", callback_data="adm:u_list:0"),
         InlineKeyboardButton(text="🔎 Найти по ID", callback_data="adm:u_search")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm:main")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:u_list:"))
async def admin_users_list_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    page = int(callback.data.split(":")[-1])
    total = await db.count_users()
    pages = _total_pages(total)
    page = max(0, min(page, pages - 1))
    users = await db.list_users(limit=PAGE_SIZE, offset=page * PAGE_SIZE)

    lines = [f"👥 <b>Пользователи {page * PAGE_SIZE + 1}–{min((page + 1) * PAGE_SIZE, total)} из {total}</b>\n"]
    for u in users:
        name = escape(u.get("first_name") or u.get("username") or str(u["id"]))
        uname = f"@{escape(u['username'])}" if u.get("username") else "—"
        lines.append(f"<code>{u['id']}</code> {name} {uname} [{u['language']}] {u['created_at'][:10]}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=admin_users_list_keyboard(page, pages),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:u_search")
async def admin_users_search_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(AdminFlow.users_search)
    await callback.message.answer("🔎 Введите Telegram ID пользователя:", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(AdminFlow.users_search)
async def admin_users_search_execute(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        user_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Введите числовой Telegram ID:")
        return
    await state.clear()
    info = await db.get_user_admin_info(user_id)
    if not info:
        await message.answer(f"❌ Пользователь с ID {user_id} не найден.", reply_markup=admin_main_keyboard())
        return
    text, kb = _admin_user_card(info)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("adm:user_ban:"))
async def admin_toggle_user_ban(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    try:
        user_id = int(callback.data.rsplit(":", 1)[1])
    except (AttributeError, ValueError):
        await callback.answer("Некорректный пользователь.", show_alert=True)
        return
    if user_id in settings.admin_ids:
        await callback.answer("Нельзя блокировать администратора.", show_alert=True)
        return
    info = await db.get_user_admin_info(user_id)
    if info is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    changed = await db.set_user_banned(user_id, not bool(info["is_banned"]))
    if not changed:
        await callback.answer("Не удалось изменить статус пользователя.", show_alert=True)
        return
    info = await db.get_user_admin_info(user_id)
    if info is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    text, keyboard = _admin_user_card(info)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("Статус пользователя изменён.")


# ─── STATISTICS ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:stats")
async def admin_stats_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await _show_stats(callback, days=None)


@router.callback_query(F.data.startswith("adm:stats:"))
async def admin_stats_period_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    days_str = callback.data.split(":")[-1]
    days = int(days_str) if days_str != "0" else None
    await _show_stats(callback, days=days)


async def _show_stats(callback: CallbackQuery, days: int | None) -> None:
    stats = await db.get_admin_stats(days=days)
    period = {1: "Сегодня", 7: "За 7 дней", 30: "За 30 дней"}.get(days, "За всё время")
    pop = stats.get("popular", [])
    pop_text = ", ".join(f"{s}({c})" for s, c in pop) if pop else "—"
    text = (
        f"📊 <b>Статистика</b> — {period}\n\n"
        f"👥 Пользователей: <b>{stats['users']}</b>\n"
        f"📝 Тестов пройдено: <b>{stats['tests']}</b>\n"
        f"📈 Средний результат: <b>{stats['avg_score']}%</b>\n"
        f"❓ Активных вопросов: <b>{stats['questions']}</b>\n\n"
        f"💳 Платежей (unlocks): <b>{stats['payments']}</b> — <b>{stats['payment_stars']} ⭐</b>\n"
        f"⭐ Донатов: <b>{stats['donations']}</b> — <b>{stats['donation_stars']} ⭐</b>\n\n"
        f"🏆 Топ предметы: {pop_text}"
    )
    await callback.message.edit_text(text, reply_markup=admin_stats_keyboard())
    await callback.answer()


# ─── PAYMENTS ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:pay")
async def admin_payments_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await _show_payments(callback, "all", 0)


@router.callback_query(F.data.startswith("adm:pay:"))
async def admin_payments_filtered_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    parts = callback.data.split(":")
    filter_type = parts[2]
    page = int(parts[3]) if len(parts) > 3 else 0
    await _show_payments(callback, filter_type, page)


async def _show_payments(callback: CallbackQuery, filter_type: str, page: int) -> None:
    total = await db.count_payments_admin(filter_type)
    pages = _total_pages(total)
    page = max(0, min(page, pages - 1))
    payments = await db.get_payments_admin(filter_type, limit=PAGE_SIZE, offset=page * PAGE_SIZE)

    filter_label = {"all": "Все", "paid": "Оплаченные", "unlock": "Разблокировки"}.get(filter_type, filter_type)
    lines = [f"💳 <b>Платежи — {filter_label}</b> ({total})\n"]
    for p in payments:
        status = "✅" if p["status"] == "paid" else "⏳"
        lines.append(
            f"{status} <code>#{p['id']}</code> uid:{p['user_id']} "
            f"{p['amount']}⭐ {p['product_type']} {p['created_at'][:10]}"
        )
    await callback.message.edit_text(
        "\n".join(lines) or "Платежей нет.",
        reply_markup=admin_payments_keyboard(filter_type, page, pages),
    )
    await callback.answer()


# ─── DONATIONS ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:don")
async def admin_donations_menu_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await _show_donations(callback, 0)


@router.callback_query(F.data.startswith("adm:don:"))
async def admin_donations_paged_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    page = int(callback.data.split(":")[-1])
    await _show_donations(callback, page)


async def _show_donations(callback: CallbackQuery, page: int) -> None:
    total_cnt, total_stars = await db.count_donations_total()
    pages = _total_pages(total_cnt)
    page = max(0, min(page, pages - 1))
    donations = await db.list_donations(limit=PAGE_SIZE, offset=page * PAGE_SIZE)

    lines = [f"⭐ <b>Донаты</b>\n\nВсего: {total_cnt} | Получено: {total_stars} ⭐\n"]
    for d in donations:
        status = "✅" if d["status"] == "paid" else "⏳"
        lines.append(f"{status} uid:{d['user_id']} {d['amount']}⭐ {d['created_at'][:10]}")
    await callback.message.edit_text(
        "\n".join(lines) or "Донатов нет.",
        reply_markup=admin_donations_keyboard(page, pages),
    )
    await callback.answer()


# ─── SETTINGS ─────────────────────────────────────────────────────────────────

SETTING_DEFAULTS = {
    "donation_min_stars": settings.donation_min_stars,
    "donation_max_stars": settings.donation_max_stars,
}

SETTING_RANGES = {
    "donation_min_stars": (1, 100),
    "donation_max_stars": (100, 100000),
}

SETTING_LABELS = {
    "donation_min_stars": "⭐ Минимальный донат",
    "donation_max_stars": "⭐ Максимальный донат",
}


@router.callback_query(F.data == "adm:settings")
async def admin_settings_cb(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.clear()
    current = await db.runtime.get_all()
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\nНажмите на параметр для изменения:",
        reply_markup=admin_settings_keyboard(current, SETTING_DEFAULTS),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:set:"))
async def admin_set_setting_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    key = callback.data[len("adm:set:"):]
    if key not in SETTING_DEFAULTS:
        await callback.answer("❌ Неизвестный параметр", show_alert=True)
        return
    rng = SETTING_RANGES.get(key, (1, 999999))
    label = SETTING_LABELS.get(key, key)
    current_val = db.runtime.get_int(key, SETTING_DEFAULTS[key])
    await state.set_state(AdminFlow.set_value)
    await state.update_data(set_key=key)
    await callback.message.answer(
        f"⚙️ <b>{label}</b>\n\nТекущее значение: <b>{current_val}</b>\n"
        f"Допустимый диапазон: {rng[0]} – {rng[1]}\n\n"
        "Введите новое значение:",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminFlow.set_value)
async def admin_set_setting_value(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    key = data["set_key"]
    text = (message.text or "").strip()

    if not text.isdigit():
        await message.answer("❌ Введите целое положительное число:")
        return

    value = int(text)
    rng = SETTING_RANGES.get(key, (1, 999999))
    if not (rng[0] <= value <= rng[1]):
        await message.answer(f"❌ Значение должно быть от {rng[0]} до {rng[1]}:")
        return

    await db.runtime.set_value(key, str(value))
    await state.clear()
    current = await db.runtime.get_all()
    await message.answer(f"✅ Настройка обновлена: <b>{value}</b>")
    await message.answer(
        "⚙️ <b>Настройки</b>:",
        reply_markup=admin_settings_keyboard(current, SETTING_DEFAULTS),
    )


# ─── IMPORT BULK QUESTIONS ─────────────────────────────────────────────────────

@router.callback_query(F.data.in_({"adm:import", "adm:q_import"}))
async def admin_import_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    await state.set_state(AdminFlow.import_wait)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Скачать шаблон", callback_data="adm:template")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="adm:main")],
    ])
    await callback.message.answer(
        "📥 <b>Массовая загрузка вопросов</b>\n\n"
        "Отправьте файл в формате <b>JSON</b>, <b>CSV</b> или <b>XLSX</b>.\n\n"
        "Поддерживаются форматы: <b>.json</b>, <b>.csv</b> и <b>.xlsx</b>.\n\n"
        "Обязательные поля записи:\n"
        "<code>subject</code>, <code>question_text</code>, <code>options</code>, <code>correct_option_index</code>\n\n"
        "Дополнительно: <code>topic</code>, <code>language</code>, <code>explanation</code>, <code>difficulty</code>\n\n"
        "После отправки я проверю файл и, при успехе, добавлю вопросы в базу и покажу их названия.",
        reply_markup=kb,
    )
    await callback.answer()


@router.message(AdminFlow.import_wait, F.document)
async def admin_import_file(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    try:
        file = await message.bot.get_file(message.document.file_id)
        raw_bytes = await message.bot.download_file(file.file_path)
        file_name = message.document.file_name or file.file_path.rsplit("/", 1)[-1]
        await _process_import_payload(message, state, raw_bytes, file_name=file_name)
    except Exception as exc:  # pragma: no cover - defensive guard for Telegram transport errors
        await message.answer(f"❌ Не удалось прочитать файл: {exc}")
        return


@router.message(AdminFlow.import_wait, F.text)
async def admin_import_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    await _process_import_payload(message, state, message.text or "")


async def _process_import_payload(message: Message, state: FSMContext, raw: str | bytes, file_name: str | None = None) -> None:
    try:
        rows = parse_import_payload(raw, file_name=file_name)
    except ValueError as exc:
        await message.answer(f"❌ {exc}\n\nИспользуйте шаблон: /get_template")
        return

    valid = []
    errors = []
    duplicates = 0
    dup_cache: dict[tuple[str, str], set[str]] = {}
    subject_aliases = {
        name.strip().casefold(): subject["slug"]
        for subject in await db.all_subjects()
        for name in (subject["slug"], subject["title"])
    }

    for idx, item in enumerate(rows, start=1):
        subject_name = str(item["subject"]).strip()
        subject_slug = subject_aliases.get(subject_name.casefold())
        if subject_slug is None:
            errors.append(f"#{idx}: неизвестный предмет «{escape(subject_name)}»")
            continue
        item["subject"] = subject_slug
        key = (subject_slug, str(item["language"]).strip() or "ru")
        if key not in dup_cache:
            dup_cache[key] = await db.get_existing_question_texts(key[0], key[1])
        question_normalized = item["question"].strip().lower()
        if question_normalized in dup_cache[key]:
            duplicates += 1
            continue
        dup_cache[key].add(question_normalized)
        valid.append({
            "subject": item["subject"],
            "topic": item.get("topic"),
            "language": item["language"],
            "question": item["question"],
            "options": item["options"],
            "correct": item["correct"],
            "explanation": item.get("explanation"),
            "difficulty": item.get("difficulty", "medium"),
        })

    if errors:
        error_lines = "\n".join(errors[:10])
        if len(errors) > 10:
            error_lines += f"\n... и ещё {len(errors) - 10} ошибок"
        await message.answer(
            "❌ Импорт отменён: исправьте неизвестные предметы.\n"
            "Создайте свой предмет в разделе «Предметы» или используйте slug из шаблона.\n\n"
            f"{error_lines}"
        )
        return

    total = len(rows)
    summary = (
        f"📊 <b>Результат проверки</b>\n\n"
        f"Всего записей: <b>{total}</b>\n"
        f"✅ Валидных: <b>{len(valid)}</b>\n"
        f"⚠️ Дубликатов: <b>{duplicates}</b>\n"
        f"❌ Ошибок: <b>0</b>"
    )

    if not valid:
        await state.clear()
        await message.answer(summary + "\n\n❌ Нечего импортировать.", reply_markup=admin_main_keyboard())
        return

    summary += f"\n\n<b>Импортировать {len(valid)} вопросов?</b>"
    _pending_imports[message.from_user.id] = valid
    await state.clear()
    await message.answer(summary, reply_markup=admin_import_confirm_keyboard())


@router.callback_query(F.data == "adm:import_ok")
async def admin_import_confirm_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    items = _pending_imports.pop(callback.from_user.id, None)
    if not items:
        await callback.answer("❌ Данные для импорта не найдены. Начните заново.", show_alert=True)
        return
    try:
        count = await db.import_questions(items)
    except ValueError as exc:
        logger.warning("Question import rejected at confirmation: %s", exc)
        await callback.message.answer(
            f"❌ Импорт отменён: {escape(str(exc))}. Проверьте предметы и загрузите файл повторно.",
            reply_markup=admin_main_keyboard(),
        )
        await callback.answer("Импорт не выполнен.", show_alert=True)
        return
    total_now = await db.count_questions()
    success_text = build_import_success_text(items, imported_count=count)
    await callback.message.edit_text(
        f"{success_text}\n\n"
        f"<b>Всего в базе:</b> <b>{total_now}</b>",
        reply_markup=admin_main_keyboard(),
    )
    await callback.answer(f"✅ Импортировано: {count}")


@router.callback_query(F.data == "adm:import_cancel")
async def admin_import_cancel_cb(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await _deny(callback)
        return
    _pending_imports.pop(callback.from_user.id, None)
    await callback.message.edit_text("❌ Импорт отменён.", reply_markup=admin_main_keyboard())
    await callback.answer()
