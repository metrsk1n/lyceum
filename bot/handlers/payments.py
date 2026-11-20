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
from bot.subscriptions import (
    SUBSCRIPTION_PLANS,
    get_subscription_quote,
)
from config import settings

logger = logging.getLogger(__name__)
router = Router()


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
    lang = await db.get_user_language(callback.from_user.id)
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
        await callback.answer(t(lang, "unlock_invalid_request"), show_alert=True)
        return
    if price != EXPLANATION_PRICE_STARS:
        await callback.answer(t(lang, "unlock_price_changed"), show_alert=True)
        return
    result = await db.get_result_for_user(result_id, callback.from_user.id)
    if result is None:
        await callback.answer(t(lang, "result_not_found"), show_alert=True)
        return
    if subject is not None and not _result_has_subject(result, subject):
        await callback.answer(t(lang, "unlock_subject_not_found"), show_alert=True)
        return
    has_subscription = await db.user_has_active_subscription(callback.from_user.id)
    if subject is None and result["subject"] == "full_mock":
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
            t(lang, "premium_explanations_unlocked")
            if has_subscription else t(lang, "unlock_choose_subject")
        )
        return
    if has_subscription:
        await callback.answer(t(lang, "premium_explanations_unlocked"))
        return
    if await db.user_has_unlocked_result(callback.from_user.id, result_id, subject):
        await callback.answer(t(lang, "unlock_already_open"), show_alert=True)
        return
    payment_payload = (
        f"unlock:{callback.from_user.id}:{result_id}:{subject}"
        if subject is not None
        else f"unlock:{callback.from_user.id}:{result_id}"
    )
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=t(lang, "unlock_invoice_title"),
        description=t(lang, "unlock_invoice_description"),
        payload=payment_payload,
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=price)],
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sub:"))
async def premium_subscription(callback: CallbackQuery) -> None:
    lang = await db.get_user_language(callback.from_user.id)
    plan = callback.data.split(":", 1)[1]
    quote = await get_subscription_quote(callback.from_user.id, plan)
    if quote is None:
        await callback.answer(t(lang, "unknown_plan"), show_alert=True)
        return
    discount_code = quote.discount_code
    if quote.amount == 0:
        expires_at = await db.grant_free_subscription_from_discount(
            callback.from_user.id,
            plan,
            quote.days,
            discount_code,
        )
        if expires_at is None:
            await callback.answer(t(lang, "payment_discount_unavailable"), show_alert=True)
            return
        plan_names = {
            "ru": {"week": "1 неделю", "month": "1 месяц", "quarter": "3 месяца"},
            "uz": {"week": "1 hafta", "month": "1 oy", "quarter": "3 oy"},
            "en": {"week": "1 week", "month": "1 month", "quarter": "3 months"},
        }
        await callback.message.answer(
            t(
                lang,
                "payment_subscription_free",
                plan=plan_names.get(lang, plan_names["ru"])[plan],
                date=expires_at.strftime("%d.%m.%Y %H:%M"),
            )
        )
        await callback.answer()
        return
    amount = quote.amount
    payload = f"sub2:{plan}:{callback.from_user.id}:{amount}"
    if discount_code:
        payload += f":{discount_code}"

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=t(lang, "premium_invoice_title"),
        description=t(lang, "premium_invoice_description"),
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
        lang = await db.get_user_language(callback.from_user.id)
        await callback.answer(t(lang, "donation_invalid_amount"), show_alert=True)
        return
    min_s = db.runtime.get_int("donation_min_stars", settings.donation_min_stars)
    max_s = db.runtime.get_int("donation_max_stars", settings.donation_max_stars)
    if not min_s <= amount <= max_s:
        lang = await db.get_user_language(callback.from_user.id)
        await callback.answer(t(lang, "donation_unavailable"), show_alert=True)
        return
    lang = await db.get_user_language(callback.from_user.id)
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=t(lang, "donation_invoice_title"),
        description=t(lang, "donation_invoice_description", amount=amount),
        payload=f"donation:{callback.from_user.id}:{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=amount)],
    )
    await callback.answer()


@router.callback_query(F.data == "donate_cancel")
async def donation_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_user_language(callback.from_user.id)
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer(t(lang, "cancelled"))


