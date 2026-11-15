from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).parent
serial = 0
questions: list[dict] = []


def add(
    subject: str,
    language: str,
    difficulty: str,
    topic: str,
    prompt: str,
    answer: str,
    distractors: list[str],
    explanation: str,
) -> None:
    global serial
    serial += 1
    choices = [answer, *distractors]
    unique: list[str] = []
    for choice in choices:
        if choice not in unique:
            unique.append(choice)
    while len(unique) < 4:
        unique.append(f"{unique[-1]} (другой вариант)")
    correct = serial % 4
    options = unique[:4]
    options[0], options[correct] = options[correct], options[0]
    questions.append({
        "subject": subject,
        "language": language,
        "topic": topic,
        "question_text": prompt,
        "options": options,
        "correct_option_index": correct,
        "explanation": f"✅ Ответ: {answer}\n\n{explanation}",
        "difficulty": difficulty,
    })


def math_questions() -> None:
    subject, language = "mathematics", "ru"
    for i in range(10):
        a, b, x = 2 + i % 5, 3 + i, 4 + i % 7
        add(subject, language, "easy", "Арифметика",
            f"Вычислите: {a} × {x} + {b}.",
            str(a * x + b), [str(a * x - b), str(a + x + b), str(a * (x + b))],
            f"🧩 Сначала выполняем умножение: {a} × {x} = {a*x}.\n"
            f"🧮 Затем прибавляем {b}: {a*x} + {b} = {a*x+b}.")

    medium: list[Callable[[int], None]] = [
        lambda i: _math_linear(subject, language, i, "medium"),
        lambda i: _math_fraction(subject, language, i),
        lambda i: _math_percent(subject, language, i, "medium"),
        lambda i: _math_rectangle(subject, language, i),
        lambda i: _math_ratio(subject, language, i),
        lambda i: _math_sequence(subject, language, i, "medium"),
        lambda i: _math_average(subject, language, i),
        lambda i: _math_probability(subject, language, i),
        lambda i: _math_factor(subject, language, i),
        lambda i: _math_speed(subject, language, i),
    ]
    for family in medium:
        for i in range(3):
            family(i)

    hard: list[Callable[[int], None]] = [
        lambda i: _math_linear(subject, language, i + 5, "hard"),
        lambda i: _math_quadratic(subject, language, i),
        lambda i: _math_system(subject, language, i),
        lambda i: _math_percent(subject, language, i + 3, "hard"),
        lambda i: _math_sequence(subject, language, i + 3, "hard"),
        lambda i: _math_geometry(subject, language, i),
        lambda i: _math_probability(subject, language, i + 3),
        lambda i: _math_exponent(subject, language, i),
        lambda i: _math_work(subject, language, i),
        lambda i: _math_inequality(subject, language, i),
    ]
    for family in hard:
        for i in range(6):
            family(i)


def _math_linear(s: str, lang: str, i: int, difficulty: str) -> None:
    a, b, x = 2 + i % 6, 3 + i % 9, 2 + (i * 3) % 9
    rhs = a * x + b
    add(s, lang, difficulty, "Линейные уравнения", f"Решите уравнение: {a}x + {b} = {rhs}.",
        str(x), [str(x + 1), str(x - 1), str(-x)],
        f"🧩 Перенесём свободный член: {a}x = {rhs} − {b} = {a*x}.\n"
        f"🧮 Делим обе части на {a}: x = {x}.")


def _math_fraction(s: str, lang: str, i: int) -> None:
    den = 3 + i % 5
    num1, num2 = 1 + i % 2, 1 + (i + 1) % 2
    total = num1 + num2
    answer = f"{total}/{den}"
    add(s, lang, "medium", "Дроби",
        f"Вычислите: {num1}/{den} + {num2}/{den}.",
        answer, [f"{total}/{den*2}", f"{num1*num2}/{den}", f"{total+1}/{den}"],
        f"🧩 Знаменатели одинаковые, поэтому складываем числители: {num1} + {num2} = {total}.\n"
        f"🧮 Знаменатель остаётся {den}. Получаем {answer}.")


def _math_percent(s: str, lang: str, i: int, difficulty: str) -> None:
    base = 100 + 20 * (i % 8)
    pct = 10 + 5 * (i % 7)
    value = base * pct // 100
    add(s, lang, difficulty, "Проценты", f"Найдите {pct}% от {base}.",
        str(value), [str(value + pct), str(base - value), str(value * 2)],
        f"🧩 Переводим процент в дробь: {pct}% = {pct}/100.\n"
        f"🧮 Умножаем: {base} × {pct}/100 = {value}.")


def _math_rectangle(s: str, lang: str, i: int) -> None:
    a, b = 4 + i, 3 + i % 5
    area = a * b
    add(s, lang, "medium", "Геометрия", f"Найдите площадь прямоугольника со сторонами {a} см и {b} см.",
        f"{area} см²", [f"{2*(a+b)} см²", f"{a+b} см²", f"{area+a} см²"],
        f"🧩 Площадь прямоугольника равна произведению его сторон.\n"
        f"🧮 S = {a} × {b} = {area} см².")


def _math_ratio(s: str, lang: str, i: int) -> None:
    left, right = 2 + i % 4, 3 + i % 3
    total = (left + right) * (4 + i)
    answer = left * (4 + i)
    add(s, lang, "medium", "Пропорции",
        f"Число {total} разделили в отношении {left}:{right}. Чему равна меньшая часть?",
        str(answer), [str(total-answer), str(left+right), str(answer+5)],
        f"🧩 Всего частей: {left} + {right} = {left+right}.\n"
        f"🧮 Одна часть равна {total} ÷ {left+right}. Меньшая часть: "
        f"{total} × {left}/{left+right} = {answer}.")


def _math_sequence(s: str, lang: str, i: int, difficulty: str) -> None:
    first, step, n = 2 + i % 8, 3 + i % 6, 5 + i % 7
    answer = first + step * n
    add(s, lang, difficulty, "Последовательности",
        f"Найдите следующий член последовательности: {first}, {first+step}, {first+2*step}, …",
        str(first + 3 * step), [str(first + 2 * step), str(first + 4 * step), str(first * step)],
        f"🧩 Разность соседних членов постоянна: {first+step} − {first} = {step}.\n"
        f"🧮 Следующий член: {first+2*step} + {step} = {first+3*step}.")


def _math_average(s: str, lang: str, i: int) -> None:
    a, b, c = 4 + i, 8 + i, 12 + i
    answer = (a + b + c) // 3
    add(s, lang, "medium", "Среднее арифметическое",
        f"Найдите среднее арифметическое чисел {a}, {b} и {c}.",
        str(answer), [str(answer+1), str(b), str(a+b+c)],
        f"🧩 Складываем числа: {a} + {b} + {c} = {a+b+c}.\n"
        f"🧮 Делим сумму на количество чисел: {a+b+c} ÷ 3 = {answer}.")


