from __future__ import annotations

import asyncio
import logging
import socket
import threading

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from bot.handlers import (
    admin_router,
    payments_router,
    start_router,
    statistics_router,
    tests_router,
)
from bot.middlewares import BanMiddleware
from config import settings
import database as db
from bot.subscription_notifications import run_subscription_expiry_notifier

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _get_free_port(host: str, preferred_port: int) -> int:
    for port in (preferred_port, 0):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                return sock.getsockname()[1]
        except OSError:
            continue
    return preferred_port


def start_health_server() -> None:
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    port = _get_free_port(settings.health_host, settings.health_port)
    if port != settings.health_port:
        logger.warning(
            "Port %s is busy; health server started on fallback port %s",
            settings.health_port,
            port,
        )

    def run() -> None:
        uvicorn.run(app, host=settings.health_host, port=port, log_level="warning")

    threading.Thread(target=run, daemon=True).start()
    logger.info("Health server on %s:%s", settings.health_host, port)


async def main() -> None:
    await db.init_db()
    await db.runtime.load()   # load admin-configured settings into memory
    logger.info("Database ready: %s", settings.db_path)

    start_health_server()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    ban_middleware = BanMiddleware()
    dp.message.outer_middleware(ban_middleware)
    dp.callback_query.outer_middleware(ban_middleware)
    dp.pre_checkout_query.outer_middleware(ban_middleware)

    # ORDER MATTERS:
    # start_router is FIRST → its handlers (menu buttons, /start, ❌ Отмена)
    # take priority over FSM-state-specific handlers and auto-clear state.
    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(payments_router)
    dp.include_router(statistics_router)
    dp.include_router(tests_router)

    logger.info("Bot @%s starting...", (await bot.get_me()).username)
    notifier_task = asyncio.create_task(run_subscription_expiry_notifier(bot))
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        notifier_task.cancel()
        await asyncio.gather(notifier_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
