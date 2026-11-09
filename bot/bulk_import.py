from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from typing import Any


JSON_TEMPLATE = [
    {
        "subject": "mathematics",
        "language": "ru",
        "topic": "Уравнения",
        "question_text": "Найдите корень уравнения: 2x + 6 = 14",
        "options": ["x = 2", "x = 4", "x = 6", "x = 8"],
        "correct_option_index": 1,
        "explanation": "2x = 14 - 6 => 2x = 8 => x = 4",
    },
    {
        "subject": "english",
        "language": "en",
        "topic": "Grammar",
        "question_text": "Choose the correct form: She ___ to school every day.",
        "options": ["go", "goes", "going", "gone"],
        "correct_option_index": 1,
        "explanation": "Use the third-person singular form 'goes'.",
    },
    {
        "subject": "iq",
        "language": "ru",
        "topic": "Последовательности",
        "question_text": "Какое число продолжает последовательность: 2, 4, 8, 16, ...?",
        "options": ["18", "24", "32", "64"],
        "correct_option_index": 2,
        "explanation": "Каждое следующее число вдвое больше предыдущего.",
    },
]

CSV_HEADERS = [
    "subject",
    "topic",
    "language",
    "question_text",
    "options",
    "correct_option_index",
    "explanation",
]


def _as_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _parse_options(raw: Any) -> list[str]:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                raw = parsed
            else:
                raw = [parsed]
        except json.JSONDecodeError:
            for delim in (";", "|", "\n"):
                if delim in text:
                    raw = [item.strip() for item in text.split(delim) if item.strip()]
                    break
            else:
                raw = [text]

    if isinstance(raw, (list, tuple, set)):
        normalized = []
        for item in raw:
            value = _as_text(item)
            if value:
                normalized.append(value)
        return normalized

    value = _as_text(raw)
    return [value] if value else []


def _parse_correct(raw: Any) -> int:
    if isinstance(raw, list):
        if len(raw) != 1:
            raise ValueError("для вопроса с одним выбираемым ответом нужен ровно один правильный индекс")
        raw = raw[0]
    if isinstance(raw, str):
        raw = raw.strip()
        if raw in {"", "-"}:
            raise ValueError("correct_option_index is empty")
        try:
            return int(raw)
        except ValueError as exc:
            raise ValueError(f"correct_option_index must be an integer: {raw!r}") from exc
    if isinstance(raw, (int, float)) and int(raw) == raw:
        return int(raw)
    raise ValueError(f"correct_option_index must be an integer: {raw!r}")


def normalize_question_record(item: Mapping[str, Any] | None, index: int = 1) -> tuple[dict | None, str | None]:
    if not isinstance(item, Mapping):
        return None, f"#{index}: запись должна быть объектом JSON"

    raw_subject = item.get("subject")
    subject = _as_text(raw_subject)
    if not subject:
        return None, f"#{index}: поле 'subject' обязательно"

    raw_question = item.get("question_text", item.get("question"))
    question_text = _as_text(raw_question)
    if not question_text:
        return None, f"#{index}: поле 'question_text' обязательно"

    options = _parse_options(item.get("options"))
    if len(options) < 2:
        return None, f"#{index}: 'options' должен содержать минимум 2 варианта"

    try:
        correct_index = _parse_correct(
            item.get("correct_option_index", item.get("correct", item.get("correct_index")))
        )
    except ValueError as exc:
        return None, f"#{index}: {exc}"

    if not 0 <= correct_index < len(options):
        return None, f"#{index}: correct_option_index должен быть в диапазоне [0, {len(options)-1}]"

    topic = _as_text(item.get("topic")) or None
    language = _as_text(item.get("language", item.get("lang"))) or "ru"
    explanation = _as_text(item.get("explanation", item.get("Разбор"))) or None
    difficulty = _as_text(item.get("difficulty")) or "medium"

    normalized = {
        "subject": subject,
        "topic": topic,
        "language": language,
        "question": question_text,
        "options": options,
        "correct": [correct_index],
        "explanation": explanation,
        "difficulty": difficulty,
    }
    return normalized, None


def _extract_rows_from_json(data: Any) -> list[Any]:
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    if isinstance(data, list):
        return data
    if isinstance(data, Mapping):
        return [data]
    raise ValueError("Ожидается JSON-массив или объект с полем 'questions'")


