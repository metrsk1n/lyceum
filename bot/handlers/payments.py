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
from bot.keyboards import donation_confirm_keyboard, main_menu, paid_test_keyboard
from bot.locale import t
from bot.states import DonationFlow
from config import settings

logger = logging.getLogger(__name__)
router = Router()
SUBSCRIPTION_PLANS = {
    "week": (150, 7),
    "month": (450, 30),
    "halfyear": (1800, 180),
}
TEST_PRICE_STARS = 25


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
        if len(parts) != 3:
            raise ValueError
        result_id = int(parts[1])
        price = int(parts[2])
    except ValueError:
        await callback.answer("Некорректный запрос на разбор.", show_alert=True)
        return
    expected_price = db.runtime.get_int("answer_unlock_price", settings.answer_unlock_price)
    if price != expected_price:
        await callback.answer("Цена изменилась. Обновите сообщение и попробуйте снова.", show_alert=True)
        return
    if await db.get_result_for_user(result_id, callback.from_user.id) is None:
        await callback.answer("Результат не найден.", show_alert=True)
        return
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Разбор теста",
        description="Открытие правильных ответов и объяснений",
        payload=f"unlock:{callback.from_user.id}:{result_id}",
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
        description="Доступ к подробному разбору ответов и истории ошибок",
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
    elif payload.startswith("unlock:"):
        parts = payload.split(":")
        expected_amount = db.runtime.get_int("answer_unlock_price", settings.answer_unlock_price)
        if (
            len(parts) != 3 or not parts[1].isdigit() or int(parts[1]) != query.from_user.id
            or not parts[2].isdigit()
            or query.total_amount != expected_amount or query.currency != "XTR"
            or await db.get_result_for_user(int(parts[2]), query.from_user.id) is None
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
            plan_names = {"week": "7 дней", "month": "1 месяц", "halfyear": "6 месяцев"}
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

    elif payload.startswith("unlock:"):
        parts = payload.split(":")
        expected_amount = db.runtime.get_int("answer_unlock_price", settings.answer_unlock_price)
        if (
            len(parts) != 3 or not parts[1].isdigit() or int(parts[1]) != user_id
            or not parts[2].isdigit()
            or amount != expected_amount or sp.currency != "XTR"
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
        if await db.record_paid_payment(user_id, charge_id, payload, amount, "unlock"):
            logger.info("Unlock uid=%s stars=%s", user_id, amount)
        await message.answer(t(lang, "unlock_success"))
        lines = [t(lang, "answers_list")]
        for i, answer in enumerate(result["answers"], 1):
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
                lines.append(f"   💡 {escape(answer['explanation'])}")
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