def _math_probability(s: str, lang: str, i: int) -> None:
    red, blue = 2 + i % 4, 3 + i % 5
    total = red + blue
    add(s, lang, "hard" if i >= 3 else "medium", "Вероятность",
        f"В мешке {red} красных и {blue} синих шаров. Какова вероятность вынуть красный шар?",
        f"{red}/{total}", [f"{blue}/{total}", f"{red}/{blue}", f"1/{total}"],
        f"🧩 Благоприятных исходов {red}, всего шаров {red} + {blue} = {total}.\n"
        f"🧮 Вероятность = благоприятные исходы / все исходы = {red}/{total}.")


def _math_factor(s: str, lang: str, i: int) -> None:
    a, b = 2 + i % 7, 3 + i % 6
    product = a * b
    add(s, lang, "medium", "Разложение на множители",
        f"Какое значение имеет выражение x² − {product}x + {a+b}x при x = 1?",
        str(1 - product + a + b), [str(1+product-a-b), str(a*b), str(a+b)],
        f"🧩 Подставляем x = 1: 1² − {product}·1 + {a+b}·1.\n"
        f"🧮 Получаем 1 − {product} + {a+b} = {1-product+a+b}.")


def _math_speed(s: str, lang: str, i: int) -> None:
    speed, hours = 30 + 10 * i, 2 + i % 4
    distance = speed * hours
    add(s, lang, "medium", "Движение", f"Автомобиль ехал со скоростью {speed} км/ч в течение {hours} ч. Какой путь он прошёл?",
        f"{distance} км", [f"{speed+hours} км", f"{distance+speed} км", f"{speed//hours} км"],
        f"🧩 Используем формулу пути: s = v × t.\n"
        f"🧮 s = {speed} × {hours} = {distance} км.")


def _math_quadratic(s: str, lang: str, i: int) -> None:
    root1, root2 = 2 + i % 6, 5 + i % 7
    total, product = root1 + root2, root1 * root2
    add(s, lang, "hard", "Квадратные уравнения",
        f"Найдите меньший корень уравнения x² − {total}x + {product} = 0.",
        str(min(root1, root2)), [str(max(root1, root2)), str(-root1), str(product)],
        f"🧩 Ищем два числа с суммой {total} и произведением {product}: это {root1} и {root2}.\n"
        f"🧮 Уравнение раскладывается: (x − {root1})(x − {root2}) = 0. "
        f"Корни {root1} и {root2}; меньший — {min(root1, root2)}.")


def _math_system(s: str, lang: str, i: int) -> None:
    x, y = 2 + i % 8, 3 + (i * 2) % 7
    a, b = x + y, x - y
    add(s, lang, "hard", "Системы уравнений",
        f"Найдите x + y, если x − y = {b} и 2x + 2y = {2*a}.",
        str(a), [str(b), str(2*a), str(a+1)],
        f"🧩 Во втором уравнении делим обе части на 2: x + y = {a}.\n"
        f"🧮 Требуемая сумма уже найдена: x + y = {a}.")


def _math_geometry(s: str, lang: str, i: int) -> None:
    r = 2 + i % 8
    diameter = 2 * r
    area_factor = r * r
    add(s, lang, "hard", "Геометрия",
        f"Радиус круга равен {r} см. Чему равна площадь круга, если π оставить символом?",
        f"{area_factor}π см²", [f"{diameter}π см²", f"{r}π см²", f"{area_factor} см²"],
        f"🧩 Площадь круга вычисляется по формуле S = πr².\n"
        f"🧮 Подставляем r = {r}: S = π × {r}² = {area_factor}π см².")


def _math_exponent(s: str, lang: str, i: int) -> None:
    a, b = 2 + i % 5, 2 + (i * 2) % 4
    answer = a ** (b + 1)
    add(s, lang, "hard", "Степени",
        f"Упростите выражение ({a}²)^{b} ÷ {a}^{b-1}.",
        str(answer), [str(a**(b+2)), str(a**b), str(a**(b-1))],
        f"🧩 При возведении степени в степень показатели перемножаются: ({a}²)^{b} = {a}^{2*b}.\n"
        f"🧮 При делении степеней с одинаковым основанием показатели вычитаются: "
        f"{a}^{2*b} ÷ {a}^{b-1} = {a}^{2*b-(b-1)} = {a}^{b+1} = {answer}.")


def _math_work(s: str, lang: str, i: int) -> None:
    t1, t2 = 4 + i % 5, 6 + i % 4
    numerator = t1 * t2
    answer = f"{Fraction(numerator, t1+t2)} ч"
    add(s, lang, "hard", "Совместная работа",
        f"Первый мастер выполняет работу за {t1} ч, второй — за {t2} ч. За сколько часов они выполнят её вместе?",
        answer, [f"{t1+t2} ч", f"{min(t1,t2)} ч", f"{abs(t1-t2)} ч"],
        f"🧩 Их скорости работы: 1/{t1} и 1/{t2} работы в час.\n"
        f"🧮 Вместе: 1/{t1} + 1/{t2} = ({t1+t2})/{numerator}. "
        f"Время равно обратной величине: {numerator}/{t1+t2} ч.")


def _math_inequality(s: str, lang: str, i: int) -> None:
    a, bound = 2 + i % 5, 3 + i % 8
    answer = bound + 1
    add(s, lang, "hard", "Неравенства",
        f"Какое наименьшее целое число x удовлетворяет неравенству {a}x > {a*bound}?",
        str(answer), [str(bound), str(answer+1), str(-answer)],
        f"🧩 Делим обе части на положительное число {a}; знак неравенства не меняется.\n"
        f"🧮 Получаем x > {bound}. Наименьшее целое решение — {answer}.")


