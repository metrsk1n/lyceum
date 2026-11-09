from bot.handlers.start import router as start_router
from bot.handlers.tests import router as tests_router
from bot.handlers.statistics import router as statistics_router
from bot.handlers.payments import router as payments_router
from bot.handlers.admin import router as admin_router

__all__ = [
    "start_router",
    "tests_router",
    "statistics_router",
    "payments_router",
    "admin_router",
]
