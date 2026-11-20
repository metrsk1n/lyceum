from __future__ import annotations

import json
import logging
import random
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

from config import settings

logger = logging.getLogger(__name__)

DB_PATH = Path(settings.db_path)


@asynccontextmanager
async def _db() -> AsyncIterator[aiosqlite.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn


async def _one(conn: aiosqlite.Connection, sql: str, params: tuple = ()) -> aiosqlite.Row | None:
    cursor = await conn.execute(sql, params)
    return await cursor.fetchone()


async def _all(conn: aiosqlite.Connection, sql: str, params: tuple = ()) -> list[aiosqlite.Row]:
    cursor = await conn.execute(sql, params)
    return await cursor.fetchall()


# ─── Runtime Settings ─────────────────────────────────────────────────────────

class RuntimeSettings:
    """In-memory cache of DB settings that override config values at runtime."""
    _data: dict[str, str] = {}

    @classmethod
    async def load(cls) -> None:
        async with _db() as conn:
            rows = await _all(conn, "SELECT key, value FROM settings")
            cls._data = {r["key"]: r["value"] for r in rows}

    @classmethod
    def get_int(cls, key: str, default: int) -> int:
        v = cls._data.get(key)
        try:
            return int(v) if v is not None else default
        except (ValueError, TypeError):
            return default

    @classmethod
    async def set_value(cls, key: str, value: str) -> None:
        async with _db() as conn:
            await conn.execute(
                "INSERT INTO settings (key, value) VALUES (?,?)"
                " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            await conn.commit()
        cls._data[key] = value

    @classmethod
    async def get_all(cls) -> dict[str, str]:
        async with _db() as conn:
            rows = await _all(conn, "SELECT key, value FROM settings")
            return {r["key"]: r["value"] for r in rows}


runtime = RuntimeSettings()


# ─── Init ─────────────────────────────────────────────────────────────────────

async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                language    TEXT NOT NULL DEFAULT 'ru',
                is_banned   INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                slug      TEXT NOT NULL UNIQUE,
                title     TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS questions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                subject     TEXT NOT NULL,
                topic       TEXT,
                language    TEXT NOT NULL DEFAULT 'ru',
                question    TEXT NOT NULL,
                options     TEXT NOT NULL,
                correct     TEXT NOT NULL,
                explanation TEXT,
                difficulty  TEXT DEFAULT 'medium',
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS results (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id),
                subject      TEXT NOT NULL,
                mode         TEXT NOT NULL DEFAULT 'training',
                score        INTEGER NOT NULL DEFAULT 0,
                total        INTEGER NOT NULL DEFAULT 0,
                time_sec     INTEGER NOT NULL DEFAULT 0,
                answers_json TEXT NOT NULL DEFAULT '[]',
                questions_json TEXT NOT NULL DEFAULT '[]',
                current_index INTEGER NOT NULL DEFAULT 0,
                status       TEXT NOT NULL DEFAULT 'completed',
                started_at   TEXT NOT NULL DEFAULT (datetime('now')),
                finished_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_question_history (
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                subject     TEXT NOT NULL,
                solved_at   TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, question_id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id),
                charge_id    TEXT NOT NULL UNIQUE,
                payload      TEXT NOT NULL,
                amount       INTEGER NOT NULL,
                product_type TEXT NOT NULL DEFAULT 'unlock',
                status       TEXT NOT NULL DEFAULT 'pending',
                expires_at   TEXT,
                created_at   TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS subscription_notifications (
                user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at       TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                sent_at          TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, expires_at, notification_type)
            );

            CREATE TABLE IF NOT EXISTS user_access (
                user_id                 INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                gift_claimed             INTEGER NOT NULL DEFAULT 0,
                free_test_credits        INTEGER NOT NULL DEFAULT 0,
                paid_test_credits        INTEGER NOT NULL DEFAULT 0,
                paid_full_test_credits  INTEGER NOT NULL DEFAULT 0,
                free_full_mock_credits  INTEGER NOT NULL DEFAULT 0,
                explanation_credits      INTEGER NOT NULL DEFAULT 0,
                subscription_discount    INTEGER NOT NULL DEFAULT 0,
                subscription_discount_code TEXT
            );

            CREATE TABLE IF NOT EXISTS user_free_mocks (
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                subject     TEXT NOT NULL,
                started_at  TEXT NOT NULL DEFAULT (datetime('now')),
                completed_at TEXT,
                PRIMARY KEY (user_id, subject)
            );

            CREATE TABLE IF NOT EXISTS daily_test_usage (
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                usage_date   TEXT NOT NULL,
                tests_used   INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, usage_date)
            );

            CREATE TABLE IF NOT EXISTS promo_codes (
                code          TEXT PRIMARY KEY,
                reward_type   TEXT NOT NULL,
                value         INTEGER NOT NULL,
                max_uses      INTEGER NOT NULL DEFAULT 0,
                uses_count    INTEGER NOT NULL DEFAULT 0,
                expires_at    TEXT,
                created_by    INTEGER NOT NULL,
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                is_active     INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS promo_redemptions (
                code         TEXT NOT NULL REFERENCES promo_codes(code) ON DELETE CASCADE,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                redeemed_at  TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (code, user_id)
            );

            CREATE TABLE IF NOT EXISTS donations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                charge_id  TEXT NOT NULL UNIQUE,
                amount     INTEGER NOT NULL,
                status     TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        columns_cursor = await conn.execute("PRAGMA table_info(questions)")
        columns = await columns_cursor.fetchall()
        if not any(row[1] == "topic" for row in columns):
            await conn.execute("ALTER TABLE questions ADD COLUMN topic TEXT")

        user_columns_cursor = await conn.execute("PRAGMA table_info(users)")
        user_columns = {row[1] for row in await user_columns_cursor.fetchall()}
        if "is_banned" not in user_columns:
            await conn.execute(
                "ALTER TABLE users ADD COLUMN is_banned INTEGER NOT NULL DEFAULT 0"
            )

        payment_columns_cursor = await conn.execute("PRAGMA table_info(payments)")
        payment_columns = {row[1] for row in await payment_columns_cursor.fetchall()}
        if "product_type" not in payment_columns:
            await conn.execute("ALTER TABLE payments ADD COLUMN product_type TEXT NOT NULL DEFAULT 'unlock'")
        if "status" not in payment_columns:
            await conn.execute("ALTER TABLE payments ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
        if "expires_at" not in payment_columns:
            await conn.execute("ALTER TABLE payments ADD COLUMN expires_at TEXT")
        access_columns_cursor = await conn.execute("PRAGMA table_info(user_access)")
        access_columns = {row[1] for row in await access_columns_cursor.fetchall()}
        if "paid_full_test_credits" not in access_columns:
            await conn.execute(
                "ALTER TABLE user_access ADD COLUMN paid_full_test_credits INTEGER NOT NULL DEFAULT 0"
            )
        if "free_full_mock_credits" not in access_columns:
            await conn.execute(
                "ALTER TABLE user_access ADD COLUMN free_full_mock_credits INTEGER NOT NULL DEFAULT 0"
            )
        result_columns_cursor = await conn.execute("PRAGMA table_info(results)")
        result_columns = {row[1] for row in await result_columns_cursor.fetchall()}
        if "questions_json" not in result_columns:
            await conn.execute(
                "ALTER TABLE results ADD COLUMN questions_json TEXT NOT NULL DEFAULT '[]'"
            )
        if "current_index" not in result_columns:
            await conn.execute(
                "ALTER TABLE results ADD COLUMN current_index INTEGER NOT NULL DEFAULT 0"
            )
        if "status" not in result_columns:
            await conn.execute(
                "ALTER TABLE results ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'"
            )
        if "started_at" not in result_columns:
            await conn.execute(
                "ALTER TABLE results ADD COLUMN started_at TEXT NOT NULL DEFAULT ''"
            )
            await conn.execute(
                "UPDATE results SET started_at=finished_at WHERE started_at=''"
            )
        await conn.commit()

        # Seed the built-in subjects without removing administrator-created ones.
        canonical = [
            ("mathematics", "Математика"),
            ("english",     "Английский"),
            ("iq",          "IQ"),
        ]
        # Upsert canonical subjects
        for slug, title in canonical:
            await conn.execute(
                "INSERT INTO subjects (slug, title, is_active) VALUES (?,?,1)"
                " ON CONFLICT(slug) DO UPDATE SET title=excluded.title, is_active=1",
                (slug, title),
            )
        await conn.execute("UPDATE subjects SET is_active=0 WHERE slug IN ('physics','russian')")
        migration = await _one(conn, "SELECT value FROM settings WHERE key='pricing_v2_migrated'")
        if migration is None:
            await conn.execute(
                "UPDATE settings SET value='25' WHERE key='answer_unlock_price' AND value IN ('50','75')"
            )
            await conn.execute(
                "INSERT INTO settings (key,value) VALUES ('pricing_v2_migrated','1')"
            )
        questions_path = Path(__file__).parent / "data" / "questions.json"
        if questions_path.is_file():
            question_records = json.loads(questions_path.read_text(encoding="utf-8"))
            for item in question_records:
                existing = await _one(
                    conn,
                    "SELECT 1 FROM questions WHERE subject=? AND language=? AND question=? LIMIT 1",
                    (item["subject"], item["language"], item["question_text"]),
                )
                if existing is None:
                    await conn.execute(
                        "INSERT INTO questions "
                        "(subject,topic,language,question,options,correct,explanation,difficulty) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (
                            item["subject"],
                            item.get("topic"),
                            item["language"],
                            item["question_text"],
                            json.dumps(item["options"], ensure_ascii=False),
                            json.dumps([item["correct_option_index"]]),
                            item["explanation"],
                            item["difficulty"],
                        ),
                    )
        else:
            logger.warning(
                "Optional question seed file is missing: %s; skipping seed import",
                questions_path,
            )
        await conn.commit()
    logger.info("Database initialized at %s", DB_PATH)


# ─── Users ───────────────────────────────────────────────────────────────────

async def get_or_create_user(user_id: int, first_name: str | None, username: str | None) -> dict:
    async with _db() as conn:
        row = await _one(conn, "SELECT * FROM users WHERE id=?", (user_id,))
        if row is None:
            await conn.execute(
                "INSERT INTO users (id, username, first_name, language) VALUES (?,?,?,?)",
                (user_id, username, first_name, settings.default_language),
            )
            await conn.commit()
            row = await _one(conn, "SELECT * FROM users WHERE id=?", (user_id,))
        else:
            updates: dict[str, Any] = {}
            if username and row["username"] != username:
                updates["username"] = username
            if first_name and row["first_name"] != first_name:
                updates["first_name"] = first_name
            if updates:
                cols = ", ".join(f"{k}=?" for k in updates)
                await conn.execute(f"UPDATE users SET {cols} WHERE id=?", (*updates.values(), user_id))
                await conn.commit()
                row = await _one(conn, "SELECT * FROM users WHERE id=?", (user_id,))
        return dict(row)


async def get_user_language(user_id: int) -> str:
    async with _db() as conn:
        row = await _one(conn, "SELECT language FROM users WHERE id=?", (user_id,))
        return row["language"] if row else settings.default_language


async def set_user_language(user_id: int, language: str) -> None:
    async with _db() as conn:
        await conn.execute("UPDATE users SET language=? WHERE id=?", (language, user_id))
        await conn.commit()


async def count_users() -> int:
    async with _db() as conn:
        row = await _one(conn, "SELECT COUNT(*) FROM users")
        return row[0] if row else 0


async def get_all_user_ids() -> list[int]:
    async with _db() as conn:
        rows = await _all(conn, "SELECT id FROM users WHERE is_banned=0 ORDER BY id")
        return [row["id"] for row in rows]


async def is_user_banned(user_id: int) -> bool:
    async with _db() as conn:
        row = await _one(conn, "SELECT is_banned FROM users WHERE id=?", (user_id,))
        return bool(row["is_banned"]) if row else False


async def set_user_banned(user_id: int, is_banned: bool) -> bool:
    async with _db() as conn:
        cursor = await conn.execute(
            "UPDATE users SET is_banned=? WHERE id=?",
            (int(is_banned), user_id),
        )
        await conn.commit()
        return cursor.rowcount == 1


async def count_new_today() -> int:
    async with _db() as conn:
        row = await _one(conn, "SELECT COUNT(*) FROM users WHERE date(created_at)=date('now')")
        return row[0] if row else 0


async def count_active_today() -> int:
    async with _db() as conn:
        row = await _one(conn, "SELECT COUNT(DISTINCT user_id) FROM results WHERE date(finished_at)=date('now')")
        return row[0] if row else 0


async def list_users(limit: int = 30, offset: int = 0) -> list[dict]:
    async with _db() as conn:
        rows = await _all(conn, "SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [dict(r) for r in rows]


async def get_user_admin_info(user_id: int) -> dict | None:
    async with _db() as conn:
        u = await _one(conn, "SELECT * FROM users WHERE id=?", (user_id,))
        if not u:
            return None
        tr = await _one(
            conn,
            "SELECT COUNT(*), COALESCE(AVG(CAST(score AS REAL)/total*100),0) "
            "FROM results WHERE user_id=? AND total>0 AND status='completed'",
            (user_id,),
        )
        pr = await _one(conn, "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payments WHERE user_id=? AND status='paid'", (user_id,))
        result = dict(u)
        result["test_count"] = tr[0] if tr else 0
        result["avg_score"] = round(tr[1] or 0, 1) if tr else 0
        result["payment_count"] = pr[0] if pr else 0
        result["stars_spent"] = pr[1] if pr else 0
        return result


# ─── Subjects ─────────────────────────────────────────────────────────────────

async def get_subjects() -> list[dict]:
    async with _db() as conn:
        rows = await _all(conn, "SELECT * FROM subjects WHERE is_active=1 ORDER BY id")
        return [dict(r) for r in rows]


async def all_subjects() -> list[dict]:
    async with _db() as conn:
        rows = await _all(conn, "SELECT * FROM subjects ORDER BY id")
        return [dict(r) for r in rows]


async def add_subject(slug: str, title: str) -> None:
    async with _db() as conn:
        await conn.execute("INSERT OR IGNORE INTO subjects (slug, title) VALUES (?,?)", (slug, title))
        await conn.commit()


async def update_subject_title(subject_id: int, title: str) -> None:
    async with _db() as conn:
        await conn.execute("UPDATE subjects SET title=? WHERE id=?", (title, subject_id))
        await conn.commit()


async def toggle_subject(subject_id: int) -> None:
    async with _db() as conn:
        await conn.execute(
            "UPDATE subjects SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?",
            (subject_id,),
        )
        await conn.commit()


async def delete_subject_safe(subject_id: int) -> tuple[bool, int]:
    """Delete subject if it has no active questions. Returns (deleted, question_count)."""
    async with _db() as conn:
        subj = await _one(conn, "SELECT slug FROM subjects WHERE id=?", (subject_id,))
        if not subj:
            return False, 0
        cnt_row = await _one(conn, "SELECT COUNT(*) FROM questions WHERE subject=? AND is_active=1", (subj["slug"],))
        cnt = cnt_row[0] if cnt_row else 0
        if cnt > 0:
            return False, cnt
        await conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
        await conn.commit()
        return True, 0


# ─── Questions ────────────────────────────────────────────────────────────────

def _parse_question(row: aiosqlite.Row) -> dict:
    q = dict(row)
    q["options"] = json.loads(q["options"])
    q["correct"] = json.loads(q["correct"])
    return q


async def get_random_questions(subject: str, language: str, amount: int) -> list[dict]:
    async with _db() as conn:
        rows = await _all(conn, "SELECT * FROM questions WHERE subject=? AND language=? AND is_active=1", (subject, language))
        pool = [_parse_question(r) for r in rows]
        if not pool and language != "ru":
            rows = await _all(conn, "SELECT * FROM questions WHERE subject=? AND is_active=1", (subject,))
            pool = [_parse_question(r) for r in rows]
        return random.sample(pool, min(amount, len(pool)))


async def get_unresolved_questions(user_id: int, subject: str, language: str, amount: int = 20) -> list[dict]:
    async with _db() as conn:
        subject_values = [subject]
        subject_row = await _one(conn, "SELECT title FROM subjects WHERE slug=?", (subject,))
        if subject_row and subject_row["title"] not in subject_values:
            subject_values.append(subject_row["title"])
        subject_placeholders = ",".join("?" for _ in subject_values)
        subject_filter = f"subject IN ({subject_placeholders})"

        rows = await _all(
            conn,
            f"SELECT * FROM questions WHERE {subject_filter} AND language=? AND is_active=1 "
            "AND id NOT IN (SELECT question_id FROM user_question_history WHERE user_id=? AND subject=?)",
            (*subject_values, language, user_id, subject),
        )
        if not rows:
            rows = await _all(
                conn,
                f"SELECT * FROM questions WHERE {subject_filter} AND is_active=1 "
                "AND id NOT IN (SELECT question_id FROM user_question_history WHERE user_id=? AND subject=?)",
                (*subject_values, user_id, subject),
            )

        if not rows:
            await conn.execute(
                "DELETE FROM user_question_history WHERE user_id=? AND subject=?",
                (user_id, subject),
            )
            rows = await _all(
                conn,
                f"SELECT * FROM questions WHERE {subject_filter} AND language=? AND is_active=1",
                (*subject_values, language),
            )
            if not rows:
                rows = await _all(
                    conn,
                    f"SELECT * FROM questions WHERE {subject_filter} AND is_active=1",
                    tuple(subject_values),
                )
            await conn.commit()

        pool = [_parse_question(row) for row in rows]
        return random.sample(pool, min(amount, len(pool)))


async def record_solved_questions(user_id: int, subject: str, question_ids: list[int]) -> None:
    if not question_ids:
        return
    async with _db() as conn:
        await conn.executemany(
            "INSERT OR IGNORE INTO user_question_history (user_id, question_id, subject) VALUES (?,?,?)",
            [(user_id, question_id, subject) for question_id in question_ids],
        )
        await conn.commit()


async def get_question_by_id(question_id: int) -> dict | None:
    async with _db() as conn:
        row = await _one(conn, "SELECT * FROM questions WHERE id=?", (question_id,))
        return _parse_question(row) if row else None


async def add_question(
    subject: str, language: str, question: str,
    options: list[str], correct: list[int],
    explanation: str | None, difficulty: str = "medium",
) -> int:
    async with _db() as conn:
        cursor = await conn.execute(
            "INSERT INTO questions (subject,language,question,options,correct,explanation,difficulty) VALUES (?,?,?,?,?,?,?)",
            (subject, language, question, json.dumps(options, ensure_ascii=False), json.dumps(correct), explanation, difficulty),
        )
        await conn.commit()
        return cursor.lastrowid


async def update_question(question_id: int, **kwargs: Any) -> None:
    if "options" in kwargs and isinstance(kwargs["options"], list):
        kwargs["options"] = json.dumps(kwargs["options"], ensure_ascii=False)
    if "correct" in kwargs and isinstance(kwargs["correct"], list):
        kwargs["correct"] = json.dumps(kwargs["correct"])
    cols = ", ".join(f"{k}=?" for k in kwargs)
    async with _db() as conn:
        await conn.execute(f"UPDATE questions SET {cols} WHERE id=?", (*kwargs.values(), question_id))
        await conn.commit()


async def delete_question(question_id: int) -> None:
    async with _db() as conn:
        await conn.execute("DELETE FROM questions WHERE id=?", (question_id,))
        await conn.commit()


async def count_questions(subject: str | None = None) -> int:
    async with _db() as conn:
        if subject:
            row = await _one(conn, "SELECT COUNT(*) FROM questions WHERE subject=? AND is_active=1", (subject,))
        else:
            row = await _one(conn, "SELECT COUNT(*) FROM questions WHERE is_active=1")
        return row[0] if row else 0


async def list_questions(subject: str | None = None, limit: int = 10, offset: int = 0) -> list[dict]:
    async with _db() as conn:
        if subject:
            rows = await _all(conn, "SELECT * FROM questions WHERE subject=? AND is_active=1 ORDER BY id DESC LIMIT ? OFFSET ?", (subject, limit, offset))
        else:
            rows = await _all(conn, "SELECT * FROM questions WHERE is_active=1 ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
        return [_parse_question(r) for r in rows]


async def search_questions_db(query: str, limit: int = 10, offset: int = 0) -> list[dict]:
    try:
        qid = int(query)
        async with _db() as conn:
            row = await _one(conn, "SELECT * FROM questions WHERE id=?", (qid,))
            if row:
                return [_parse_question(row)]
    except ValueError:
        pass
    like = f"%{query}%"
    async with _db() as conn:
        rows = await _all(conn, "SELECT * FROM questions WHERE is_active=1 AND (question LIKE ? OR subject LIKE ?) ORDER BY id DESC LIMIT ? OFFSET ?", (like, like, limit, offset))
        return [_parse_question(r) for r in rows]


async def count_search_questions(query: str) -> int:
    try:
        qid = int(query)
        async with _db() as conn:
            row = await _one(conn, "SELECT COUNT(*) FROM questions WHERE id=?", (qid,))
            if row and row[0] > 0:
                return row[0]
    except ValueError:
        pass
    like = f"%{query}%"
    async with _db() as conn:
        row = await _one(conn, "SELECT COUNT(*) FROM questions WHERE is_active=1 AND (question LIKE ? OR subject LIKE ?)", (like, like))
        return row[0] if row else 0


async def import_questions(questions_list: list[dict]) -> int:
    async with _db() as conn:
        subject_rows = await _all(conn, "SELECT slug, title FROM subjects")
        subject_aliases = {
            name.strip().casefold(): row["slug"]
            for row in subject_rows
            for name in (row["slug"], row["title"])
        }
        normalized_questions = []
        for item in questions_list:
            value = dict(item)
            raw_subject = str(value.get("subject", value.get("subject_name", ""))).strip()
            subject = subject_aliases.get(raw_subject.casefold())
            if subject is None:
                raise ValueError(f"Неизвестный предмет: {raw_subject or 'пустое значение'}")
            language = str(value.get("language", value.get("lang", settings.default_language))).strip() or settings.default_language
            question_text = str(value.get("question_text", value.get("question", ""))).strip()
            if not question_text:
                raise ValueError("Текст вопроса не может быть пустым")
            topic = value.get("topic")
            if topic is not None:
                topic = str(topic).strip() or None
            options = value.get("options", [])
            if isinstance(options, str):
                try:
                    options = json.loads(options)
                except json.JSONDecodeError:
                    options = [part.strip() for part in options.split(";") if part.strip()]
            if not isinstance(options, list):
                raise ValueError("Варианты ответа должны быть списком")
            options = [str(option).strip() for option in options if str(option).strip()]
            if len(options) < 2:
                raise ValueError("У вопроса должно быть не менее двух вариантов ответа")

            correct = value.get("correct")
            if "correct_option_index" in value and correct is None:
                correct = [value["correct_option_index"]]
            if isinstance(correct, int):
                correct = [correct]
            elif isinstance(correct, str):
                correct = [int(correct)]
            if not isinstance(correct, list) or len(correct) != 1:
                raise ValueError("Для вопроса с одним выбираемым ответом нужен ровно один правильный вариант")
            correct = [int(correct[0])]
            if any(index < 0 or index >= len(options) for index in correct):
                raise ValueError("Индекс правильного ответа не соответствует вариантам")

            explanation = value.get("explanation")
            if explanation is not None:
                explanation = str(explanation).strip() or None
            difficulty = str(value.get("difficulty", "medium")).strip() or "medium"
            normalized_questions.append(
                (subject, topic, language, question_text, options, correct, explanation, difficulty)
            )

        for subject, topic, language, question_text, options, correct, explanation, difficulty in normalized_questions:
            await conn.execute(
                "INSERT INTO questions (subject, topic, language, question, options, correct, explanation, difficulty) VALUES (?,?,?,?,?,?,?,?)",
                (
                    subject,
                    topic,
                    language,
                    question_text,
                    json.dumps(options, ensure_ascii=False),
                    json.dumps(correct),
                    explanation,
                    difficulty,
                ),
            )
        await conn.commit()
    return len(normalized_questions)


async def get_existing_question_texts(subject: str, language: str) -> set[str]:
    async with _db() as conn:
        rows = await _all(conn, "SELECT question FROM questions WHERE subject=? AND language=?", (subject, language))
        return {r["question"].strip().lower() for r in rows}


# ─── Results ─────────────────────────────────────────────────────────────────

async def save_result(
    user_id: int, subject: str, mode: str,
    score: int, total: int, time_sec: int, answers: list[dict],
) -> int:
    async with _db() as conn:
        cursor = await conn.execute(
            "INSERT INTO results (user_id,subject,mode,score,total,time_sec,answers_json) VALUES (?,?,?,?,?,?,?)",
            (user_id, subject, mode, score, total, time_sec, json.dumps(answers, ensure_ascii=False)),
        )
        await conn.commit()
        return cursor.lastrowid


async def create_test_session(
    user_id: int,
    subject: str,
    mode: str,
    total: int,
    questions: list[dict],
) -> int:
    async with _db() as conn:
        cursor = await conn.execute(
            "INSERT INTO results "
            "(user_id,subject,mode,total,answers_json,questions_json,current_index,status) "
            "VALUES (?,?,?,?,?,?,0,'in_progress')",
            (
                user_id,
                subject,
                mode,
                total,
                "[]",
                json.dumps(questions, ensure_ascii=False),
            ),
        )
        await conn.commit()
        return cursor.lastrowid


async def update_test_session(
    session_id: int,
    user_id: int,
    *,
    score: int,
    total: int,
    time_sec: int,
    answers: list[dict],
    current_index: int,
    status: str,
) -> bool:
    if status not in {"in_progress", "completed"}:
        raise ValueError(f"Invalid test session status: {status}")
    async with _db() as conn:
        cursor = await conn.execute(
            "UPDATE results SET score=?,total=?,time_sec=?,answers_json=?,"
            "current_index=?,status=?,finished_at=CASE WHEN ?='completed' "
            "THEN datetime('now') ELSE finished_at END "
            "WHERE id=? AND user_id=?",
            (
                score,
                total,
                time_sec,
                json.dumps(answers, ensure_ascii=False),
                current_index,
                status,
                status,
                session_id,
                user_id,
            ),
        )
        await conn.commit()
        return cursor.rowcount == 1


def _questions_from_session_answers(answers: list[dict], subject: str) -> list[dict]:
    questions = []
    for answer in answers:
        question_id = answer.get("qid")
        correct = answer.get("correct")
        options = answer.get("options")
        if (
            not isinstance(question_id, int)
            or not isinstance(correct, int)
            or not isinstance(options, list)
            or not options
        ):
            return []
        questions.append({
            "id": question_id,
            "subject": answer.get("subject") or subject,
            "question": answer.get("question", ""),
            "options": options,
            "correct": [correct],
            "explanation": answer.get("explanation") or "",
        })
    return questions


async def get_result_for_user(result_id: int, user_id: int) -> dict | None:
    async with _db() as conn:
        row = await _one(conn, "SELECT * FROM results WHERE id=? AND user_id=?", (result_id, user_id))
        if not row:
            return None
        result = dict(row)
        result["answers"] = json.loads(result["answers_json"])
        result["questions"] = json.loads(result["questions_json"])
        if not result["questions"] and result["answers"]:
            result["questions"] = _questions_from_session_answers(
                result["answers"],
                result["subject"],
            )
        return result


async def get_user_results(user_id: int, limit: int = 10) -> list[dict]:
    async with _db() as conn:
        rows = await _all(
            conn,
            "SELECT * FROM results WHERE user_id=? "
            "ORDER BY CASE WHEN status='in_progress' THEN 0 ELSE 1 END,"
            "started_at DESC,id DESC LIMIT ?",
            (user_id, limit),
        )
        result = []
        for r in rows:
            item = dict(r)
            item["answers"] = json.loads(item["answers_json"])
            item["questions"] = json.loads(item["questions_json"])
            if not item["questions"] and item["answers"]:
                item["questions"] = _questions_from_session_answers(
                    item["answers"],
                    item["subject"],
                )
            result.append(item)
        return result


async def get_user_stats(user_id: int) -> dict:
    async with _db() as conn:
        row = await _one(
            conn,
            "SELECT COUNT(*) as t, SUM(score) as c, SUM(total) as q "
            "FROM results WHERE user_id=? AND status='completed'",
            (user_id,),
        )
        if not row or not row["t"]:
            return {"total_tests": 0, "correct": 0, "total_q": 0, "accuracy": 0.0, "best": 0.0}
        correct = row["c"] or 0
        total_q = row["q"] or 0
        accuracy = round(correct / total_q * 100, 1) if total_q else 0.0
        best_row = await _one(
            conn,
            "SELECT MAX(CAST(score AS REAL)/total*100) as b "
            "FROM results WHERE user_id=? AND status='completed' AND total>0",
            (user_id,),
        )
        best = round(best_row["b"] or 0.0, 1) if best_row else 0.0
        return {"total_tests": row["t"], "correct": correct, "total_q": total_q, "accuracy": accuracy, "best": best}


async def _ensure_user_access(conn: aiosqlite.Connection, user_id: int) -> None:
    await conn.execute("INSERT OR IGNORE INTO user_access (user_id) VALUES (?)", (user_id,))


async def claim_gift_tests(user_id: int, amount: int = 3) -> bool:
    async with _db() as conn:
        await _ensure_user_access(conn, user_id)
        cursor = await conn.execute(
            "UPDATE user_access SET gift_claimed=1, free_test_credits=free_test_credits+? "
            "WHERE user_id=? AND gift_claimed=0",
            (amount, user_id),
        )
        await conn.commit()
        return cursor.rowcount == 1


async def claim_free_mock(user_id: int, subject: str) -> bool:
    async with _db() as conn:
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO user_free_mocks (user_id,subject) VALUES (?,?)",
            (user_id, subject),
        )
        await conn.commit()
        return cursor.rowcount == 1


async def complete_free_mock(user_id: int, subject: str) -> None:
    async with _db() as conn:
        await conn.execute(
            "UPDATE user_free_mocks SET completed_at=datetime('now') WHERE user_id=? AND subject=?",
            (user_id, subject),
        )
        await conn.commit()


async def get_free_mock_status(user_id: int) -> set[str]:
    async with _db() as conn:
        rows = await _all(conn, "SELECT subject FROM user_free_mocks WHERE user_id=?", (user_id,))
        return {row["subject"] for row in rows}


async def get_user_access(user_id: int) -> dict:
    async with _db() as conn:
        await _ensure_user_access(conn, user_id)
        await conn.commit()
        row = await _one(conn, "SELECT * FROM user_access WHERE user_id=?", (user_id,))
        usage = await _one(
            conn,
            "SELECT tests_used FROM daily_test_usage WHERE user_id=? AND usage_date=?",
            (user_id, date.today().isoformat()),
        )
        result = dict(row)
        result["daily_tests_used"] = usage["tests_used"] if usage else 0
        return result


async def consume_free_full_mock_credit(user_id: int) -> bool:
    async with _db() as conn:
        await _ensure_user_access(conn, user_id)
        cursor = await conn.execute(
            "UPDATE user_access SET free_full_mock_credits=free_full_mock_credits-1 "
            "WHERE user_id=? AND free_full_mock_credits>0",
            (user_id,),
        )
        await conn.commit()
        return cursor.rowcount == 1


async def consume_test_access(user_id: int, subscriber_daily_limit: int = 5) -> str:
    if user_id in settings.admin_ids:
        return "subscriber"

    if await user_has_active_subscription(user_id):
        async with _db() as conn:
            usage_date = date.today().isoformat()
            await conn.execute(
                "INSERT OR IGNORE INTO daily_test_usage (user_id, usage_date, tests_used) VALUES (?,?,0)",
                (user_id, usage_date),
            )
            cursor = await conn.execute(
                "UPDATE daily_test_usage SET tests_used=tests_used+1 "
                "WHERE user_id=? AND usage_date=? AND tests_used<?",
                (user_id, usage_date, subscriber_daily_limit),
            )
            await conn.commit()
            return "subscriber" if cursor.rowcount else "daily_limit"

    async with _db() as conn:
        await _ensure_user_access(conn, user_id)
        for column, access_type in (("free_test_credits", "gift"), ("paid_test_credits", "paid")):
            cursor = await conn.execute(
                f"UPDATE user_access SET {column}={column}-1 WHERE user_id=? AND {column}>0",
                (user_id,),
            )
            if cursor.rowcount:
                await conn.commit()
                return access_type
        await conn.commit()
        return "payment_required"


async def consume_full_test_access(user_id: int, subscriber_daily_limit: int = 5) -> str:
    if user_id in settings.admin_ids:
        return "subscriber"

    async with _db() as conn:
        await _ensure_user_access(conn, user_id)
        cursor = await conn.execute(
            "UPDATE user_access SET paid_full_test_credits=paid_full_test_credits-1 "
            "WHERE user_id=? AND paid_full_test_credits>0",
            (user_id,),
        )
        if cursor.rowcount:
            await conn.commit()
            return "paid"
        await conn.commit()

    if await user_has_active_subscription(user_id):
        async with _db() as conn:
            usage_date = date.today().isoformat()
            await conn.execute(
                "INSERT OR IGNORE INTO daily_test_usage (user_id, usage_date, tests_used) VALUES (?,?,0)",
                (user_id, usage_date),
            )
            cursor = await conn.execute(
                "UPDATE daily_test_usage SET tests_used=tests_used+1 "
                "WHERE user_id=? AND usage_date=? AND tests_used<?",
                (user_id, usage_date, subscriber_daily_limit),
            )
            await conn.commit()
            return "subscriber" if cursor.rowcount else "daily_limit"
    return "payment_required"


async def record_test_purchase(user_id: int, charge_id: str, payload: str, amount: int) -> bool:
    async with _db() as conn:
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO payments "
            "(user_id,charge_id,payload,amount,product_type,status) VALUES (?,?,?,?,'test','paid')",
            (user_id, charge_id, payload, amount),
        )
        if cursor.rowcount:
            await _ensure_user_access(conn, user_id)
            await conn.execute(
                "UPDATE user_access SET paid_test_credits=paid_test_credits+1 WHERE user_id=?",
                (user_id,),
            )
        await conn.commit()
        return cursor.rowcount == 1


async def record_full_test_purchase(user_id: int, charge_id: str, payload: str, amount: int) -> bool:
    async with _db() as conn:
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO payments "
            "(user_id,charge_id,payload,amount,product_type,status) "
            "VALUES (?,?,?,?,'full_test','paid')",
            (user_id, charge_id, payload, amount),
        )
        if cursor.rowcount:
            await _ensure_user_access(conn, user_id)
            await conn.execute(
                "UPDATE user_access SET paid_full_test_credits=paid_full_test_credits+1 WHERE user_id=?",
                (user_id,),
            )
        await conn.commit()
        return cursor.rowcount == 1