def english_questions() -> None:
    subject, language = "english", "en"
    easy = [
        ("Choose the correct form: My sister ___ a student.", "is", ["are", "am", "be"], "🧩 The subject is “my sister”, which is third-person singular.\n🧮 The correct present form of “to be” is “is”."),
        ("Choose the plural form of “child”.", "children", ["childs", "childes", "childrens"], "🧩 “Child” has an irregular plural.\n🧮 Its standard plural form is “children”."),
        ("Choose the correct article: I saw ___ elephant at the zoo.", "an", ["a", "the", "no article"], "🧩 “Elephant” begins with a vowel sound.\n🧮 Use “an” before a singular countable noun beginning with a vowel sound."),
        ("Choose the opposite of “early”.", "late", ["fast", "soon", "quick"], "🧩 We need the antonym, not a synonym.\n🧮 The opposite of “early” is “late”."),
        ("Choose the correct form: They ___ football on Sundays.", "play", ["plays", "playing", "played"], "🧩 “They” is a plural subject and the sentence describes a habit.\n🧮 Use the base verb in the present simple: “play”."),
        ("Choose the correct preposition: The book is ___ the table.", "on", ["at", "into", "from"], "🧩 The book is resting on the surface.\n🧮 The correct preposition is “on”."),
        ("What is the past form of “go”?", "went", ["goed", "gone", "going"], "🧩 “Go” is an irregular verb.\n🧮 Its past simple form is “went”; “gone” is its past participle."),
        ("Choose the correct pronoun: This is Anna. ___ is my friend.", "She", ["He", "They", "It"], "🧩 Anna is one person referred to with a feminine pronoun.\n🧮 Use “she”."),
        ("Choose the correct form: We ___ at home now.", "are", ["is", "am", "be"], "🧩 “We” takes the plural form of “to be”.\n🧮 The correct form is “are”."),
        ("Choose a synonym for “begin”.", "start", ["finish", "close", "leave"], "🧩 A synonym has a similar meaning.\n🧮 “Start” means the same as “begin”."),
    ]
    for q in easy:
        add(subject, language, "easy", "Grammar and vocabulary", *q[:1], q[1], q[2], q[3])

    medium = [
        lambda i: _english_tense(i, "medium"),
        lambda i: _english_article(i),
        lambda i: _english_comparison(i),
        lambda i: _english_preposition(i, "medium"),
        lambda i: _english_modal(i),
        lambda i: _english_connector(i),
        lambda i: _english_quantifier(i),
        lambda i: _english_word_form(i),
        lambda i: _english_passive(i, "medium"),
        lambda i: _english_conditional(i, "medium"),
    ]
    for family in medium:
        for i in range(3):
            family(i)
    hard = [
        lambda i: _english_tense(i + 3, "hard"),
        lambda i: _english_conditional(i + 3, "hard"),
        lambda i: _english_passive(i + 3, "hard"),
        lambda i: _english_reported(i),
        lambda i: _english_relative(i),
        lambda i: _english_preposition(i + 3, "hard"),
        lambda i: _english_phrasal(i),
        lambda i: _english_word_form(i + 3),
        lambda i: _english_inversion(i),
        lambda i: _english_vocab(i),
    ]
    for family in hard:
        for i in range(6):
            family(i)


def _english_tense(i: int, difficulty: str) -> None:
    subjects = ["Maya", "The workers", "Our teacher", "I", "The train", "They"]
    verbs = [("finish", "has finished", "finished", "is finishing"),
             ("arrive", "have arrived", "arrived", "are arriving"),
             ("write", "has written", "wrote", "is writing"),
             ("see", "have seen", "saw", "am seeing"),
             ("leave", "has left", "left", "is leaving"),
             ("complete", "have completed", "completed", "are completing")]
    subject, (verb, correct, past, progressive) = subjects[i % 6], verbs[i % 6]
    plural = subject in {"The workers", "They", "I"}
    correct = ("have " if plural else "has ") + {
        "finish": "finished", "arrive": "arrived", "write": "written",
        "see": "seen", "leave": "left", "complete": "completed",
    }[verb]
    time_marker = "the task by now" if i >= 6 else "the task already"
    add("english", "en", difficulty, "Verb tenses",
        f"Choose the correct form: {subject} ___ {time_marker}.",
        correct, [past, progressive, "will " + verb],
        f"🧩 “Already” commonly signals a completed action with present relevance.\n"
        f"🧮 Use the present perfect: have/has + past participle. "
        f"{'Plural subjects take “have”.' if plural else 'A singular subject takes “has”.'}")


def _english_article(i: int) -> None:
    noun, article, distractors = [
        ("hour", "an", ["a", "the", "no article"]),
        ("university", "a", ["an", "the", "no article"]),
        ("honest answer", "an", ["a", "the", "no article"]),
    ][i % 3]
    add("english", "en", "medium", "Articles",
        f"Choose the correct article: It took me ___ {noun} to finish.",
        article, distractors,
        f"🧩 Choose “a/an” by the first sound, not simply the first letter.\n"
        f"🧮 “{noun}” begins with {'a vowel' if article == 'an' else 'a consonant'} sound, so “{article}” is correct.")


def _english_comparison(i: int) -> None:
    pairs = [("careful", "more careful", "carefuller", "most careful"),
             ("good", "better", "gooder", "best"),
             ("far", "farther", "farrer", "farthest")]
    adj, answer, wrong1, wrong2 = pairs[i % 3]
    add("english", "en", "medium", "Comparatives",
        f"Complete the sentence with the comparative form: This route is ___ than the old one ({adj}).",
        answer, [wrong1, wrong2, adj],
        f"🧩 The sentence compares two routes, so it needs a comparative adjective.\n"
        f"🧮 The comparative form of “{adj}” is “{answer}”.")


def _english_preposition(i: int, difficulty: str) -> None:
    records = [
        ("interested ___ science", "in", ["on", "at", "for"], "The adjective “interested” is followed by “in”."),
        ("depend ___ the weather", "on", ["of", "at", "with"], "The verb “depend” is followed by “on”."),
        ("good ___ solving problems", "at", ["in", "on", "for"], "“Good at” is used before a skill or activity."),
        ("apologised ___ being late", "for", ["to", "at", "with"], "“Apologise for” introduces the reason."),
        ("arrived ___ the airport", "at", ["in", "on", "to"], "Use “at” for a particular point or place."),
        ("responsible ___ the project", "for", ["of", "to", "with"], "The adjective “responsible” is followed by “for”."),
        ("keen ___ learning new skills", "on", ["at", "for", "with"], "The adjective “keen” is followed by “on”."),
        ("objected ___ the proposed changes", "to", ["for", "with", "at"], "The verb “object” is followed by “to”."),
        ("succeeded ___ solving the puzzle", "in", ["at", "on", "for"], "The verb “succeed” is followed by “in”."),
        ("applied ___ the position", "for", ["to", "at", "with"], "Use “apply for” when referring to a job or position."),
        ("familiar ___ the procedure", "with", ["to", "for", "at"], "The adjective “familiar” is followed by “with”."),
        ("prevented ___ entering the room", "from", ["of", "to", "for"], "The verb “prevent” is followed by “from” + gerund."),
    ]
    phrase, answer, wrong, rule = records[i % len(records)]
    add("english", "en", difficulty, "Prepositions", f"Choose the correct preposition in the phrase “{phrase}”.",
        answer, wrong, f"🧩 This phrase uses a fixed adjective/verb + preposition pattern.\n🧮 {rule}")


def _english_modal(i: int) -> None:
    records = [
        ("You ___ wear a seat belt; it is the law.", "must", ["might", "could", "would"], "“Must” expresses a strong obligation."),
        ("___ I borrow your pen, please?", "Could", ["Must", "Should", "Need"], "“Could I…?” is a polite request."),
        ("You ___ see a doctor if the pain continues.", "should", ["mustn't", "can't", "wouldn't"], "“Should” gives advice."),
    ]
    prompt, answer, wrong, rule = records[i % len(records)]
    add("english", "en", "medium", "Modal verbs", prompt, answer, wrong,
        f"🧩 Identify the meaning required by the context.\n🧮 {rule}")