def _extract_rows_from_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise ValueError("CSV-файл пуст или не содержит заголовков")
    rows = []
    for row in reader:
        record = {key.strip(): value for key, value in row.items() if key is not None}
        if record:
            rows.append(record)
    if not rows:
        raise ValueError("CSV-файл не содержит записей")
    return rows


def _extract_rows_from_xlsx(raw_bytes: bytes | io.BytesIO) -> list[dict[str, Any]]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise ValueError("Для загрузки .xlsx нужен пакет openpyxl. Установите его через pip install openpyxl.") from exc

    if isinstance(raw_bytes, io.BytesIO):
        payload = raw_bytes.getvalue()
    else:
        payload = raw_bytes

    workbook = load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    if not workbook.sheetnames:
        raise ValueError("XLSX-файл не содержит листов")
    sheet = workbook[workbook.sheetnames[0]]
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise ValueError("XLSX-файл пуст")

    header = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    data_rows: list[dict[str, Any]] = []
    for row in rows[1:]:
        if row is None or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        record = {}
        for idx, value in enumerate(row):
            if idx < len(header):
                record[header[idx]] = value
        if record:
            data_rows.append(record)
    if not data_rows:
        raise ValueError("В XLSX-файле нет данных после заголовка")
    return data_rows


def parse_import_payload(raw: str | bytes | io.BytesIO, file_name: str | None = None) -> list[dict[str, Any]]:
    """Parse a bulk import file into normalized, DB-ready question entries."""
    if isinstance(raw, io.BytesIO):
        raw = raw.getvalue()

    if file_name is not None:
        lower_name = file_name.lower()
        if lower_name.endswith(".json"):
            if isinstance(raw, (bytes, bytearray)):
                text = raw.decode("utf-8-sig")
            else:
                text = str(raw)
            payload = json.loads(text)
            rows = _extract_rows_from_json(payload)
        elif lower_name.endswith(".csv"):
            text = raw.decode("utf-8-sig") if isinstance(raw, (bytes, bytearray)) else str(raw)
            rows = _extract_rows_from_csv(text)
        elif lower_name.endswith(".xlsx"):
            if isinstance(raw, str):
                raise ValueError("XLSX должен быть отправлен как двоичный файл")
            rows = _extract_rows_from_xlsx(raw)
        else:
            raise ValueError("Поддерживаются только .json, .csv и .xlsx файлы")
    else:
        text = raw.decode("utf-8-sig") if isinstance(raw, (bytes, bytearray)) else str(raw)
        if not text.strip():
            raise ValueError("Файл пуст")
        try:
            payload = json.loads(text)
            rows = _extract_rows_from_json(payload)
        except json.JSONDecodeError:
            rows = _extract_rows_from_csv(text)

    normalized = []
    errors = []
    for idx, row in enumerate(rows, start=1):
        item, error = normalize_question_record(row, idx)
        if error:
            errors.append(error)
            continue
        normalized.append(item)
    if errors:
        shown_errors = errors[:10]
        if len(errors) > len(shown_errors):
            shown_errors.append(f"... и ещё {len(errors) - len(shown_errors)} ошибок")
        raise ValueError("\n".join(shown_errors))
    return normalized


def build_template_json() -> bytes:
    return json.dumps(JSON_TEMPLATE, ensure_ascii=False, indent=2).encode("utf-8")


def build_template_csv() -> bytes:
    import csv as _csv

    output = io.StringIO()
    writer = _csv.writer(output)
    writer.writerow(CSV_HEADERS)
    for item in JSON_TEMPLATE:
        writer.writerow([
            item["subject"],
            item["topic"],
            item["language"],
            item["question_text"],
            json.dumps(item["options"], ensure_ascii=False),
            item["correct_option_index"],
            item["explanation"],
        ])
    return output.getvalue().encode("utf-8")


def build_template_xlsx() -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise RuntimeError("Для генерации .xlsx нужен пакет openpyxl.") from exc

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Questions"
    sheet.append(CSV_HEADERS)
    for item in JSON_TEMPLATE:
        sheet.append([
            item["subject"],
            item["topic"],
            item["language"],
            item["question_text"],
            json.dumps(item["options"], ensure_ascii=False),
            item["correct_option_index"],
            item["explanation"],
        ])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