# ─── Telegram payment processing ──────────────────────────────────────────────

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    lang = await db.get_user_language(query.from_user.id)
    payload = query.invoice_payload
    if payload.startswith("sub:"):
        parts = payload.split(":")
        if len(parts) not in {3, 4} or not parts[2].isdigit() or int(parts[2]) != query.from_user.id:
            await query.answer(ok=False, error_message=t(lang, "payment_check_subscription_failed"))
            return
        quote = await get_subscription_quote(query.from_user.id, parts[1])
        expected_amount = quote.amount if quote else 0
        if (len(parts) == 4) != bool(quote and quote.discount_code):
            await query.answer(ok=False, error_message=t(lang, "payment_discount_unavailable"))
            return
        if len(parts) == 4 and quote and quote.discount_code != parts[3]:
            await query.answer(ok=False, error_message=t(lang, "payment_discount_unavailable"))
            return
        if quote is None or query.total_amount != expected_amount or query.currency != "XTR":
            await query.answer(ok=False, error_message=t(lang, "payment_amount_mismatch"))
            return
    elif payload.startswith("sub2:"):
        parts = payload.split(":")
        valid_payload = (
            len(parts) in {4, 5}
            and parts[2].isdigit()
            and int(parts[2]) == query.from_user.id
            and parts[3].isdigit()
        )
        quote = await get_subscription_quote(query.from_user.id, parts[1]) if valid_payload else None
        code = parts[4] if len(parts) == 5 else None
        if (
            not valid_payload or quote is None or int(parts[3]) < 1
            or quote.amount != int(parts[3]) or quote.discount_code != code
            or query.total_amount != int(parts[3]) or query.currency != "XTR"
        ):
            await query.answer(ok=False, error_message=t(lang, "payment_amount_mismatch"))
            return
    elif payload.startswith("test:"):
        parts = payload.split(":")
        subjects = {subject["slug"] for subject in await db.get_subjects()}
        if (
            len(parts) != 3 or not parts[1].isdigit() or int(parts[1]) != query.from_user.id
            or parts[2] not in subjects or query.total_amount != TEST_PRICE_STARS or query.currency != "XTR"
        ):
            await query.answer(ok=False, error_message=t(lang, "payment_check_test_failed"))
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
            await query.answer(ok=False, error_message=t(lang, "payment_check_full_mock_failed"))
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
            await query.answer(ok=False, error_message=t(lang, "payment_check_explanation_failed"))
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
            await query.answer(ok=False, error_message=t(lang, "payment_check_donation_failed"))
            return
    else:
        await query.answer(ok=False, error_message=t(lang, "payment_unknown"))
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
            await message.answer(t(lang, "payment_donation_invalid"))
            return
        await db.create_donation(user_id, charge_id, amount)
        if await db.confirm_donation(charge_id):
            logger.info("Donation uid=%s stars=%s", user_id, amount)
        await message.answer(t(lang, "support_thanks", amount=amount))

    elif payload.startswith(("sub:", "sub2:")):
        parts = payload.split(":")
        is_quoted = parts[0] == "sub2"
        valid_shape = (
            len(parts) in ({4, 5} if is_quoted else {3, 4})
            and parts[2].isdigit()
            and int(parts[2]) == user_id
            and (not is_quoted or parts[3].isdigit())
        )
        plan = SUBSCRIPTION_PLANS.get(parts[1]) if valid_shape else None
        discount_code = (
            parts[4] if is_quoted and len(parts) == 5
            else parts[3] if not is_quoted and len(parts) == 4
            else None
        )
        if is_quoted and valid_shape and parts[3].isdigit():
            expected_amount = int(parts[3])
        else:
            quote = await get_subscription_quote(user_id, parts[1]) if plan else None
            expected_amount = quote.amount if quote else 0
            if quote and quote.discount_code != discount_code:
                expected_amount = 0
        user_discount = await db.get_user_subscription_discount(user_id)
        if (
            plan is None or expected_amount < 1 or amount != expected_amount or sp.currency != "XTR"
            or (discount_code and (not user_discount or user_discount[1] != discount_code))
        ):
            logger.error("Invalid subscription payment payload=%s amount=%s", payload, amount)
            await message.answer(t(lang, "payment_subscription_invalid"))
            return

        previous = await db.get_latest_subscription_expiry(user_id)
        starts_at = max(datetime.now(), previous) if previous else datetime.now()
        expires_at = (starts_at + timedelta(days=plan[1])).isoformat(timespec="seconds")
        if await db.record_paid_payment(user_id, charge_id, payload, amount, "subscription", expires_at):
            if discount_code:
                await db.consume_user_subscription_discount(user_id, discount_code)
            logger.info("Premium uid=%s plan=%s stars=%s", user_id, parts[1], amount)
            plan_names = {
                "ru": {"week": "1 неделю", "month": "1 месяц", "quarter": "3 месяца"},
                "uz": {"week": "1 hafta", "month": "1 oy", "quarter": "3 oy"},
                "en": {"week": "1 week", "month": "1 month", "quarter": "3 months"},
            }.get(lang, {}).get(parts[1], "1 hafta")
            await message.answer(
                t(
                    lang,
                    "payment_subscription_success",
                    plan=plan_names,
                    date=datetime.fromisoformat(expires_at).strftime("%d.%m.%Y %H:%M"),
                )
            )
        else:
            await message.answer(t(lang, "payment_duplicate_subscription"))

    elif payload.startswith("test:"):
        parts = payload.split(":")
        subjects = {subject["slug"] for subject in await db.get_subjects()}
        if (
            len(parts) != 3 or not parts[1].isdigit() or int(parts[1]) != user_id
            or parts[2] not in subjects or amount != TEST_PRICE_STARS or sp.currency != "XTR"
        ):
            logger.error("Invalid test payment payload=%s amount=%s", payload, amount)
            await message.answer(t(lang, "payment_test_invalid"))
            return
        if await db.record_test_purchase(user_id, charge_id, payload, amount):
            await message.answer(
                t(lang, "payment_test_success"),
                reply_markup=paid_test_keyboard(lang),
            )
        else:
            await message.answer(t(lang, "payment_duplicate"))

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
            await message.answer(t(lang, "payment_full_mock_invalid"))
            return
        if await db.record_full_test_purchase(user_id, charge_id, payload, amount):
            await message.answer(
                t(lang, "payment_full_mock_success"),
                reply_markup=paid_full_test_keyboard(lang),
            )
        else:
            await message.answer(t(lang, "payment_duplicate"))

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
            await message.answer(t(lang, "payment_explanation_invalid"))
            return
        result_id = int(parts[2])
        result = await db.get_result_for_user(result_id, user_id)
        if result is None:
            logger.error("Paid unlock refers to missing result: uid=%s result_id=%s", user_id, result_id)
            await message.answer(t(lang, "payment_result_not_found"))
            return
        subject = parts[3] if len(parts) == 4 else None
        if subject is not None and not _result_has_subject(result, subject):
            logger.error(
                "Paid unlock refers to missing subject: uid=%s result_id=%s subject=%s",
                user_id,
                result_id,
                subject,
            )
            await message.answer(t(lang, "payment_subject_not_found"))
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