async def consume_explanation_access(user_id: int) -> bool:
    if await user_has_active_subscription(user_id):
        return True
    async with _db() as conn:
        await _ensure_user_access(conn, user_id)
        cursor = await conn.execute(
            "UPDATE user_access SET explanation_credits=explanation_credits-1 "
            "WHERE user_id=? AND explanation_credits>0",
            (user_id,),
        )
        await conn.commit()
        return cursor.rowcount == 1


async def create_promo_code(
    code: str, reward_type: str, value: int, max_uses: int, expires_at: str | None, created_by: int,
) -> None:
    if reward_type not in {"tests", "full_tests", "free_full_mocks", "explanations", "discount"}:
        raise ValueError(f"Unsupported promo reward type: {reward_type}")
    if value < 1 or max_uses < 0 or (reward_type == "discount" and value > 100):
        raise ValueError("Invalid promo value or usage limit")
    async with _db() as conn:
        await conn.execute(
            "INSERT INTO promo_codes (code,reward_type,value,max_uses,expires_at,created_by) VALUES (?,?,?,?,?,?)",
            (code.upper(), reward_type, value, max_uses, expires_at, created_by),
        )
        await conn.commit()


async def redeem_promo_code(user_id: int, code: str) -> dict | None:
    normalized_code = code.strip().upper()
    async with _db() as conn:
        await conn.execute("BEGIN IMMEDIATE")
        await _ensure_user_access(conn, user_id)
        promo = await _one(conn, "SELECT * FROM promo_codes WHERE code=? AND is_active=1", (normalized_code,))
        if not promo:
            return None
        if promo["expires_at"] and datetime.fromisoformat(promo["expires_at"]) < datetime.now():
            return {"error": "expired"}
        if await _one(conn, "SELECT 1 FROM promo_redemptions WHERE code=? AND user_id=?", (normalized_code, user_id)):
            return {"error": "used"}
        if promo["max_uses"] and promo["uses_count"] >= promo["max_uses"]:
            return {"error": "limit"}

        if promo["reward_type"] == "tests":
            await conn.execute(
                "UPDATE user_access SET free_test_credits=free_test_credits+? WHERE user_id=?",
                (promo["value"], user_id),
            )
        elif promo["reward_type"] == "full_tests":
            await conn.execute(
                "UPDATE user_access SET paid_full_test_credits=paid_full_test_credits+? WHERE user_id=?",
                (promo["value"], user_id),
            )
        elif promo["reward_type"] == "free_full_mocks":
            await conn.execute(
                "UPDATE user_access SET free_full_mock_credits=free_full_mock_credits+? WHERE user_id=?",
                (promo["value"], user_id),
            )
        elif promo["reward_type"] == "explanations":
            await conn.execute(
                "UPDATE user_access SET explanation_credits=explanation_credits+? WHERE user_id=?",
                (promo["value"], user_id),
            )
        elif promo["reward_type"] == "discount":
            if not 1 <= promo["value"] <= 100:
                return {"error": "invalid"}
            access = await _one(conn, "SELECT subscription_discount FROM user_access WHERE user_id=?", (user_id,))
            if access["subscription_discount"]:
                return {"error": "discount_pending"}
            await conn.execute(
                "UPDATE user_access SET subscription_discount=?, subscription_discount_code=? WHERE user_id=?",
                (promo["value"], normalized_code, user_id),
            )
        else:
            return {"error": "invalid"}

        await conn.execute(
            "INSERT INTO promo_redemptions (code,user_id) VALUES (?,?)",
            (normalized_code, user_id),
        )
        await conn.execute("UPDATE promo_codes SET uses_count=uses_count+1 WHERE code=?", (normalized_code,))
        await conn.commit()
        return {"reward_type": promo["reward_type"], "value": promo["value"]}


