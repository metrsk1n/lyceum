from __future__ import annotations

from dataclasses import dataclass

from aiogram.types import InlineKeyboardMarkup

import database as db
from bot.keyboards import premium_keyboard
from bot.locale import t

SUBSCRIPTION_PLANS = {
    "week": (200, 7),
    "month": (700, 30),
    "quarter": (2000, 90),
}

_PRICE_SETTING_KEYS = {
    "week": "premium_week_stars",
    "month": "premium_month_stars",
    "quarter": "premium_quarter_stars",
}


@dataclass(frozen=True)
class SubscriptionQuote:
    base_amount: int
    amount: int
    days: int
    discount_percent: int
    discount_code: str | None


async def get_subscription_quote(user_id: int, plan: str) -> SubscriptionQuote | None:
    base_plan = SUBSCRIPTION_PLANS.get(plan)
    if base_plan is None:
        return None

    base_amount = db.runtime.get_int(_PRICE_SETTING_KEYS[plan], base_plan[0])
    admin_discount = db.runtime.get_int("premium_discount_percent", 0)
    user_discount = await db.get_user_subscription_discount(user_id)
    user_percent, user_code = user_discount if user_discount else (0, None)

    discount_percent = max(admin_discount, user_percent)
    discount_code = user_code if user_percent >= admin_discount and user_percent > 0 else None
    amount = (
        0
        if discount_percent == 100
        else max(1, round(base_amount * (100 - discount_percent) / 100))
    )
    return SubscriptionQuote(
        base_amount=base_amount,
        amount=amount,
        days=base_plan[1],
        discount_percent=discount_percent,
        discount_code=discount_code,
    )


async def premium_presentation(user_id: int, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    quotes = {
        plan: await get_subscription_quote(user_id, plan)
        for plan in SUBSCRIPTION_PLANS
    }
    labels = {
        "ru": {
            "title": "💳 <b>Тарифы:</b>",
            "week": "1 неделя",
            "month": "1 месяц",
            "quarter": "3 месяца",
        },
        "uz": {
            "title": "💳 <b>Tariflar:</b>",
            "week": "1 hafta",
            "month": "1 oy",
            "quarter": "3 oy",
        },
        "en": {
            "title": "💳 <b>Plans:</b>",
            "week": "1 week",
            "month": "1 month",
            "quarter": "3 months",
        },
    }.get(lang, {
        "title": "💳 <b>Тарифы:</b>",
        "week": "1 неделя",
        "month": "1 месяц",
        "quarter": "3 месяца",
    })
    lines = [labels["title"]]
    for plan, quote in quotes.items():
        if quote is None:
            continue
        price = f"<b>{quote.amount} ⭐</b>"
        if quote.discount_percent and quote.amount < quote.base_amount:
            price = (
                f"<s>{quote.base_amount} ⭐</s> → {price} "
                f"(−{quote.discount_percent}%)"
            )
        lines.append(f"• {labels[plan]} — {price}")

    text = f"{t(lang, 'premium_description')}\n\n" + "\n".join(lines)
    prices = {plan: quote.amount for plan, quote in quotes.items() if quote is not None}
    return text, premium_keyboard(lang, prices)
