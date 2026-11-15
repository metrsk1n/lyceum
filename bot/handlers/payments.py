from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, LabeledPrice, Message,
    PreCheckoutQuery, SuccessfulPayment,
)

import database as db
from bot.keyboards import (
    donation_confirm_keyboard,
    main_menu,
    paid_full_test_keyboard,
    paid_test_keyboard,
    result_questions_keyboard,
)
from bot.locale import t
from bot.pricing import (
    EXPLANATION_PRICE_STARS,
    FULL_MOCK_SUBJECTS,
    FULL_TEST_PRICE_STARS,
    TEST_PRICE_STARS,
)
from bot.states import DonationFlow
from config import settings

logger = logging.getLogger(__name__)
router = Router()
SUBSCRIPTION_PLANS = {
    "week": (200, 7),
    "month": (700, 30),
    "quarter": (2000, 90),
}


def _result_has_subject(result: dict, subject: str) -> bool:
    if result["subject"] == "full_mock":
        return (
            subject in FULL_MOCK_SUBJECTS
            and any(answer.get("subject") == subject for answer in result["answers"])
        )
    return subject == result["subject"]


# ─── Payment history ──────────────────────────────────────────────────────────

@router.message(F.text.in_({"💳 Платежи", "💳 Payments", "💳 To'lovlar"}))
@router.message(Command("payments"))
async def show_payments(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = await db.get_user_language(message.from_user.id)
    payments = await db.get_user_payments(message.from_user.id)
    if not payments:
        await message.answer(t(lang, "payments_empty"))
        return
    lines = [t(lang, "payments_list")]
    for p in payments:
        lines.append(t(lang, "payment_item",
            date=p["created_at"][:10], type=p["product_type"],
            amount=p["amount"], status=p["status"],
        ))
    await message.answer("".join(lines))


# ─── Unlock answers ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("unlock:"))
async def unlock_answers(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    try:
        if len(parts) == 4:
            result_id = int(parts[1])
            subject = parts[2]
            price = int(parts[3])
        elif len(parts) == 3:
            result_id = int(parts[1])
            subject = None
            price = int(parts[2])
        else:
            raise ValueError
    except ValueError:
        await callback.answer("Некорректный запрос на разбор.", show_alert=True)
        return
    if price != EXPLANATION_PRICE_STARS:
        await callback.answer("Цена изменилась. Обновите сообщение и попробуйте снова.", show_alert=True)
        return
    result = await db.get_result_for_user(result_id, callback.from_user.id)
    if result is None:
        await callback.answer("Результат не найден.", show_alert=True)
        return
    if subject is not None and not _result_has_subject(result, subject):
        await callback.answer("В этом результате нет такого предмета.", show_alert=True)
        return
    has_subscription = await db.user_has_active_subscription(callback.from_user.id)
    if subject is None and result["subject"] == "full_mock":
        lang = await db.get_user_language(callback.from_user.id)
        titles = {
            "mathematics": {"ru": "Математика", "en": "Mathematics", "uz": "Matematika"},
            "english": {"ru": "Английский", "en": "English", "uz": "Ingliz tili"},
            "iq": {"ru": "IQ", "en": "IQ", "uz": "IQ"},
        }
        unlock_subjects = [
            (slug, titles[slug].get(lang, slug))
            for slug in ("mathematics", "english", "iq")
            if _result_has_subject(result, slug)
        ] if not has_subscription else []
        await callback.message.edit_reply_markup(
            reply_markup=result_questions_keyboard(
                result_id,
                len(result["answers"]),
                EXPLANATION_PRICE_STARS,
                lang,
                unlock_subjects,
            ),
        )
        await callback.answer(
            "Premium уже открывает разборы без доплаты."
            if has_subscription else "Выберите предмет для разбора."
        )
        return
    if has_subscription:
        await callback.answer("Premium уже открывает разборы без доплаты.")
        return
    if await db.user_has_unlocked_result(callback.from_user.id, result_id, subject):
        await callback.answer("Разбор этого предмета уже открыт.", show_alert=True)
        return
    payment_payload = (
        f"unlock:{callback.from_user.id}:{result_id}:{subject}"
        if subject is not None
        else f"unlock:{callback.from_user.id}:{result_id}"
    )
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Разбор предмета",
        description="Открытие объяснений по выбранному предмету",
        payload=payment_payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=price)],
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sub:"))
async def premium_subscription(callback: CallbackQuery) -> None:
    plan = callback.data.split(":", 1)[1]
    subscription = SUBSCRIPTION_PLANS.get(plan)
    if subscription is None:
        await callback.answer("Неизвестный тариф.", show_alert=True)
        return
    base_amount, _ = subscription
    discount = await db.get_user_subscription_discount(callback.from_user.id)
    discount_code = discount[1] if discount else None
    amount = max(1, round(base_amount * (100 - discount[0]) / 100)) if discount else base_amount
    payload = f"sub:{plan}:{callback.from_user.id}"
    if discount_code:
        payload += f":{discount_code}"

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Premium подписка",
        description="До 5 тестов в день, подробные разборы ответов и история ошибок",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=amount)],
    )
    await callback.answer()


