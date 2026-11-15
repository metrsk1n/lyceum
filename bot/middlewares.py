from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, TelegramObject

import database as db


class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        update_event = event
        user = getattr(update_event, "from_user", None)
        if user is None or not await db.is_user_banned(user.id):
            return await handler(event, data)

        if isinstance(update_event, Message) and update_event.successful_payment:
            return await handler(event, data)
        if isinstance(update_event, PreCheckoutQuery):
            await update_event.answer(
                ok=False,
                error_message="Доступ к боту ограничен. Обратитесь к администратору.",
            )
        elif isinstance(update_event, CallbackQuery):
            await update_event.answer("Доступ к боту ограничен.", show_alert=True)
        elif isinstance(update_event, Message):
            await update_event.answer("Доступ к боту ограничен. Обратитесь к администратору.")
        return None