async def toggle_promo_code(code: str) -> bool:
    async with _db() as conn:
        cursor = await conn.execute(
            "UPDATE promo_codes SET is_active=CASE WHEN is_active=1 THEN 0 ELSE 1 END "
            "WHERE code=?",
            (code.upper(),),
        )
        await conn.commit()
        return cursor.rowcount == 1


async def get_user_subscription_discount(user_id: int) -> tuple[int, str] | None:
    async with _db() as conn:
        row = await _one(
            conn,
            "SELECT subscription_discount, subscription_discount_code FROM user_access WHERE user_id=?",
            (user_id,),
        )
        if not row or not row["subscription_discount"]:
            return None
        return row["subscription_discount"], row["subscription_discount_code"]


async def consume_user_subscription_discount(user_id: int, code: str) -> bool:
    async with _db() as conn:
        cursor = await conn.execute(
            "UPDATE user_access SET subscription_discount=0, subscription_discount_code=NULL "
            "WHERE user_id=? AND subscription_discount_code=? AND subscription_discount>0",
            (user_id, code),
        )
        await conn.commit()
        return cursor.rowcount == 1


async def grant_free_subscription_from_discount(
    user_id: int,
    plan: str,
    days: int,
    code: str | None = None,
) -> datetime | None:
    if plan not in {"week", "month", "quarter"} or days not in {7, 30, 90}:
        raise ValueError("Invalid free subscription plan")
    now = datetime.now()
    async with _db() as conn:
        await conn.execute("BEGIN IMMEDIATE")
        access = await _one(
            conn,
            "SELECT subscription_discount,subscription_discount_code "
            "FROM user_access WHERE user_id=?",
            (user_id,),
        )
        if code is None:
            if RuntimeSettings.get_int("premium_discount_percent", 0) != 100:
                return None
        elif (
            access is None
            or access["subscription_discount"] != 100
            or access["subscription_discount_code"] != code
        ):
            return None

        rows = await _all(
            conn,
            "SELECT expires_at FROM payments WHERE user_id=? AND status='paid' "
            "AND product_type='subscription' AND expires_at IS NOT NULL",
            (user_id,),
        )
        expirations = []
        for row in rows:
            try:
                expiry = datetime.fromisoformat(row["expires_at"])
            except ValueError:
                continue
            if expiry > now:
                expirations.append(expiry)
        starts_at = max(expirations, default=now)
        expires_at = starts_at + timedelta(days=days)
        cursor = await conn.execute(
            "INSERT INTO payments "
            "(user_id,charge_id,payload,amount,product_type,status,expires_at) "
            "VALUES (?,?,?,0,'subscription','paid',?)",
            (
                user_id,
                f"promo-free:{uuid.uuid4()}",
                f"sub:{plan}:{user_id}:{code or 'admin-discount'}",
                expires_at.isoformat(timespec="seconds"),
            ),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("Unable to record free subscription")
        if code is not None:
            cleared = await conn.execute(
                "UPDATE user_access SET subscription_discount=0,subscription_discount_code=NULL "
                "WHERE user_id=? AND subscription_discount=100 AND subscription_discount_code=?",
                (user_id, code),
            )
            if cleared.rowcount != 1:
                raise RuntimeError("Unable to consume 100% subscription discount")
        await conn.commit()
        return expires_at


async def list_promo_codes(limit: int = 20, offset: int = 0) -> list[dict]:
    async with _db() as conn:
        rows = await _all(
            conn,
            "SELECT code,reward_type,value,max_uses,uses_count,expires_at,is_active "
            "FROM promo_codes ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(row) for row in rows]


async def count_promo_codes() -> int:
    async with _db() as conn:
        row = await _one(conn, "SELECT COUNT(*) FROM promo_codes")
        return row[0] if row else 0


async def get_promo_redemptions(code: str, limit: int = 20, offset: int = 0) -> tuple[int, list[dict]]:
    async with _db() as conn:
        count_row = await _one(
            conn,
            "SELECT COUNT(*) FROM promo_redemptions WHERE code=?",
            (code.upper(),),
        )
        rows = await _all(
            conn,
            "SELECT u.id AS user_id, u.username, u.first_name, r.redeemed_at "
            "FROM promo_redemptions r JOIN users u ON u.id=r.user_id "
            "WHERE r.code=? ORDER BY r.redeemed_at DESC, u.id LIMIT ? OFFSET ?",
            (code.upper(), limit, offset),
        )
        return (count_row[0] if count_row else 0, [dict(row) for row in rows])


async def get_user_promo_redemptions(user_id: int, limit: int = 20) -> list[dict]:
    async with _db() as conn:
        rows = await _all(
            conn,
            "SELECT r.code,p.reward_type,p.value,r.redeemed_at "
            "FROM promo_redemptions r JOIN promo_codes p ON p.code=r.code "
            "WHERE r.user_id=? ORDER BY r.redeemed_at DESC,r.code LIMIT ?",
            (user_id, limit),
        )
        return [dict(row) for row in rows]


async def count_results() -> int:
    async with _db() as conn:
        row = await _one(conn, "SELECT COUNT(*) FROM results WHERE status='completed'")
        return row[0] if row else 0


async def get_admin_stats(days: int | None = None) -> dict:
    async with _db() as conn:
        if days:
            df = f"datetime('now', '-{days} days')"
            u_cnt = (await _one(conn, f"SELECT COUNT(*) FROM users WHERE datetime(created_at)>={df}"))[0]
            tr = await _one(
                conn,
                f"SELECT COUNT(*), COALESCE(AVG(CAST(score AS REAL)/total*100),0) "
                f"FROM results WHERE total>0 AND status='completed' AND datetime(finished_at)>={df}",
            )
            pr = await _one(conn, f"SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payments WHERE status='paid' AND datetime(created_at)>={df}")
            dr = await _one(conn, f"SELECT COUNT(*), COALESCE(SUM(amount),0) FROM donations WHERE status='paid' AND datetime(created_at)>={df}")
        else:
            u_cnt = (await _one(conn, "SELECT COUNT(*) FROM users"))[0]
            tr = await _one(
                conn,
                "SELECT COUNT(*), COALESCE(AVG(CAST(score AS REAL)/total*100),0) "
                "FROM results WHERE total>0 AND status='completed'",
            )
            pr = await _one(conn, "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payments WHERE status='paid'")
            dr = await _one(conn, "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM donations WHERE status='paid'")
        qr = await _one(conn, "SELECT COUNT(*) FROM questions WHERE is_active=1")
        pop = await _all(
            conn,
            "SELECT subject, COUNT(*) as cnt FROM results "
            "WHERE status='completed' GROUP BY subject ORDER BY cnt DESC LIMIT 3",
        )
        return {
            "users": u_cnt or 0,
            "tests": tr[0] if tr else 0,
            "avg_score": round(tr[1] or 0, 1) if tr else 0,
            "payments": pr[0] if pr else 0,
            "payment_stars": pr[1] if pr else 0,
            "donations": dr[0] if dr else 0,
            "donation_stars": dr[1] if dr else 0,
            "questions": qr[0] if qr else 0,
            "popular": [(r["subject"], r["cnt"]) for r in pop],
        }


# ─── Payments ─────────────────────────────────────────────────────────────────

async def create_payment(user_id: int, charge_id: str, payload: str, amount: int, product_type: str = "unlock", expires_at: str | None = None) -> int:
    async with _db() as conn:
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO payments (user_id,charge_id,payload,amount,product_type,expires_at) VALUES (?,?,?,?,?,?)",
            (user_id, charge_id, payload, amount, product_type, expires_at),
        )
        await conn.commit()
        return cursor.lastrowid


async def record_paid_payment(
    user_id: int, charge_id: str, payload: str, amount: int,
    product_type: str, expires_at: str | None = None,
) -> bool:
    async with _db() as conn:
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO payments "
            "(user_id,charge_id,payload,amount,product_type,status,expires_at) "
            "VALUES (?,?,?,?,?,'paid',?)",
            (user_id, charge_id, payload, amount, product_type, expires_at),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def user_has_active_subscription(user_id: int) -> bool:
    if user_id in settings.admin_ids:
        return True

    async with _db() as conn:
        rows = await _all(
            conn,
            "SELECT expires_at FROM payments WHERE user_id=? AND status='paid' AND product_type='subscription' ORDER BY created_at DESC",
            (user_id,),
        )
        now = datetime.now()
        for row in rows:
            expires_at = row["expires_at"]
            if not expires_at:
                continue
            try:
                if datetime.fromisoformat(expires_at) > now:
                    return True
            except ValueError:
                continue
        return False


async def user_has_unlocked_result(
    user_id: int,
    result_id: int,
    subject: str | None = None,
) -> bool:
    async with _db() as conn:
        if subject is None:
            row = await _one(
                conn,
                "SELECT 1 FROM payments WHERE user_id=? AND payload IN (?,?) "
                "AND status='paid' AND product_type='unlock'",
                (user_id, f"unlock:{user_id}:{result_id}", f"unlock:{user_id}:{result_id}:all"),
            )
        else:
            row = await _one(
                conn,
                "SELECT 1 FROM payments WHERE user_id=? AND "
                "(payload=? OR payload=?) AND status='paid' AND product_type='unlock'",
                (
                    user_id,
                    f"unlock:{user_id}:{result_id}:{subject}",
                    f"unlock:{user_id}:{result_id}",
                ),
            )
        return row is not None


async def get_latest_subscription_expiry(user_id: int) -> datetime | None:
    async with _db() as conn:
        rows = await _all(
            conn,
            "SELECT expires_at FROM payments WHERE user_id=? AND status='paid' "
            "AND product_type='subscription' AND expires_at IS NOT NULL",
            (user_id,),
        )
        expirations = []
        for row in rows:
            try:
                expirations.append(datetime.fromisoformat(row["expires_at"]))
            except ValueError:
                continue
        return max(expirations) if expirations else None


async def get_subscriptions_expiring_on(target_date: date) -> list[dict]:
    async with _db() as conn:
        rows = await _all(
            conn,
            "SELECT user_id, expires_at FROM payments WHERE status='paid' "
            "AND product_type='subscription' AND expires_at IS NOT NULL",
        )

    latest_by_user: dict[int, datetime] = {}
    for row in rows:
        try:
            expiry = datetime.fromisoformat(row["expires_at"])
        except ValueError:
            continue
        user_id = row["user_id"]
        if user_id not in latest_by_user or expiry > latest_by_user[user_id]:
            latest_by_user[user_id] = expiry

    return [
        {"user_id": user_id, "expires_at": expiry.isoformat(timespec="seconds")}
        for user_id, expiry in latest_by_user.items()
        if expiry.date() == target_date
    ]


async def subscription_notice_sent(user_id: int, expires_at: str, notification_type: str) -> bool:
    async with _db() as conn:
        row = await _one(
            conn,
            "SELECT 1 FROM subscription_notifications WHERE user_id=? AND expires_at=? AND notification_type=?",
            (user_id, expires_at, notification_type),
        )
        return row is not None


async def mark_subscription_notice_sent(user_id: int, expires_at: str, notification_type: str) -> None:
    async with _db() as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO subscription_notifications (user_id, expires_at, notification_type) VALUES (?,?,?)",
            (user_id, expires_at, notification_type),
        )
        await conn.commit()