# ─── Donation flow ────────────────────────────────────────────────────────────

@router.message(F.text.in_({"🌟 Поддержать", "🌟 Support", "🌟 Qo'llab-quvvatlash"}))
async def donation_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    lang = await db.get_user_language(message.from_user.id)
    min_s = db.runtime.get_int("donation_min_stars", settings.donation_min_stars)
    max_s = db.runtime.get_int("donation_max_stars", settings.donation_max_stars)
    await state.set_state(DonationFlow.waiting_amount)
    await message.answer(t(lang, "support_prompt", min=min_s, max=max_s))


@router.message(DonationFlow.waiting_amount)
async def donation_amount(message: Message, state: FSMContext) -> None:
    lang = await db.get_user_language(message.from_user.id)
    min_s = db.runtime.get_int("donation_min_stars", settings.donation_min_stars)
    max_s = db.runtime.get_int("donation_max_stars", settings.donation_max_stars)

    text = message.text or ""
    if not text.isdigit():
        await message.answer(t(lang, "support_invalid", min=min_s, max=max_s))
        return

    amount = int(text)
    if not (min_s <= amount <= max_s):
        await message.answer(t(lang, "support_invalid", min=min_s, max=max_s))
        return

    await state.clear()
    await message.answer(
        t(lang, "support_preview", amount=amount),
        reply_markup=donation_confirm_keyboard(lang, amount),
    )


@router.callback_query(F.data.startswith("donate_confirm:"))
async def donation_confirm(callback: CallbackQuery) -> None:
    try:
        amount = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректная сумма.", show_alert=True)
        return
    min_s = db.runtime.get_int("donation_min_stars", settings.donation_min_stars)
    max_s = db.runtime.get_int("donation_max_stars", settings.donation_max_stars)
    if not min_s <= amount <= max_s:
        await callback.answer("Сумма доната недоступна. Начните заново.", show_alert=True)
        return
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Поддержать проект",
        description=f"Донат {amount} ⭐ Stars",
        payload=f"donation:{callback.from_user.id}:{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=amount)],
    )
    await callback.answer()


@router.callback_query(F.data == "donate_cancel")
async def donation_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("Отменено")


