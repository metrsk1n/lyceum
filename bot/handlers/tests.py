from __future__ import annotations

import random
import json
import logging
import time
from functools import lru_cache
from html import escape
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice

import database as db
from bot.keyboards import answer_keyboard, premium_keyboard, result_questions_keyboard, test_size_keyboard
from bot.locale import t
from bot.pricing import (
    EXPLANATION_PRICE_STARS,
    FULL_MOCK_SUBJECTS,
    FULL_TEST_PRICE_STARS,
    TEST_PRICE_STARS,
    TEST_QUESTIONS,
)
from bot.states import TestFlow

router = Router()
logger = logging.getLogger(__name__)

OPTION_LETTERS = "АБВГДЕЖЗ"
FULL_MOCK_QUESTIONS_PER_SUBJECT = 20
SUBJECT_TITLES = {
    "mathematics": {"ru": "Математика", "en": "Mathematics", "uz": "Matematika"},
    "english": {"ru": "Английский", "en": "English", "uz": "Ingliz tili"},
    "iq": {"ru": "IQ", "en": "IQ", "uz": "IQ"},
}


@lru_cache(maxsize=1)
def _static_mocks() -> dict[str, list[dict]]:
    path = Path(__file__).resolve().parents[2] / "data" / "static_mocks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = {"english", "mathematics", "iq"}
    if set(data) != expected or any(len(data[subject]) != 100 for subject in expected):
        raise ValueError(f"Static mock bank must have 100 questions per subject: {path}")
    return data


@router.callback_query(F.data.startswith("subject:"))
async def choose_test_size(callback: CallbackQuery) -> None:
    subject = callback.data.split(":", 1)[1]
    subjects = {item["slug"] for item in await db.get_subjects()}
    if subject not in subjects:
        await callback.answer("Предмет не найден.", show_alert=True)
        return
    amount = TEST_QUESTIONS
    await callback.message.edit_text(
        "Полный мок: 60 вопросов — по 20 по математике, английскому и IQ.\n"
        "Выберите формат теста:",
        reply_markup=test_size_keyboard(
            subject,
            amount,
            FULL_TEST_PRICE_STARS,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("testsize:"))
async def start_test(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    if len(parts) != 3 or parts[2] not in {"regular", "full"}:
        await callback.answer("Некорректный формат теста.", show_alert=True)
        return
    subject, size = parts[1], parts[2]
    subjects = {item["slug"] for item in await db.get_subjects()}
    if size == "regular" and subject not in subjects:
        await callback.answer("Предмет не найден.", show_alert=True)
        return
    if size == "full" and subject not in {*FULL_MOCK_SUBJECTS, "all"}:
        await callback.answer("Предмет не найден.", show_alert=True)
        return

    lang = await db.get_user_language(callback.from_user.id)
    if size == "full":
        questions = []
        missing_subjects = []
        for mock_subject in FULL_MOCK_SUBJECTS:
            subject_questions = await db.get_unresolved_questions(
                callback.from_user.id,
                mock_subject,
                lang,
                amount=FULL_MOCK_QUESTIONS_PER_SUBJECT,
            )
            if len(subject_questions) != FULL_MOCK_QUESTIONS_PER_SUBJECT:
                missing_subjects.append(SUBJECT_TITLES[mock_subject].get(lang, mock_subject))
            questions.extend(subject_questions)
        if missing_subjects:
            await callback.message.answer(
                "Полный мок пока недоступен: не хватает вопросов в предметах "
                f"{', '.join(missing_subjects)}. Требуется по 20 вопросов для каждого предмета."
            )
            await callback.answer()
            return
        subject = "full_mock"
    else:
        questions = await db.get_unresolved_questions(
            callback.from_user.id,
            subject,
            lang,
            amount=TEST_QUESTIONS,
        )
        if len(questions) < TEST_QUESTIONS:
            await callback.message.answer(t(lang, "no_questions"))
            await callback.answer()
            return

    access = (
        await db.consume_full_test_access(callback.from_user.id, subscriber_daily_limit=5)
        if size == "full"
        else await db.consume_test_access(callback.from_user.id, subscriber_daily_limit=5)
    )
    if access == "daily_limit":
        await callback.message.answer("Вы использовали дневную квоту Premium (5 тестов). Новые тесты будут доступны завтра.")
        await callback.answer()
        return
    if access == "payment_required":
        price = (
            FULL_TEST_PRICE_STARS if size == "full" else TEST_PRICE_STARS
        )
        payload_type = "full_test" if size == "full" else "test"
        title = "Полный мок" if size == "full" else "Один тест"
        description = (
            "60 вопросов: по 20 по математике, английскому и IQ"
            if size == "full"
            else "Доступ к новому тесту"
        )
        payload = (
            f"{payload_type}:{callback.from_user.id}"
            if size == "full"
            else f"{payload_type}:{callback.from_user.id}:{subject}"
        )
        try:
            await callback.bot.send_invoice(
                chat_id=callback.from_user.id,
                title=title,
                description=description,
                payload=payload,
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label=title, amount=price)],
            )
        except Exception:
            await callback.message.answer("Не удалось выставить счёт. Попробуйте снова позже.")
        await callback.answer()
        return

    if size != "full":
        random.shuffle(questions)

    await _start_test(callback, state, questions, subject, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("mock:"))