def _english_connector(i: int) -> None:
    records = [
        ("It was raining, ___ we continued the match.", "but", ["because", "so", "unless"], "The ideas contrast."),
        ("She studied hard, ___ she passed the exam.", "so", ["although", "unless", "but"], "The second clause is a result."),
        ("___ he was tired, he finished the report.", "Although", ["Because", "So", "Unless"], "The clauses contrast."),
    ]
    first, answer, wrong, rule = records[i % 3]
    add("english", "en", "medium", "Linking words", first, answer, wrong,
        f"🧩 Determine the logical relationship between the clauses.\n🧮 {rule}")


def _english_quantifier(i: int) -> None:
    records = [
        ("There isn't ___ milk left.", "much", ["many", "few", "several"], "“Milk” is uncountable, so use “much” in a negative sentence."),
        ("How ___ books did you borrow?", "many", ["much", "little", "any"], "“Books” is a plural countable noun, so use “many”."),
        ("We have ___ time, so let's hurry.", "little", ["few", "many", "several"], "“Time” is uncountable; “little” means not much."),
    ]
    prompt, answer, wrong, rule = records[i % len(records)]
    add("english", "en", "medium", "Quantifiers", prompt, answer, wrong,
        f"🧩 Check whether the noun is countable or uncountable.\n🧮 {rule}")


def _english_word_form(i: int) -> None:
    records = [
        ("She answered the question ___. (CONFIDENT)", "confidently", ["confident", "confidence", "confidentness"], "An adverb modifies the verb “answered”; the adverb is “confidently”."),
        ("The decision was completely ___. (EXPECT)", "unexpected", ["unexpectedly", "expectation", "expecting"], "An adjective is required after “was”; “unexpected” fits the meaning."),
        ("Their ___ surprised everyone. (ARRIVE)", "arrival", ["arrive", "arrivingly", "arrived"], "A noun is needed as the subject; the noun form is “arrival”."),
        ("We were impressed by her ___ during the interview. (CONFIDENT)", "confidence", ["confident", "confidently", "confidential"], "A noun is needed after the possessive adjective “her”; the noun is “confidence”."),
        ("The team made a ___ improvement. (SIGNIFY)", "significant", ["significantly", "significance", "signified"], "An adjective is needed before the noun “improvement”; the adjective is “significant”."),
        ("The new system operates ___. (EFFICIENT)", "efficiently", ["efficient", "efficiency", "inefficient"], "An adverb modifies the verb “operates”; the adverb is “efficiently”."),
        ("There is no ___ that the plan will work. (CERTAIN)", "certainty", ["certain", "certainly", "certify"], "A noun is needed after “no”; the noun is “certainty”."),
        ("The instructions were ___ and easy to follow. (HELP)", "helpful", ["helpfully", "helpless", "help"], "An adjective is needed after “were”; “helpful” fits the meaning."),
        ("The discovery was extremely ___. (IMPORT)", "important", ["importance", "importantly", "import"], "An adjective is needed after “was”; the adjective is “important”."),
    ]
    prompt, answer, wrong, rule = records[i % len(records)]
    add("english", "en", "medium" if i < 3 else "hard", "Word formation", prompt, answer, wrong,
        f"🧩 Identify the part of speech required by the sentence.\n🧮 {rule}")


def _english_passive(i: int, difficulty: str) -> None:
    subjects = ["The letters", "The bridge", "These meals", "The report", "The rooms", "The results",
                "The packages", "The museum", "The documents", "The machines", "The invitations", "The website"]
    past = ["send", "build", "prepare", "write", "clean", "publish",
            "deliver", "renovate", "check", "inspect", "print", "update"]
    participles = ["sent", "built", "prepared", "written", "cleaned", "published",
                   "delivered", "renovated", "checked", "inspected", "printed", "updated"]
    subject, verb, participle = subjects[i % len(subjects)], past[i % len(past)], participles[i % len(participles)]
    be = "are" if subject in {"The letters", "These meals", "The rooms", "The results", "The packages", "The documents", "The machines", "The invitations"} else "is"
    answer = f"{be} {participle}"
    add("english", "en", difficulty, "Passive voice",
        f"Complete the passive sentence: {subject} ___ every morning. ({verb})",
        answer, [f"{be} {verb}", f"was {participle}", f"have {participle}"],
        f"🧩 In the present simple passive, use am/is/are + past participle.\n"
        f"🧮 “{subject}” is {'plural' if be == 'are' else 'singular'}, so the correct form is “{answer}”.")


def _english_conditional(i: int, difficulty: str) -> None:
    records = [
        ("If water reaches 100°C, it ___. (boil)", "boils", ["will boil", "would boil", "boiled"], "A general truth uses the zero conditional: if + present simple, present simple."),
        ("If I had more time, I ___ another language. (learn)", "would learn", ["will learn", "learned", "would have learned"], "An unreal or hypothetical present uses if + past simple and would + base verb."),
        ("If she had left earlier, she ___ the train. (catch)", "would have caught", ["would catch", "will catch", "caught"], "A past unreal condition uses if + past perfect and would have + past participle."),
        ("If it rains tomorrow, we ___ at home. (stay)", "will stay", ["would stay", "stayed", "would have stayed"], "A real future possibility uses if + present simple and will + base verb."),
        ("If he ___ harder, he would pass. (study)", "studied", ["studies", "will study", "had studied"], "The second conditional uses past simple in the if-clause."),
        ("If they had known the address, they ___ us. (visit)", "would have visited", ["will visit", "would visit", "visited"], "The third conditional uses would have + past participle in the result clause."),
        ("If you heat ice, it ___. (melt)", "melts", ["will melt", "would melt", "melted"], "A general truth uses the zero conditional: present simple in both clauses."),
        ("If we finish early, we ___ you. (call)", "will call", ["would call", "called", "would have called"], "A real future possibility uses if + present simple and will + base verb."),
        ("If I were in your position, I ___ the offer. (accept)", "would accept", ["will accept", "accepted", "would have accepted"], "The second conditional uses if + past simple and would + base verb."),
        ("If she had saved more, she ___ a car. (buy)", "would have bought", ["will buy", "would buy", "bought"], "The third conditional uses if + past perfect and would have + past participle."),
        ("If plants do not get water, they ___. (die)", "die", ["will die", "would die", "died"], "A general fact uses the zero conditional."),
        ("If the bus is late, we ___ a taxi. (take)", "will take", ["would take", "took", "would have taken"], "A real future possibility uses if + present simple and will + base verb."),
    ]
    prompt, answer, wrong, rule = records[i % len(records)]
    add("english", "en", difficulty, "Conditionals", prompt, answer, wrong,
        f"🧩 Identify whether the sentence describes a fact, a real future possibility, or an unreal condition.\n🧮 {rule}")