# ─── Telegram payment processing ──────────────────────────────────────────────

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    payload = query.invoice_payload
    if payload.startswith("sub:"):
        parts = payload.split(":")
        if len(parts) not in {3, 4} or not parts[2].isdigit() or int(parts[2]) != query.from_user.id:
            await query.answer(ok=False, error_message="Не удалось проверить подписку.")
            return
        plan = SUBSCRIPTION_PLANS.get(parts[1])
        discount = await db.get_user_subscription_discount(query.from_user.id)
        if len(parts) == 4:
            if not discount or discount[1] != parts[3]:
                await query.answer(ok=False, error_message="Скидка больше недоступна.")
                return
            expected_amount = max(1, round(plan[0] * (100 - discount[0]) / 100)) if plan else 0
        else:
            expected_amount = plan[0] if plan else 0
        if plan is None or query.total_amount != expected_amount or query.currency != "XTR":
            await query.answer(ok=False, error_message="Тариф или сумма платежа не совпадает.")
            return
    elif payload.startswith("test:"):
        parts = payload.split(":")
        subjects = {subject["slug"] for subject in await db.get_subjects()}
        if (
            len(parts) != 3 or not parts[1].isdigit() or int(parts[1]) != query.from_user.id
            or parts[2] not in subjects or query.total_amount != TEST_PRICE_STARS or query.currency != "XTR"
        ):
            await query.answer(ok=False, error_message="Не удалось проверить покупку теста.")
            return
    elif payload.startswith("full_test:"):
        parts = payload.split(":")
        subjects = {subject["slug"] for subject in await db.get_subjects()}
        if (
            len(parts) not in {2, 3} or not parts[1].isdigit()
            or int(parts[1]) != query.from_user.id
            or (len(parts) == 3 and parts[2] not in subjects)
            or query.total_amount != FULL_TEST_PRICE_STARS
            or query.currency != "XTR"
        ):
            await query.answer(ok=False, error_message="Не удалось проверить покупку полного мока.")
            return
    elif payload.startswith("unlock:"):
        parts = payload.split(":")
        result = None
        valid_payload = (
            len(parts) in {3, 4}
            and parts[1].isdigit()
            and int(parts[1]) == query.from_user.id
            and parts[2].isdigit()
        )
        if valid_payload:
            result = await db.get_result_for_user(int(parts[2]), query.from_user.id)
        if len(parts) == 3 and result is not None and result["subject"] == "full_mock":
            valid_payload = False
        if len(parts) == 4 and result is not None:
            valid_payload = valid_payload and _result_has_subject(result, parts[3])
        if (
            not valid_payload
            or query.total_amount != EXPLANATION_PRICE_STARS
            or query.currency != "XTR"
        ):
            await query.answer(ok=False, error_message="Не удалось проверить покупку разбора.")
            return
    elif payload.startswith("donation:"):
        parts = payload.split(":")
        min_s = db.runtime.get_int("donation_min_stars", settings.donation_min_stars)
        max_s = db.runtime.get_int("donation_max_stars", settings.donation_max_stars)
        if (
            len(parts) != 3 or not parts[1].isdigit() or int(parts[1]) != query.from_user.id
            or not parts[2].isdigit() or int(parts[2]) != query.total_amount
            or not min_s <= query.total_amount <= max_s or query.currency != "XTR"
        ):
            await query.answer(ok=False, error_message="Не удалось проверить донат.")
            return
    else:
        await query.answer(ok=False, error_message="Неизвестный платёж.")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    sp: SuccessfulPayment = message.successful_payment
    charge_id = sp.telegram_payment_charge_id
    payload = sp.invoice_payload
    amount = sp.total_amount
    user_id = message.from_user.id
    lang = await db.get_user_language(user_id)

    if payload.startswith("donation:"):
        parts = payload.split(":")
        min_s = db.runtime.get_int("donation_min_stars", settings.donation_min_stars)
        max_s = db.runtime.get_int("donation_max_stars", settings.donation_max_stars)
        if (
            len(parts) != 3 or not parts[1].isdigit() or int(parts[1]) != user_id
            or not parts[2].isdigit() or int(parts[2]) != amount
            or not min_s <= amount <= max_s or sp.currency != "XTR"
        ):
            logger.error("Invalid donation payment payload=%s amount=%s", payload, amount)
            await message.answer("Платёж получен, но донат не удалось проверить. Обратитесь в поддержку.")
            return
        await db.create_donation(user_id, charge_id, amount)
        if await db.confirm_donation(charge_id):
            logger.info("Donation uid=%s stars=%s", user_id, amount)
        await message.answer(t(lang, "support_thanks", amount=amount))

    elif payload.startswith("sub:"):
        parts = payload.split(":")
        plan = SUBSCRIPTION_PLANS.get(parts[1]) if len(parts) in {3, 4} and parts[2].isdigit() and int(parts[2]) == user_id else None
        discount = await db.get_user_subscription_discount(user_id)
        if len(parts) == 4 and discount and discount[1] == parts[3] and plan:
            expected_amount = max(1, round(plan[0] * (100 - discount[0]) / 100))
        else:
            expected_amount = plan[0] if plan else 0
        if (
            plan is None or amount != expected_amount or sp.currency != "XTR"
            or (len(parts) == 4 and (not discount or discount[1] != parts[3]))
        ):
            logger.error("Invalid subscription payment payload=%s amount=%s", payload, amount)
            await message.answer("Платёж получен, но тариф не удалось проверить. Поддержка уже уведомлена.")
            return

        previous = await db.get_latest_subscription_expiry(user_id)
        starts_at = max(datetime.now(), previous) if previous else datetime.now()
        expires_at = (starts_at + timedelta(days=plan[1])).isoformat(timespec="seconds")
        if await db.record_paid_payment(user_id, charge_id, payload, amount, "subscription", expires_at):
            if len(parts) == 4:
                await db.consume_user_subscription_discount(user_id, parts[3])
            logger.info("Premium uid=%s plan=%s stars=%s", user_id, parts[1], amount)
            plan_names = {"week": "1 неделю", "month": "1 месяц", "quarter": "3 месяца"}
            await message.answer(
                f"✅ Успешная покупка подписки Premium на {plan_names[parts[1]]}.\n"
                f"Подписка действует до {datetime.fromisoformat(expires_at).strftime('%d.%m.%Y %H:%M')}."
            )
        else:
            await message.answer("✅ Этот платёж уже обработан, Premium активен.")

    elif payload.startswith("test:"):
        parts = payload.split(":")
        subjects = {subject["slug"] for subject in await db.get_subjects()}
        if (
            len(parts) != 3 or not parts[1].isdigit() or int(parts[1]) != user_id
            or parts[2] not in subjects or amount != TEST_PRICE_STARS or sp.currency != "XTR"
        ):
            logger.error("Invalid test payment payload=%s amount=%s", payload, amount)
            await message.answer("Платёж получен, но покупку теста не удалось проверить. Обратитесь в поддержку.")
            return
        if await db.record_test_purchase(user_id, charge_id, payload, amount):
            await message.answer(
                "✅ Оплата получена. Тест добавлен на ваш баланс.",
                reply_markup=paid_test_keyboard(),
            )
        else:
            await message.answer("✅ Этот платёж уже был обработан.")

    elif payload.startswith("full_test:"):
        parts = payload.split(":")
        subjects = {subject["slug"] for subject in await db.get_subjects()}
        if (
            len(parts) not in {2, 3} or not parts[1].isdigit()
            or int(parts[1]) != user_id
            or (len(parts) == 3 and parts[2] not in subjects)
            or amount != FULL_TEST_PRICE_STARS or sp.currency != "XTR"
        ):
            logger.error("Invalid full test payment payload=%s amount=%s", payload, amount)
            await message.answer("Платёж получен, но покупку полного мока не удалось проверить. Обратитесь в поддержку.")
            return
        if await db.record_full_test_purchase(user_id, charge_id, payload, amount):
            await message.answer(
                "✅ Оплата получена. Полный мок (60 вопросов: по 20 по математике, английскому и IQ) добавлен на баланс.",
                reply_markup=paid_full_test_keyboard(),
            )
        else:
            await message.answer("✅ Этот платёж уже был обработан.")

    elif payload.startswith("unlock:"):
        parts = payload.split(":")
        valid_payload = (
            len(parts) in {3, 4}
            and parts[1].isdigit()
            and int(parts[1]) == user_id
            and parts[2].isdigit()
        )
        if (
            not valid_payload
            or amount != EXPLANATION_PRICE_STARS
            or sp.currency != "XTR"
        ):
            logger.error("Invalid unlock payment payload=%s amount=%s", payload, amount)
            await message.answer("Платёж получен, но покупку разбора не удалось проверить. Обратитесь в поддержку.")
            return
        result_id = int(parts[2])
        result = await db.get_result_for_user(result_id, user_id)
        if result is None:
            logger.error("Paid unlock refers to missing result: uid=%s result_id=%s", user_id, result_id)
            await message.answer("Платёж получен, но результат не найден. Обратитесь в поддержку.")
            return
        subject = parts[3] if len(parts) == 4 else None
        if subject is not None and not _result_has_subject(result, subject):
            logger.error(
                "Paid unlock refers to missing subject: uid=%s result_id=%s subject=%s",
                user_id,
                result_id,
                subject,
            )
            await message.answer("Платёж получен, но предмет не найден. Обратитесь в поддержку.")
            return
        if await db.record_paid_payment(user_id, charge_id, payload, amount, "unlock"):
            logger.info("Unlock uid=%s stars=%s", user_id, amount)
        await message.answer(t(lang, "unlock_success"))
        lines = [t(lang, "answers_list")]
        unlock_answers_list = [
            answer for answer in result["answers"]
            if subject is None or (answer.get("subject") or result["subject"]) == subject
        ]
        for i, answer in enumerate(unlock_answers_list, 1):
            mark = "✅" if answer.get("is_correct") else "❌"
            options = answer.get("options", [])
            correct_index = answer.get("correct", 0)
            correct_text = (
                options[correct_index]
                if isinstance(correct_index, int) and 0 <= correct_index < len(options)
                else "?"
            )
            lines.append(
                f"{i}. {mark} {escape(answer.get('question', ''))}\n"
                f"   → {escape(str(correct_text))}"
            )
            if answer.get("explanation"):
                steps = [
                    f"\t{escape(line.strip())}"
                    for line in answer["explanation"].splitlines()
                    if line.strip()
                ]
                lines.append(f"<pre>{chr(10).join(steps)}</pre>")
            lines.append("")

        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0
        for line in lines:
            if current_chunk and current_length + len(line) + 1 > 3500:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(line)
            current_length += len(line) + 1
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        for chunk in chunks:
            await message.answer(chunk)
    else:
        logger.warning("Unknown payment payload: %s", payload)