async def start_free_mock(callback: CallbackQuery, state: FSMContext) -> None:
    subject = callback.data.split(":", 1)[1]
    if subject not in {"english", "mathematics", "iq"}:
        await callback.answer("Бесплатный мок не найден.", show_alert=True)
        return
    lang = await db.get_user_language(callback.from_user.id)
    mock_items = _static_mocks()[subject]
    questions = [
        {
            "id": item["id"],
            "question": item["question_text"],
            "options": item["options"],
            "correct": [item["correct_option_index"]],
            "explanation": item["explanation"],
        }
        for item in mock_items
    ]
    if not await db.claim_free_mock(callback.from_user.id, subject):
        await callback.answer("Этот бесплатный мок уже использован.", show_alert=True)
        return
    await _start_test(callback, state, questions, subject, lang, free_mock=True)
    await callback.answer()


async def _start_test(
    callback: CallbackQuery,
    state: FSMContext,
    questions: list[dict],
    subject: str,
    lang: str,
    free_mock: bool = False,
) -> None:
    await state.set_state(TestFlow.answering)
    await state.update_data(
        questions=questions,
        answers=[],
        current=0,
        subject=subject,
        start_time=time.time(),
        score=0,
        option_map={},
        free_mock=free_mock,
        full_mock=subject == "full_mock",
    )

    await callback.message.answer(f"🎯 Тест начался. Вопросов: {len(questions)}")
    await _send_question(callback, state, questions[0], 1, len(questions), lang)


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
    current_data = await state.get_data()
    if current_data.get("full_mock"):
        subject = question.get("subject")
        title = SUBJECT_TITLES.get(subject, {}).get(lang, subject or "")
        text = f"📚 <b>{escape(title)}</b>\n{text}"
    await callback.message.answer(text, reply_markup=answer_keyboard(question["id"], shuffled_options))

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
        "subject": current.get("subject", data["subject"]),
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
    if subject == "full_mock":
        subject_title = {
            "ru": "Полный мок · математика, английский и IQ",
            "en": "Full mock · Mathematics, English, and IQ",
            "uz": "To'liq mock · Matematika, Ingliz tili va IQ",
        }.get(lang, "Полный мок")
    else:
        subject_title = next((item["title"] for item in subjects if item["slug"] == subject), subject)
    result_id = await db.save_result(
        user_id=callback.from_user.id,
        subject=subject,
        mode="free_mock" if data.get("free_mock") else "full_mock" if data.get("full_mock") else "practice",
        score=score,
        total=total,
        time_sec=max(0, int(time.time() - data["start_time"])),
        answers=answers,
    )
    if data.get("free_mock"):
        await db.complete_free_mock(callback.from_user.id, subject)
    elif data.get("full_mock"):
        question_ids_by_subject: dict[str, list[int]] = {}
        for answer in answers:
            answer_subject = answer.get("subject")
            if answer_subject:
                question_ids_by_subject.setdefault(answer_subject, []).append(answer["qid"])
        for answer_subject, question_ids in question_ids_by_subject.items():
            await db.record_solved_questions(callback.from_user.id, answer_subject, question_ids)
    else:
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

    if await db.user_has_active_subscription(callback.from_user.id):
        unlock_subjects = []
    elif subject == "full_mock":
        unlock_subjects = [
            (slug, SUBJECT_TITLES[slug].get(lang, slug))
            for slug in FULL_MOCK_SUBJECTS
        ]
    else:
        unlock_subjects = [(
            subject,
            next((item["title"] for item in subjects if item["slug"] == subject), subject),
        )]
    await callback.message.answer(
        "\n".join(lines),
        reply_markup=result_questions_keyboard(
            result_id,
            total,
            EXPLANATION_PRICE_STARS,
            lang,
            unlock_subjects,
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

    answer = result["answers"][index]
    answer_subject = answer.get("subject") or result["subject"]
    has_unlocked_result = await db.user_has_unlocked_result(
        callback.from_user.id,
        result_id,
        answer_subject,
    )
    if not has_unlocked_result and not await db.consume_explanation_access(callback.from_user.id):
        await callback.answer("Подробный разбор доступен по подписке Premium.", show_alert=True)
        await callback.message.answer(
            "💎 Подробный разбор доступен только подписчикам Premium. Выберите тариф:",
            reply_markup=premium_keyboard(),
        )
        return

    explanation = answer.get("explanation") or "Разбор к этому вопросу пока не добавлен."
    options = answer.get("options", [])
    correct_index = answer.get("correct", 0)
    correct_answer = options[correct_index] if 0 <= correct_index < len(options) else "Не указан"
    steps = [line.strip() for line in explanation.splitlines() if line.strip()]
    formatted_steps = "\n".join(f"\t{escape(step)}" for step in steps)
    text = (
        f"💡 <b>Разбор вопроса {index + 1}</b>\n\n"
        f"{escape(answer.get('question', ''))}\n\n"
        f"✅ Правильный ответ: {escape(correct_answer)}\n\n"
        f"<pre>{formatted_steps}</pre>"
    )
    await callback.message.answer(text)
    await callback.answer()
