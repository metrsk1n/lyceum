from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

import database as db

logger = logging.getLogger(__name__)
CHECK_INTERVAL_SECONDS = 3600


def _notice_text(notification_type: str, expires_at: str, language: str) -> str:
    expiry = datetime.fromisoformat(expires_at).strftime("%d.%m.%Y %H:%M")
    messages = {
        "three_days": {
            "ru": f"⏳ Ваша подписка Premium закончится через 3 дня, {expiry}.",
            "uz": f"⏳ Premium obunangiz 3 kundan keyin, {expiry} da tugaydi.",
            "en": f"⏳ Your Premium subscription expires in 3 days, on {expiry}.",
        },
        "expires_today": {
            "ru": f"📅 Сегодня заканчивается ваша подписка Premium ({expiry}). Продлите её, чтобы сохранить доступ к разборам.",
            "uz": f"📅 Premium obunangiz bugun tugaydi ({expiry}). Tahlillardan foydalanish uchun obunani uzaytiring.",
            "en": f"📅 Your Premium subscription expires today ({expiry}). Renew it to keep access to explanations.",
        },
    }
    return messages[notification_type].get(language, messages[notification_type]["ru"])


async def check_subscription_expirations(bot: Bot, today: date | None = None) -> int:
    today = today or date.today()
    notices = [
        ("three_days", today + timedelta(days=3)),
        ("expires_today", today),
    ]
    sent_count = 0

    for notification_type, expiry_date in notices:
        due_subscriptions = await db.get_subscriptions_expiring_on(expiry_date)
        for subscription in due_subscriptions:
            user_id = subscription["user_id"]
            expires_at = subscription["expires_at"]
            if await db.subscription_notice_sent(user_id, expires_at, notification_type):
                continue

            try:
                await bot.send_message(
                    user_id,
                    _notice_text(notification_type, expires_at, await db.get_user_language(user_id)),
                )
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after)
                try:
                    await bot.send_message(
                        user_id,
                        _notice_text(notification_type, expires_at, await db.get_user_language(user_id)),
                    )
                except TelegramForbiddenError:
                    await db.mark_subscription_notice_sent(user_id, expires_at, notification_type)
                    continue
                except Exception:
                    logger.exception("Could not send subscription expiry notice")
                    continue
            except TelegramForbiddenError:
                await db.mark_subscription_notice_sent(user_id, expires_at, notification_type)
                continue
            except Exception:
                logger.exception("Could not send subscription expiry notice")
                continue

            await db.mark_subscription_notice_sent(user_id, expires_at, notification_type)
            sent_count += 1
            await asyncio.sleep(0.05)

    return sent_count


async def run_subscription_expiry_notifier(bot: Bot) -> None:
    while True:
        try:
            await check_subscription_expirations(bot)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Subscription expiry check failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)