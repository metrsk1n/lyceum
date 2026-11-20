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
from bot.keyboards import answer_keyboard, result_questions_keyboard, test_size_keyboard
from bot.subscriptions import premium_presentation
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
    lang = await db.get_user_language(callback.from_user.id)
    subject = callback.data.split(":", 1)[1]
    subjects = {item["slug"] for item in await db.get_subjects()}
    if subject not in subjects:
        await callback.answer(t(lang, "subject_not_found"), show_alert=True)
        return
    amount = TEST_QUESTIONS
    await callback.message.edit_text(
        t(lang, "choose_test_size"),
        reply_markup=test_size_keyboard(
            subject,
            amount,
            FULL_TEST_PRICE_STARS,
            lang,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("testsize:"))
async def start_test(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_user_language(callback.from_user.id)
    parts = callback.data.split(":")
    if len(parts) != 3 or parts[2] not in {"regular", "full"}:
        await callback.answer(t(lang, "test_invalid_format"), show_alert=True)
        return
    subject, size = parts[1], parts[2]
    subjects = {item["slug"] for item in await db.get_subjects()}
    if size == "regular" and subject not in subjects:
        await callback.answer(t(lang, "subject_not_found"), show_alert=True)
        return
    if size == "full" and subject not in {*FULL_MOCK_SUBJECTS, "all"}:
        await callback.answer(t(lang, "subject_not_found"), show_alert=True)
        return

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
                t(lang, "full_mock_missing", subjects=", ".join(missing_subjects))
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
        await callback.message.answer(t(lang, "daily_limit"))
        await callback.answer()
        return
    if access == "payment_required":
        price = (
            FULL_TEST_PRICE_STARS if size == "full" else TEST_PRICE_STARS
        )
        payload_type = "full_test" if size == "full" else "test"
        title = t(lang, "full_mock_title") if size == "full" else t(lang, "single_test_title")
        description = (
            t(lang, "full_mock_invoice_description")
            if size == "full"
            else t(lang, "test_invoice_description")
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
            await callback.message.answer(t(lang, "invoice_failed"))
        await callback.answer()
        return

    if size != "full":
        random.shuffle(questions)

    await _start_test(callback, state, questions, subject, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("mock:"))
async def start_free_mock(callback: CallbackQuery, state: FSMContext) -> None:
    subject = callback.data.split(":", 1)[1]
    if subject != "full":
        await callback.answer(t(await db.get_user_language(callback.from_user.id), "free_mock_not_found"), show_alert=True)
        return
    lang = await db.get_user_language(callback.from_user.id)
    mocks = _static_mocks()
    questions = []
    for mock_subject in FULL_MOCK_SUBJECTS:
        for item in random.sample(mocks[mock_subject], FULL_MOCK_QUESTIONS_PER_SUBJECT):
            use_uzbek = lang == "uz"
            questions.append({
                "id": -(len(questions) + 1),
                "subject": mock_subject,
                "question": item["question_text_uz"] if use_uzbek else item["question_text"],
                "options": item["options_uz"] if use_uzbek else item["options"],
                "correct": [item["correct_option_index"]],
                "explanation": item["explanation_uz"] if use_uzbek else item["explanation"],
            })
    random.shuffle(questions)
    if not await db.consume_free_full_mock_credit(callback.from_user.id):
        await callback.answer(t(lang, "free_mock_not_found"), show_alert=True)
        return
    await _start_test(callback, state, questions, "full_mock", lang, free_full_mock=True)
    await callback.answer()


async def _start_test(
    callback: CallbackQuery,
    state: FSMContext,
    questions: list[dict],
    subject: str,
    lang: str,
    free_mock: bool = False,
    free_full_mock: bool = False,
) -> None:
    mode = (
        "free_mock" if free_mock
        else "free_full_mock" if free_full_mock
        else "full_mock" if subject == "full_mock"
        else "practice"
    )
    session_id = await db.create_test_session(
        callback.from_user.id,
        subject,
        mode,
        len(questions),
        questions,
    )
    started_at = time.time()
    await state.set_state(TestFlow.answering)
    await state.update_data(
        session_id=session_id,
        questions=questions,
        answers=[],
        current=0,
        subject=subject,
        start_time=started_at,
        score=0,
        option_map={},
        free_mock=free_mock,
        free_full_mock=free_full_mock,
        full_mock=subject == "full_mock",
    )

    await callback.message.answer(t(lang, "test_started", count=len(questions)))
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
    if data.get("session_id") is not None:
        await db.update_test_session(
            data["session_id"],
            callback.from_user.id,
            score=score,
            total=len(data["questions"]),
            time_sec=max(0, int(time.time() - data["start_time"])),
            answers=answers,
            current_index=next_idx,
            status="in_progress",
        )

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
        subject_title = SUBJECT_TITLES.get(
            subject,
            {},
        ).get(lang, next((item["title"] for item in subjects if item["slug"] == subject), subject))
    session_id = data.get("session_id")
    if session_id is None:
        session_id = await db.create_test_session(
            callback.from_user.id,
            subject,
            (
                "free_mock" if data.get("free_mock")
                else "free_full_mock" if data.get("free_full_mock")
                else "full_mock" if data.get("full_mock")
                else "practice"
            ),
            len(data["questions"]),
            data["questions"],
        )
    if not await db.update_test_session(
        session_id,
        callback.from_user.id,
        score=score,
        total=len(data["questions"]),
        time_sec=max(0, int(time.time() - data["start_time"])),
        answers=answers,
        current_index=total,
        status="completed",
    ):
        raise RuntimeError(f"Unable to complete test session {session_id}")
    result_id = session_id
    if data.get("free_mock"):
        await db.complete_free_mock(callback.from_user.id, subject)
    elif data.get("full_mock"):
        if not data.get("free_full_mock"):
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
        t(lang, "test_result_subject", subject=escape(subject_title)),
        t(lang, "test_result_score", score=score, total=total, percent=percent),
        "",
    ]
    for index, answer in enumerate(answers):
        status = (
            t(lang, "answer_correct")
            if answer["is_correct"]
            else t(lang, "answer_wrong", answer=answer["correct_letter"])
        )
        lines.append(f"{index + 1}. {answer['selected_letter']} — {status}")
    lines.extend(["", t(lang, "result_review_prompt")])

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
            session_id=result_id,
            session_status="completed",
            can_retake=True,
        ),
    )

    await state.clear()