async def get_user_mistakes(user_id: int, limit: int = 10) -> list[dict]:
    async with _db() as conn:
        rows = await _all(
            conn,
            "SELECT answers_json FROM results WHERE user_id=? ORDER BY finished_at DESC LIMIT 20",
            (user_id,),
        )
        mistakes: list[dict] = []
        for row in rows:
            answers = json.loads(row["answers_json"]) if row["answers_json"] else []
            for answer in answers:
                if not answer.get("is_correct"):
                    mistakes.append({
                        "question": answer.get("question", ""),
                        "correct_text": answer.get("options", [])[answer.get("correct", 0)] if answer.get("options") else "",
                    })
                    if len(mistakes) >= limit:
                        return mistakes
        return mistakes


async def get_user_subscription(user_id: int) -> dict | None:
    async with _db() as conn:
        row = await _one(
            conn,
            "SELECT * FROM payments WHERE user_id=? AND status='paid' AND product_type='subscription' ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        return dict(row) if row else None


async def confirm_payment(charge_id: str) -> bool:
    async with _db() as conn:
        row = await _one(conn, "SELECT status FROM payments WHERE charge_id=?", (charge_id,))
        if row and row[0] == "paid":
            return False
        await conn.execute("UPDATE payments SET status='paid' WHERE charge_id=?", (charge_id,))
        await conn.commit()
        return True


async def get_user_payments(user_id: int) -> list[dict]:
    async with _db() as conn:
        rows = await _all(conn, "SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
        return [dict(r) for r in rows]


async def count_payments() -> int:
    async with _db() as conn:
        row = await _one(conn, "SELECT COUNT(*) FROM payments WHERE status='paid'")
        return row[0] if row else 0


async def get_payments_admin(filter_type: str = "all", limit: int = 10, offset: int = 0) -> list[dict]:
    async with _db() as conn:
        if filter_type == "paid":
            rows = await _all(conn, "SELECT * FROM payments WHERE status='paid' ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        elif filter_type == "unlock":
            rows = await _all(conn, "SELECT * FROM payments WHERE product_type='unlock' ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        else:
            rows = await _all(conn, "SELECT * FROM payments ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [dict(r) for r in rows]


async def count_payments_admin(filter_type: str = "all") -> int:
    async with _db() as conn:
        if filter_type == "paid":
            row = await _one(conn, "SELECT COUNT(*) FROM payments WHERE status='paid'")
        elif filter_type == "unlock":
            row = await _one(conn, "SELECT COUNT(*) FROM payments WHERE product_type='unlock'")
        else:
            row = await _one(conn, "SELECT COUNT(*) FROM payments")
        return row[0] if row else 0


# ─── Donations ────────────────────────────────────────────────────────────────

async def create_donation(user_id: int, charge_id: str, amount: int) -> int:
    async with _db() as conn:
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO donations (user_id,charge_id,amount) VALUES (?,?,?)",
            (user_id, charge_id, amount),
        )
        await conn.commit()
        return cursor.lastrowid


async def confirm_donation(charge_id: str) -> bool:
    async with _db() as conn:
        row = await _one(conn, "SELECT status FROM donations WHERE charge_id=?", (charge_id,))
        if row and row[0] == "paid":
            return False
        await conn.execute("UPDATE donations SET status='paid' WHERE charge_id=?", (charge_id,))
        await conn.commit()
        return True


async def count_donations() -> int:
    async with _db() as conn:
        row = await _one(conn, "SELECT COALESCE(SUM(amount),0) FROM donations WHERE status='paid'")
        return row[0] if row else 0


async def list_donations(limit: int = 30, offset: int = 0) -> list[dict]:
    async with _db() as conn:
        rows = await _all(conn, "SELECT * FROM donations ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [dict(r) for r in rows]


async def count_donations_total() -> tuple[int, int]:
    """Returns (count, total_stars)."""
    async with _db() as conn:
        row = await _one(conn, "SELECT COUNT(*), COALESCE(SUM(amount),0) FROM donations WHERE status='paid'")
        return (row[0] or 0, row[1] or 0) if row else (0, 0)