def _english_reported(i: int) -> None:
    records = [
        ("“I am tired,” she said. → She said that she ___ tired.", "was", ["is", "has been", "will be"], "In reported speech after a past reporting verb, present simple commonly shifts back to past simple."),
        ("“We have finished,” they said. → They said that they ___ finished.", "had", ["have", "will have", "were"], "Present perfect shifts back to past perfect in standard reported speech."),
        ("“I can swim,” he said. → He said that he ___ swim.", "could", ["can", "may", "will"], "The modal “can” usually shifts to “could” after a past reporting verb."),
        ("“I will call,” she said. → She said that she ___ call.", "would", ["will", "can", "had"], "The modal “will” shifts to “would” in reported speech."),
        ("“I saw him,” Tom said. → Tom said that he ___ him.", "had seen", ["has seen", "saw", "would see"], "Past simple commonly shifts to past perfect in reported speech."),
        ("“We are working,” they said. → They said that they ___ working.", "were", ["are", "have been", "will be"], "Present continuous shifts back to past continuous."),
    ]
    prompt, answer, wrong, rule = records[i % len(records)]
    add("english", "en", "hard", "Reported speech", prompt, answer, wrong,
        f"🧩 The reporting verb “said” is in the past, so the tense usually moves one step back.\n🧮 {rule}")


def _english_relative(i: int) -> None:
    records = [
        ("The scientist ___ discovered the vaccine won an award.", "who", ["which", "whose", "where"], "Use “who” for a person acting as the subject of a relative clause."),
        ("This is the house ___ my grandmother was born.", "where", ["which", "who", "whose"], "Use “where” to refer to a place."),
        ("The book, ___ I borrowed yesterday, is fascinating.", "which", ["who", "where", "whose"], "Use “which” for a thing in a non-defining relative clause."),
        ("The student ___ essay won the prize thanked her teacher.", "whose", ["who", "which", "where"], "Use “whose” to show possession."),
        ("The day ___ we first met was rainy.", "when", ["where", "who", "whose"], "Use “when” to refer to a time."),
        ("The colleague to ___ I spoke was very helpful.", "whom", ["who", "which", "whose"], "After a preposition in formal English, use the object form “whom” for a person."),
    ]
    prompt, answer, wrong, rule = records[i % 6]
    add("english", "en", "hard", "Relative clauses", prompt, answer, wrong,
        f"🧩 Identify whether the missing word refers to a person, place, time, thing, or possession.\n🧮 {rule}")


def _english_phrasal(i: int) -> None:
    records = [
        ("Please ___ the lights before you leave. (switch off)", "turn off", ["turn up", "turn into", "turn over"], "“Turn off” means to stop a device or light."),
        ("I ___ an old friend at the station yesterday.", "ran into", ["ran over", "ran out", "ran away"], "“Run into” means to meet someone unexpectedly."),
        ("The meeting was ___ until Friday.", "put off", ["put on", "put up", "put out"], "“Put off” means to postpone."),
        ("Could you ___ this word in a dictionary?", "look up", ["look after", "look into", "look down"], "“Look up” means to search for information."),
        ("She ___ her younger brother after school.", "looks after", ["looks up", "looks into", "looks for"], "“Look after” means to take care of someone."),
        ("We have ___ sugar, so we need to buy some.", "run out of", ["run into", "run over", "run away"], "“Run out of” means to have none left."),
    ]
    prompt, answer, wrong, rule = records[i % 6]
    add("english", "en", "hard", "Phrasal verbs", prompt, answer, wrong,
        f"🧩 Interpret the whole verb + particle combination in context.\n🧮 {rule}")


def _english_inversion(i: int) -> None:
    records = [
        ("Rarely ___ such a beautiful performance.", "have I seen", ["I have seen", "did I saw", "I saw"], "A negative adverb at the beginning triggers subject–auxiliary inversion; present perfect uses “have I seen”."),
        ("Not only ___ the exam, but she also won a prize.", "did she pass", ["she passed", "passed she", "has she pass"], "“Not only” at the beginning of a clause triggers inversion; use did + subject + base verb."),
        ("Only after the meeting ___ the mistake.", "did we notice", ["we noticed", "noticed we", "we did noticed"], "“Only after” at the beginning triggers inversion in the main clause."),
        ("Never ___ such a difficult puzzle before.", "had they solved", ["they had solved", "did they solved", "they solve"], "“Never” at the beginning requires inversion; the past perfect is had + participle."),
        ("Under no circumstances ___ this door.", "should you open", ["you should open", "open you", "you open"], "A negative limiting phrase at the beginning triggers inversion."),
        ("Hardly ___ home when it began to snow.", "had we arrived", ["we had arrived", "did we arrived", "we arrive"], "“Hardly … when” takes inversion and commonly uses past perfect."),
    ]
    prompt, answer, wrong, rule = records[i % 6]
    add("english", "en", "hard", "Inversion", prompt, answer, wrong,
        f"🧩 The sentence begins with a restrictive or negative expression.\n🧮 {rule}")


def _english_vocab(i: int) -> None:
    records = [
        ("The instructions were so ___ that nobody misunderstood them.", "clear", ["scarce", "narrow", "rough"], "“Clear” means easy to understand."),
        ("The committee will ___ the proposal before voting.", "evaluate", ["evaporate", "imitate", "hesitate"], "“Evaluate” means to assess or judge."),
        ("The medication had an ___ effect, so the patient recovered quickly.", "immediate", ["identical", "ordinary", "distant"], "“Immediate” means happening without delay."),
        ("Although the evidence was ___, the jury reached a decision.", "limited", ["limitless", "literal", "liable"], "“Limited” means restricted in amount."),
        ("The two reports ___ each other on the main point.", "contradict", ["contribute", "convince", "construct"], "“Contradict” means to state the opposite of something."),
        ("The old building was carefully ___ to preserve its history.", "restored", ["rejected", "reduced", "repeated"], "“Restored” means repaired and returned to a former condition."),
    ]
    prompt, answer, wrong, rule = records[i % 6]
    add("english", "en", "hard", "Vocabulary in context", prompt, answer, wrong,
        f"🧩 Use the surrounding clause to infer the required meaning.\n🧮 {rule}")