async def _load_test_session(session_id: int, user_id: int) -> dict | None:
    session = await db.get_result_for_user(session_id, user_id)
    if session is None or not session.get("questions"):
        return None
    return session


async def resume_test_session(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_user_language(callback.from_user.id)
    try:
        session_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer(t(lang, "result_not_found"), show_alert=True)
        return
    session = await _load_test_session(session_id, callback.from_user.id)
    if session is None or session["status"] != "in_progress":
        await callback.answer(t(lang, "session_not_resumable"), show_alert=True)
        return

    questions = session["questions"]
    current = min(session["current_index"], len(questions))
    data = {
        "session_id": session_id,
        "questions": questions,
        "answers": session["answers"],
        "current": current,
        "subject": session["subject"],
        "start_time": time.time() - session["time_sec"],
        "score": session["score"],
        "option_map": {},
        "free_mock": session["mode"] == "free_mock",
        "free_full_mock": session["mode"] == "free_full_mock",
        "full_mock": session["subject"] == "full_mock",
    }
    await state.set_state(TestFlow.answering)
    await state.set_data(data)
    if current >= len(questions):
        await _finish_test(callback, state, data, data["answers"], data["score"], lang)
    else:
        await callback.message.answer(t(lang, "session_resumed"))
        await _send_question(callback, state, questions[current], current + 1, len(questions), lang)
    await callback.answer()


async def retake_test_session(callback: CallbackQuery, state: FSMContext) -> None:
    lang = await db.get_user_language(callback.from_user.id)
    try:
        session_id = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer(t(lang, "result_not_found"), show_alert=True)
        return
    session = await _load_test_session(session_id, callback.from_user.id)
    if session is None:
        await callback.answer(t(lang, "session_not_retakable"), show_alert=True)
        return
    await state.clear()
    await _start_test(
        callback,
        state,
        session["questions"],
        session["subject"],
        lang,
        free_mock=session["mode"] == "free_mock",
        free_full_mock=session["mode"] == "free_full_mock",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("review:"))
async def review_question(callback: CallbackQuery) -> None:
    try:
        _, result_id_text, index_text = callback.data.split(":")
        result_id, index = int(result_id_text), int(index_text)
    except (ValueError, AttributeError):
        lang = await db.get_user_language(callback.from_user.id)
        await callback.answer(t(lang, "review_failed"), show_alert=True)
        return

    result = await db.get_result_for_user(result_id, callback.from_user.id)
    if result is None or index < 0 or index >= len(result["answers"]):
        lang = await db.get_user_language(callback.from_user.id)
        await callback.answer(t(lang, "result_not_found"), show_alert=True)
        return

    answer = result["answers"][index]
    answer_subject = answer.get("subject") or result["subject"]
    has_unlocked_result = await db.user_has_unlocked_result(
        callback.from_user.id,
        result_id,
        answer_subject,
    )
    if not has_unlocked_result and not await db.consume_explanation_access(callback.from_user.id):
        lang = await db.get_user_language(callback.from_user.id)
        await callback.answer(t(lang, "explanation_premium_only"), show_alert=True)
        premium_text, premium_markup = await premium_presentation(
            callback.from_user.id,
            lang,
        )
        await callback.message.answer(
            f"{t(lang, 'explanation_premium_prompt')}\n\n{premium_text}",
            reply_markup=premium_markup,
        )
        return

    lang = await db.get_user_language(callback.from_user.id)
    explanation = answer.get("explanation") or t(lang, "explanation_missing")
    options = answer.get("options", [])
    correct_index = answer.get("correct", 0)
    correct_answer = options[correct_index] if 0 <= correct_index < len(options) else "Не указан"
    steps = [line.strip() for line in explanation.splitlines() if line.strip()]
    formatted_steps = "\n".join(f"\t{escape(step)}" for step in steps)
    text = (
        f"{t(lang, 'review_title', index=index + 1)}\n\n"
        f"{escape(answer.get('question', ''))}\n\n"
        f"{t(lang, 'correct_answer', answer=escape(correct_answer))}\n\n"
        f"<pre>{formatted_steps}</pre>"
    )
    await callback.message.answer(text)
    await callback.answer()
