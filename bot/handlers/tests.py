from __future__ import annotations

import random
import time
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice

import database as db
from bot.keyboards import answer_keyboard, premium_keyboard, result_questions_keyboard
from bot.locale import t
from bot.states import TestFlow
from bot.handlers.payments import TEST_PRICE_STARS
from config import settings

router = Router()

OPTION_LETTERS = "АБВГДЕЖЗ"


@router.callback_query(F.data.startswith("subject:"))
async def start_test(callback: CallbackQuery, state: FSMContext) -> None:
    subject = callback.data.split(":", 1)[1]
    lang = await db.get_user_language(callback.from_user.id)
    amount = max(1, db.runtime.get_int("questions_per_test", settings.questions_per_test))
    questions = await db.get_unresolved_questions(callback.from_user.id, subject, lang, amount=amount)
    if not questions:
        await callback.message.answer(t(lang, "no_questions"))
        await callback.answer()
        return

    access = await db.consume_test_access(callback.from_user.id, subscriber_daily_limit=5)
    if access == "daily_limit":
        await callback.message.answer("Вы использовали дневную квоту Premium (5 тестов). Новые тесты будут доступны завтра.")
        await callback.answer()
        return
    if access == "payment_required":
        try:
            await callback.bot.send_invoice(
                chat_id=callback.from_user.id,
                title="Один тест",
                description="Доступ к новому тесту",
                payload=f"test:{callback.from_user.id}:{subject}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Один тест", amount=TEST_PRICE_STARS)],
            )
        except Exception:
            await callback.message.answer("Не удалось выставить счёт. Попробуйте снова позже.")
        await callback.answer()
        return

    random.shuffle(questions)

    await state.set_state(TestFlow.answering)
    await state.update_data(
        questions=questions,
        answers=[],
        current=0,
        subject=subject,
        start_time=time.time(),
        score=0,
        option_map={},
    )

    try:
        await callback.message.edit_text(f"🎯 Тест начался. Вопросов: {len(questions)}")
    except Exception:
        pass
    await _send_question(callback, state, questions[0], 1, len(questions), lang)
    await callback.answer()


def _shuffle_options_for_question(question: dict) -> tuple[list[str], dict[int, int]]:
    options = list(question.get("options", []))
    if len(options) < 2:
        return options, {i: i for i in range(len(options))}

    original_indexes = list(range(len(options)))
    random.shuffle(original_indexes)
    shuffled = [options[i] for i in original_indexes]
    mapping = {idx: old_idx for idx, old_idx in enumerate(original_indexes)}
    return shuffled, mapping


async def _send_question(callback: CallbackQuery, state: FSMContext, question: dict, current: int, total: int, lang: str) -> None:
    shuffled_options, mapping = _shuffle_options_for_question(question)
    text = t(lang, "question", current=current, total=total, text=escape(question["question"]))
    await callback.message.answer(text, reply_markup=answer_keyboard(question["id"], shuffled_options))

    current_data = await state.get_data()
    option_map = current_data.get("option_map", {})
    option_map[str(question["id"])] = [mapping[index] for index in range(len(mapping))]
    await state.update_data(option_map=option_map)