def iq_questions() -> None:
    subject, language = "iq", "ru"
    easy = [
        ("Последовательности", "Какое число следующее: 2, 4, 6, 8, …?", "10", ["9", "12", "16"], "🧩 Каждый раз прибавляется 2.\n🧮 8 + 2 = 10."),
        ("Последовательности", "Какое число следующее: 5, 10, 15, 20, …?", "25", ["22", "24", "30"], "🧩 Разность соседних чисел равна 5.\n🧮 20 + 5 = 25."),
        ("Аналогии", "Книга относится к чтению так же, как вилка к …", "еде", ["письму", "одежде", "рисованию"], "🧩 Книга — инструмент для чтения.\n🧮 Вилка — инструмент для еды."),
        ("Лишнее слово", "Какое слово лишнее: круг, квадрат, треугольник, яблоко?", "яблоко", ["круг", "квадрат", "треугольник"], "🧩 Три слова обозначают геометрические фигуры.\n🧮 Яблоко — фрукт, поэтому оно лишнее."),
        ("Счёт", "У Маши 3 пары носков. Сколько это отдельных носков?", "6", ["3", "5", "9"], "🧩 В одной паре два носка.\n🧮 3 × 2 = 6 носков."),
        ("Последовательности", "Какое число следующее: 1, 3, 5, 7, …?", "9", ["8", "10", "11"], "🧩 Это последовательность нечётных чисел с шагом 2.\n🧮 7 + 2 = 9."),
        ("Сравнение", "Али выше Бора, а Бор выше Вали. Кто самый низкий?", "Валя", ["Али", "Бор", "Нельзя определить"], "🧩 Порядок роста: Али > Бор > Валя.\n🧮 Самая низкая — Валя."),
        ("Время", "Сейчас 3 часа дня. Какое время будет через 4 часа?", "7 часов вечера", ["6 часов вечера", "8 часов вечера", "7 часов утра"], "🧩 Прибавляем 4 часа к 3 часам дня.\n🧮 Получаем 7 часов вечера."),
        ("Счёт", "На столе 4 красных и 2 синих карандаша. Сколько всего карандашей?", "6", ["2", "4", "8"], "🧩 Складываем количество карандашей двух цветов.\n🧮 4 + 2 = 6."),
        ("Буквенные ряды", "Какая буква следующая: A, B, C, D, …?", "E", ["F", "G", "A"], "🧩 Буквы идут в алфавитном порядке.\n🧮 После D идёт E."),
    ]
    for topic, prompt, answer, wrong, explanation in easy:
        add(subject, language, "easy", topic, prompt, answer, wrong, explanation)

    medium: list[Callable[[int], None]] = [
        lambda i: _iq_arithmetic(i, False),
        lambda i: _iq_geometric(i, False),
        lambda i: _iq_alternating(i),
        lambda i: _iq_squares(i, False),
        lambda i: _iq_letters(i, False),
        lambda i: _iq_logic(i, False),
        lambda i: _iq_order(i, False),
        lambda i: _iq_analogy(i, False),
        lambda i: _iq_operations(i, False),
        lambda i: _iq_calendar(i),
    ]
    for family in medium:
        for i in range(3):
            family(i)
    hard: list[Callable[[int], None]] = [
        lambda i: _iq_arithmetic(i + 3, True),
        lambda i: _iq_geometric(i + 3, True),
        lambda i: _iq_alternating(i + 3),
        lambda i: _iq_squares(i + 3, True),
        lambda i: _iq_letters(i + 3, True),
        lambda i: _iq_logic(i + 3, True),
        lambda i: _iq_order(i + 3, True),
        lambda i: _iq_analogy(i + 3, True),
        lambda i: _iq_operations(i + 3, True),
        lambda i: _iq_counter(i),
    ]
    for family in hard:
        for i in range(6):
            family(i)


def _iq_arithmetic(i: int, hard: bool) -> None:
    start, step, second = 3 + i, 4 + i, 2 + i % 4
    terms = [start]
    for _ in range(3):
        terms.append(terms[-1] + step)
        step += second
    next_diff = step
    answer = terms[-1] + next_diff
    add("iq", "ru", "hard" if hard else "medium", "Числовые последовательности",
        f"Найдите следующее число: {', '.join(map(str, terms))}, …",
        str(answer), [str(terms[-1]+second), str(answer+second), str(terms[-1]*2)],
        f"🧩 Разности: {terms[1]-terms[0]}, {terms[2]-terms[1]}, {terms[3]-terms[2]} — они увеличиваются на {second}.\n"
        f"🧮 Следующая разность {next_diff}, значит {terms[-1]} + {next_diff} = {answer}.")


def _iq_geometric(i: int, hard: bool) -> None:
    first, ratio = 2 + i % 5, 2 + i % 3
    seq = [first * ratio**n for n in range(4)]
    answer = seq[-1] * ratio
    add("iq", "ru", "hard" if hard else "medium", "Геометрические последовательности",
        f"Какое число продолжает ряд: {', '.join(map(str, seq))}, …?",
        str(answer), [str(seq[-1]+ratio), str(seq[-1]*2), str(seq[-1]+first)],
        f"🧩 Каждый член умножается на {ratio}: {seq[1]} ÷ {seq[0]} = {ratio}.\n"
        f"🧮 Следующий член: {seq[-1]} × {ratio} = {answer}.")


def _iq_alternating(i: int) -> None:
    a, b, inc = 2+i, 10+2*i, 2+i%4
    seq = [a, b, a+inc, b+inc, a+2*inc, b+2*inc]
    answer = a+3*inc
    add("iq", "ru", "hard" if i >= 3 else "medium", "Чередующиеся ряды",
        f"Найдите следующее число: {', '.join(map(str, seq))}, …",
        str(answer), [str(b+3*inc), str(seq[-1]+inc), str(answer+inc)],
        f"🧩 Здесь переплетены два ряда: {a}, {a+inc}, {a+2*inc} и {b}, {b+inc}, {b+2*inc}.\n"
        f"🧮 Продолжаем первый ряд: {a+2*inc} + {inc} = {answer}.")


def _iq_squares(i: int, hard: bool) -> None:
    n = 2 + i
    seq = [k*k for k in range(n, n+4)]
    answer = (n+4)**2
    add("iq", "ru", "hard" if hard else "medium", "Квадраты",
        f"Какое число следующее: {', '.join(map(str, seq))}, …?",
        str(answer), [str(answer+1), str((n+3)*(n+4)), str(seq[-1]+4)],
        f"🧩 Члены ряда — квадраты последовательных чисел: {n}², {n+1}², {n+2}², {n+3}².\n"
        f"🧮 Следующий член — {n+4}² = {answer}.")


def _iq_letters(i: int, hard: bool) -> None:
    start, step = i % 5, 2 + i % 3
    seq = [chr(65 + start + k*step) for k in range(4)]
    answer = chr(65 + start + 4*step)
    add("iq", "ru", "hard" if hard else "medium", "Буквенные последовательности",
        f"Какая буква продолжает ряд: {', '.join(seq)}, …?",
        answer, [chr(ord(answer)+1), chr(ord(answer)-1), seq[-1]],
        f"🧩 Позиции букв в английском алфавите увеличиваются на {step}.\n"
        f"🧮 После {seq[-1]} пропускаем ещё {step-1} букв и получаем {answer}.")


