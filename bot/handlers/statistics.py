from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

import database as db
from bot.locale import t

router = Router()


async def _show_stats(message: Message) -> None:
    lang = await db.get_user_language(message.from_user.id)
    stats = await db.get_user_stats(message.from_user.id)
    if not stats["total_tests"]:
        await message.answer(t(lang, "stats_empty"))
        return
    await message.answer(t(lang, "stats",
        tests=stats["total_tests"],
        questions=stats["total_q"],
        correct=stats["correct"],
        accuracy=stats["accuracy"],
        best=stats["best"],
    ))
    results = [
        result
        for result in await db.get_user_results(message.from_user.id, limit=10)
        if result.get("status") == "completed"
    ][:5]
    if results:
        titles = {
            "ru": {
                "recent_tests": "📋 <b>Последние сессии:</b>\n",
                "mathematics": "Математика",
                "english": "Английский",
                "iq": "IQ",
            },
            "uz": {
                "recent_tests": "📋 <b>So'nggi seanslar:</b>\n",
                "mathematics": "Matematika",
                "english": "Ingliz tili",
                "iq": "IQ",
            },
            "en": {
                "recent_tests": "📋 <b>Recent sessions:</b>\n",
                "mathematics": "Mathematics",
                "english": "English",
                "iq": "IQ",
            },
        }
        labels = titles.get(lang, titles["ru"])
        lines = [labels["recent_tests"]]
        for r in results:
            pct = round(r["score"] / r["total"] * 100, 1) if r["total"] else 0
            subject = labels.get(r["subject"], r["subject"])
            lines.append(f"• {subject} — {r['score']}/{r['total']} ({pct}%) — {r['finished_at'][:10]}")
        await message.answer("\n".join(lines))


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    await _show_stats(message)