@router.callback_query(F.data.startswith("ans:"), TestFlow.answering)
async def handle_answer(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        _, q_id_str, selected_str = callback.data.split(":")
        q_id, selected = int(q_id_str), int(selected_str)
        data = await state.get_data()
        current = data["questions"][data["current"]]
    except (ValueError, KeyError, IndexError, TypeError):
        await callback.answer()
        return

    if current["id"] != q_id or selected < 0 or selected >= len(current["options"]):
        await callback.answer()
        return

    lang = await db.get_user_language(callback.from_user.id)
    stored_map = data.get("option_map", {}).get(str(q_id))
    if stored_map is None:
        await callback.answer()
        return
    display_options = [current["options"][index] for index in stored_map]
    correct_list: list[int] = current["correct"]
    correct_idx = correct_list[0] if correct_list else 0
    correct_display = stored_map.index(correct_idx) if correct_idx in stored_map else 0
    is_correct = selected == correct_display
    letters = OPTION_LETTERS

    answers: list[dict] = data["answers"]
    answers.append({
        "qid": q_id,
        "selected": selected,
        "correct": correct_display,
        "is_correct": is_correct,
        "question": current["question"],
        "options": display_options,
        "explanation": current.get("explanation") or "",
        "selected_letter": letters[selected] if selected < len(letters) else str(selected + 1),
        "correct_letter": letters[correct_display] if correct_display < len(letters) else str(correct_display + 1),
    })

    score = data["score"] + (1 if is_correct else 0)
    next_idx = data["current"] + 1
    await state.update_data(answers=answers, current=next_idx, score=score)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    questions = data["questions"]
    if next_idx < len(questions):
        await _send_question(callback, state, questions[next_idx], next_idx + 1, len(questions), lang)
    else:
        await _finish_test(callback, state, data, answers, score, lang)

    await callback.answer()


async def _finish_test(callback: CallbackQuery, state: FSMContext, data: dict, answers: list[dict], score: int, lang: str) -> None:
    total = len(answers)
    subject = data["subject"]
    subjects = await db.get_subjects()
    subject_title = next((item["title"] for item in subjects if item["slug"] == subject), subject)
    result_id = await db.save_result(
        user_id=callback.from_user.id,
        subject=subject,
        mode="practice",
        score=score,
        total=total,
        time_sec=max(0, int(time.time() - data["start_time"])),
        answers=answers,
    )
    await db.record_solved_questions(callback.from_user.id, subject, [answer["qid"] for answer in answers])

    percent = round(score / total * 100) if total else 0
    lines = [
        f"📊 Ваши результаты по предмету: {escape(subject_title)}",
        f"Правильно: {score} / {total} ({percent}%)",
        "",
    ]
    for index, answer in enumerate(answers):
        status = "✅ Верно" if answer["is_correct"] else f"❌ Неверно (Правильный: {answer['correct_letter']})"
        lines.append(f"{index + 1}. {answer['selected_letter']} — {status}")
    lines.extend(["", "💡 Нажмите на номер вопроса ниже, чтобы посмотреть подробный разбор задачи:"])

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=result_questions_keyboard(
            result_id,
            total,
            db.runtime.get_int("answer_unlock_price", settings.answer_unlock_price),
            lang,
        ),
    )

    await state.clear()


@router.callback_query(F.data.startswith("review:"))
async def review_question(callback: CallbackQuery) -> None:
    try:
        _, result_id_text, index_text = callback.data.split(":")
        result_id, index = int(result_id_text), int(index_text)
    except (ValueError, AttributeError):
        await callback.answer("Не удалось открыть разбор.", show_alert=True)
        return

    result = await db.get_result_for_user(result_id, callback.from_user.id)
    if result is None or index < 0 or index >= len(result["answers"]):
        await callback.answer("Результат не найден.", show_alert=True)
        return

    has_unlocked_result = await db.user_has_unlocked_result(callback.from_user.id, result_id)
    if not has_unlocked_result and not await db.consume_explanation_access(callback.from_user.id):
        await callback.answer("Подробный разбор доступен по подписке Premium.", show_alert=True)
        await callback.message.answer(
            "💎 Подробный разбор доступен только подписчикам Premium. Выберите тариф:",
            reply_markup=premium_keyboard(),
        )
        return

    answer = result["answers"][index]
    explanation = answer.get("explanation") or "Разбор к этому вопросу пока не добавлен."
    options = answer.get("options", [])
    correct_index = answer.get("correct", 0)
    correct_answer = options[correct_index] if 0 <= correct_index < len(options) else "Не указан"
    text = (
        f"💡 <b>Разбор вопроса {index + 1}</b>\n\n"
        f"{escape(answer.get('question', ''))}\n\n"
        f"✅ Правильный ответ: {escape(correct_answer)}\n\n"
        f"{escape(explanation)}"
    )
    await callback.message.answer(text)
    await callback.answer()