def _iq_logic(i: int, hard: bool) -> None:
    cases = [
        (["Все лиры — моры.", "Ни один мор не является тевом."], "Ни одна лира не является тевом.", "Некоторые лиры — тевы.", "Все тевы — лиры.", "Нельзя определить.", "Все лиры входят в множество моров, а моры не пересекаются с тевами."),
        (["Все врачи имеют образование.", "Некоторые исследователи — врачи."], "Некоторые исследователи имеют образование.", "Все исследователи — врачи.", "Ни один исследователь не образован.", "Нельзя определить.", "Некоторые исследователи являются врачами, а значит, имеют образование."),
        (["Ни один квадрат не является кругом.", "Фигура X — квадрат."], "Фигура X не является кругом.", "Фигура X — круг.", "Все круги — квадраты.", "Нельзя определить.", "X принадлежит классу квадратов, который не пересекается с классом кругов."),
        (["Все А относятся к Б.", "Все Б относятся к В."], "Все А относятся к В.", "Все В относятся к А.", "Ни одно А не относится к В.", "Нельзя определить.", "Принадлежность к А означает принадлежность к Б, а значит и к В."),
        (["Некоторые музыканты — преподаватели.", "Все преподаватели умеют объяснять."], "Некоторые музыканты умеют объяснять.", "Все музыканты — преподаватели.", "Ни один музыкант не умеет объяснять.", "Нельзя определить.", "Те музыканты, которые являются преподавателями, умеют объяснять."),
        (["Все зелы — раны.", "Ни один ран не является силом."], "Ни один зел не является силом.", "Некоторые зели — силы.", "Все силы — зелы.", "Нельзя определить.", "Зели входят в множество ранов, которое не пересекается с множеством силов."),
        (["Все пилоты проходят обучение.", "Все прошедшие обучение сдают экзамен."], "Все пилоты сдают экзамен.", "Все сдавшие экзамен — пилоты.", "Ни один пилот не сдаёт экзамен.", "Нельзя определить.", "Каждый пилот проходит обучение, а каждый прошедший обучение сдаёт экзамен."),
        (["Некоторые художники — архитекторы.", "Ни один архитектор не работает без чертежей."], "Некоторые художники не работают без чертежей.", "Все художники — архитекторы.", "Некоторые архитекторы работают без чертежей.", "Нельзя определить.", "Художники, которые являются архитекторами, не работают без чертежей."),
        (["Все маяки заметны ночью.", "Объект X — маяк."], "Объект X заметен ночью.", "Объект X заметен только ночью.", "Все заметные ночью объекты — маяки.", "Нельзя определить.", "X является маяком, а каждый маяк заметен ночью."),
        (["Ни один металл не является прозрачным.", "Некоторые материалы прозрачны."], "Некоторые материалы не являются металлами.", "Все материалы — металлы.", "Некоторые металлы прозрачны.", "Нельзя определить.", "Прозрачные материалы не могут быть металлами, поэтому некоторые материалы не металлы."),
        (["Все участники получили номер.", "Ира — участник."], "Ира получила номер.", "Все получившие номер — участники.", "Ира не получила номер.", "Нельзя определить.", "Ира принадлежит группе участников, каждому из которых выдали номер."),
        (["Некоторые книги — словари.", "Все словари содержат определения."], "Некоторые книги содержат определения.", "Все книги содержат определения.", "Ни одна книга не содержит определений.", "Нельзя определить.", "Книги, являющиеся словарями, содержат определения."),
    ]
    premises, answer, w1, w2, w3, rule = cases[i % len(cases)]
    add("iq", "ru", "hard" if hard else "medium", "Логические выводы",
        f"{' '.join(premises)} Какой вывод обязательно верен?",
        answer, [w1, w2, w3],
        f"🧩 Используем только данные посылки; не добавляем предположений.\n🧮 {rule}")


def _iq_order(i: int, hard: bool) -> None:
    names = ["Али", "Бек", "Вали", "Дина", "Егор", "Лола", "Малика", "Тимур", "Нодир", "Сара", "Азиз"]
    a, b, c = names[i], names[i+1], names[i+2]
    # The clues define a strict chain; rotate names to produce different instances.
    add("iq", "ru", "hard" if hard else "medium", "Порядок и сравнение",
        f"{a} старше {b}. {b} старше {c}. Кто младше всех из этих троих?",
        c, [a, b, "Недостаточно данных"],
        f"🧩 Из условий получаем цепочку: {a} старше {b}, а {b} старше {c}.\n"
        f"🧮 Следовательно, младше всех {c}.")


def _iq_analogy(i: int, hard: bool) -> None:
    cases = [
        ("птица", "гнездо", "пчела", "улей", ["мёд", "крыло", "цветок"], "Птица живёт в гнезде; пчёлы живут в улье."),
        ("автор", "книга", "композитор", "музыка", ["оркестр", "нота", "сцена"], "Автор создаёт книгу; композитор создаёт музыку."),
        ("термометр", "температура", "барометр", "давление", ["скорость", "расстояние", "масса"], "Термометр измеряет температуру; барометр измеряет давление."),
        ("семя", "растение", "яйцо", "птица", ["гнездо", "перо", "клюв"], "Из семени развивается растение; из яйца может развиться птица."),
        ("врач", "пациент", "учитель", "ученик", ["книга", "школа", "урок"], "Врач оказывает помощь пациенту; учитель обучает ученика."),
        ("секунда", "минута", "сантиметр", "метр", ["линейка", "километр", "грамм"], "Минута состоит из секунд; метр состоит из сантиметров."),
        ("ключ", "замок", "пароль", "аккаунт", ["экран", "письмо", "клавиатура"], "Ключ открывает замок; пароль даёт доступ к аккаунту."),
        ("рыба", "вода", "птица", "воздух", ["лес", "гнездо", "земля"], "Рыба передвигается в воде; птица передвигается в воздухе."),
        ("термометр", "температура", "весы", "масса", ["высота", "длина", "объём"], "Термометр измеряет температуру; весы измеряют массу."),
        ("слово", "предложение", "кирпич", "стена", ["окно", "крыша", "дверь"], "Слова образуют предложение; кирпичи образуют стену."),
        ("пчела", "мёд", "корова", "молоко", ["трава", "ферма", "сыр"], "Пчёлы производят мёд; коровы дают молоко."),
        ("глаз", "зрение", "ухо", "слух", ["голос", "шум", "музыка"], "Глаз служит для зрения; ухо — для слуха."),
        ("пекарь", "хлеб", "гончар", "горшок", ["глина", "печь", "магазин"], "Пекарь изготавливает хлеб; гончар изготавливает горшки."),
    ]
    a, rel, b, answer, wrong, rule = cases[i % len(cases)]
    add("iq", "ru", "hard" if hard else "medium", "Аналогии",
        f"Завершите аналогию: {a} относится к «{rel}», как {b} относится к …",
        answer, wrong, f"🧩 Определяем связь первой пары и применяем её ко второй.\n🧮 {rule}")


def _iq_operations(i: int, hard: bool) -> None:
    a, b, c = 2+i%7, 3+i%6, 2+i%5
    answer = a + b*c
    add("iq", "ru", "hard" if hard else "medium", "Числовые закономерности",
        f"Если операция ⊙ определена как a ⊙ b = a + b × {c}, чему равно {a} ⊙ {b}?",
        str(answer), [str((a+b)*c), str(a*b+c), str(a+b+c)],
        f"🧩 По правилу ⊙ сначала умножаем второй аргумент на {c}.\n"
        f"🧮 {a} ⊙ {b} = {a} + {b} × {c} = {a} + {b*c} = {answer}.")


def _iq_calendar(i: int) -> None:
    days, shift = 3 + i, 2 + i % 5
    answer = (days + shift - 1) % 7 + 1
    names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    start = names[days-1]
    result = names[answer-1]
    wrong = [names[(answer-2) % 7], names[answer % 7], names[(answer+2) % 7]]
    add("iq", "ru", "medium", "Календарная логика",
        f"Сегодня {start}. Какой день недели будет через {shift} дней?",
        result, wrong,
        f"🧩 Дни недели повторяются циклом из 7 дней.\n"
        f"🧮 Сдвигаемся на {shift} позиций вперёд от {start}: получаем {result}.")


def _iq_counter(i: int) -> None:
    # Each step adds the next even number: n² increments by 2n+1.
    n = 3 + i
    seq = [k*k for k in range(1, n+1)]
    answer = (n+1)**2
    add("iq", "ru", "hard", "Закономерности и разности",
        f"Найдите следующее число: {', '.join(map(str, seq))}, …",
        str(answer), [str(answer+2), str(seq[-1]+n), str(n*(n+1))],
        f"🧩 Разности между квадратами увеличиваются на 2: 3, 5, 7, …\n"
        f"🧮 Следующая разность {2*n+1}; {seq[-1]} + {2*n+1} = {answer}.")


def math_mock_extras() -> None:
    for i in range(10):
        a, x, divisor = 2 + i % 5, 3 + i, 2 + i % 4
        remainder = (divisor - (a*x) % divisor) % divisor
        numerator = a*x + remainder
        result = numerator // divisor
        add("mathematics", "ru", "hard", "Дробно-рациональные уравнения",
            f"Решите уравнение: ({a}x + {remainder})/{divisor} = {result}.",
            str(x), [str(x+1), str(x-1), str(-x)],
            f"🧩 Умножаем обе части на {divisor}: {a}x + {remainder} = {numerator}.\n"
            f"🧮 Вычитаем {remainder}, затем делим на {a}: x = {x}.")


def english_mock_extras() -> None:
    items = [
        ("If she had accepted the offer, she ___ in London now.", "would be living",
         ["would have lived", "will live", "lived"],
         "🧩 The condition refers to an unreal past; the result refers to the present.\n🧮 This mixed conditional uses past perfect in the if-clause and “would be + -ing” in the result."),
        ("No sooner ___ than the lights went out.", "had we arrived",
         ["we had arrived", "did we arrive", "we arrived"],
         "🧩 “No sooner” at the beginning requires subject–auxiliary inversion.\n🧮 The earlier past action uses past perfect: “had we arrived”."),
        ("It is essential that every applicant ___ the form.", "complete",
         ["completes", "completed", "will complete"],
         "🧩 After expressions of necessity, formal English uses the mandative subjunctive.\n🧮 The subjunctive uses the base form “complete”."),
        ("Having ___ the data, the researchers published their findings.", "analysed",
         ["analysing", "analyse", "been analyse"],
         "🧩 A perfect participle describes an action completed before the main action.\n🧮 Use “having” + past participle: “having analysed”."),
        ("I would rather you ___ the details with anyone.", "did not share",
         ["do not share", "will not share", "had not shared"],
         "🧩 “Would rather” + a different subject is followed by a past-tense form for a present preference.\n🧮 The correct form is “did not share”."),
        ("Despite ___ exhausted, she completed the presentation.", "being",
         ["was", "be", "to be"],
         "🧩 “Despite” is a preposition and is followed by a noun or gerund.\n🧮 Use the gerund “being”."),
        ("Each of the proposals ___ carefully considered.", "has been",
         ["have been", "are", "were"],
         "🧩 “Each” is grammatically singular.\n🧮 The singular present perfect passive is “has been considered”."),
        ("They must have ___ the wrong address.", "been given",
         ["gave", "giving", "being gave"],
         "🧩 A modal perfect uses modal + have + past participle; the passive adds “been”.\n🧮 The correct form is “must have been given”."),
        ("The proposal, ___ by the board, will take effect in June.", "having been approved",
         ["having approved", "has been approving", "approved it"],
         "🧩 The proposal receives the action, so the participle clause must be passive.\n🧮 The prior completed action is “having been approved”."),
        ("Not until the final chapter ___ the motive.", "does the reader discover",
         ["the reader discovers", "the reader does discover", "discovered the reader"],
         "🧩 A fronted “Not until” phrase triggers inversion in the main clause.\n🧮 Use auxiliary + subject + base verb: “does the reader discover”."),
    ]
    for prompt, answer, wrong, explanation in items:
        add("english", "en", "hard", "Advanced grammar", prompt, answer, wrong, explanation)


def iq_mock_extras() -> None:
    for i in range(10):
        first = 3 + i
        step = 2 + i % 5
        terms = [first]
        difference = step
        for _ in range(3):
            terms.append(terms[-1] + difference)
            difference += 2
        answer = terms[-1] + difference
        add("iq", "ru", "hard", "Ряды с возрастающей разностью",
            f"Найдите следующее число: {', '.join(map(str, terms))}, …",
            str(answer), [str(terms[-1]+step), str(answer+2), str(terms[-1]*2)],
            f"🧩 Разности увеличиваются на 2: {step}, {step+2}, {step+4}.\n"
            f"🧮 Следующая разность {difference}; {terms[-1]} + {difference} = {answer}.")


math_questions()
english_questions()
iq_questions()

expected = {
    ("mathematics", "easy"): 10, ("mathematics", "medium"): 30, ("mathematics", "hard"): 60,
    ("english", "easy"): 10, ("english", "medium"): 30, ("english", "hard"): 60,
    ("iq", "easy"): 10, ("iq", "medium"): 30, ("iq", "hard"): 60,
}
actual = {
    (subject, difficulty): sum(
        q["subject"] == subject and q["difficulty"] == difficulty for q in questions
    )
    for subject, difficulty in expected
}
if actual != expected or len(questions) != 300:
    raise RuntimeError(f"Question bank count mismatch: {actual}")

(ROOT / "questions.json").write_text(
    json.dumps(questions, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

mock_bank: dict[str, list[dict]] = {}
for subject in ("english", "mathematics", "iq"):
    items = [question for question in questions if question["subject"] == subject]
    extras_start = len(questions)
    if subject == "english":
        english_mock_extras()
    elif subject == "mathematics":
        math_mock_extras()
    else:
        iq_mock_extras()
    extras = questions[extras_start:]
    del questions[extras_start:]
    items = [question for question in items if question["difficulty"] != "easy"] + extras
    items.sort(key=lambda question: {"hard": 0, "medium": 1, "easy": 2}[question["difficulty"]])
    if len(items) != 100 or len({question["question_text"] for question in items}) != 100:
        raise RuntimeError(f"Static mock for {subject} must contain 100 unique questions")
    mock_bank[subject] = [
        {**question, "id": -(index + 1)}
        for index, question in enumerate(items)
    ]

(ROOT / "static_mocks.json").write_text(
    json.dumps(mock_bank, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
