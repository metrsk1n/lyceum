from __future__ import annotations

import re


TOPICS_UZ = {
    "Арифметика": "Arifmetika",
    "Линейные уравнения": "Chiziqli tenglamalar",
    "Дроби": "Kasrlar",
    "Проценты": "Foizlar",
    "Геометрия": "Geometriya",
    "Пропорции": "Nisbatlar",
    "Последовательности": "Ketma-ketliklar",
    "Среднее арифметическое": "O‘rta arifmetik",
    "Вероятность": "Ehtimollik",
    "Разложение на множители": "Ko‘paytuvchilarga ajratish",
    "Движение": "Harakat",
    "Квадратные уравнения": "Kvadrat tenglamalar",
    "Системы уравнений": "Tenglamalar sistemasi",
    "Степени": "Darajalar",
    "Совместная работа": "Birgalikdagi ish",
    "Неравенства": "Tengsizliklar",
    "Аналогии": "Analogiyalar",
    "Лишнее слово": "Ortiqcha so‘z",
    "Счёт": "Hisoblash",
    "Сравнение": "Taqqoslash",
    "Время": "Vaqt",
    "Буквенные ряды": "Harfli qatorlar",
    "Числовые последовательности": "Sonli ketma-ketliklar",
    "Геометрические последовательности": "Geometrik ketma-ketliklar",
    "Чередующиеся ряды": "Almashinuvchi qatorlar",
    "Квадраты": "Kvadratlar",
    "Буквенные последовательности": "Harfli ketma-ketliklar",
    "Логические выводы": "Mantiqiy xulosalar",
    "Порядок и сравнение": "Tartib va taqqoslash",
    "Числовые закономерности": "Sonli qonuniyatlar",
    "Календарная логика": "Taqvim mantiqi",
    "Закономерности и разности": "Qonuniyatlar va ayirmalar",
    "Ряды с возрастающей разностью": "Ayirmasi ortib boruvchi qatorlar",
    "Дробно-рациональные уравнения": "Kasr-ratsional tenglamalar",
    "Grammar and vocabulary": "Grammatika va lug‘at",
    "Verb tenses": "Fe’l zamonlari",
    "Articles": "Artikllar",
    "Comparatives": "Qiyosiy daraja",
    "Prepositions": "Predloglar",
    "Modal verbs": "Modal fe’llar",
    "Connectors": "Bog‘lovchilar",
    "Quantifiers": "Miqdor bildiruvchi so‘zlar",
    "Word formation": "So‘z yasalishi",
    "Passive voice": "Majhul nisbat",
    "Conditionals": "Shart gaplar",
    "Reported speech": "O‘zlashtirma gap",
    "Relative clauses": "Ergash gaplar",
    "Phrasal verbs": "Frazali fe’llar",
    "Inversion": "Inversiya",
    "Vocabulary": "Lug‘at",
    "Vocabulary in context": "Kontekstdagi lug‘at",
    "Linking words": "Bog‘lovchi so‘zlar",
    "Advanced grammar": "Murakkab grammatika",
}


_RU_WORDS = {
    "Али": "Ali", "Бек": "Bek", "Вали": "Vali", "Валя": "Vali",
    "Бор": "Bor",
    "Дина": "Dina", "Егор": "Yegor", "Лола": "Lola", "Малика": "Malika",
    "Тимур": "Temur", "Нодир": "Nodir", "Сара": "Sara", "Азиз": "Aziz",
    "Ира": "Ira", "Маша": "Masha",
    "книга": "kitob", "книгу": "kitobni", "чтения": "o‘qish",
    "вилка": "sanchqi", "еде": "ovqatlanish", "письму": "yozish",
    "одежде": "kiyim", "рисованию": "rasm chizish",
    "яблоко": "olma", "круг": "doira", "квадрат": "kvadrat",
    "треугольник": "uchburchak", "носков": "paypoq", "носок": "paypoq",
    "птица": "qush", "пчела": "asalari", "пчёлы": "asalarilar",
    "гнездо": "uya", "улей": "asalari uyasi", "мёд": "asal",
    "крыло": "qanot", "цветок": "gul", "автор": "muallif",
    "композитор": "bastakor", "музыка": "musiqa", "оркестр": "orkestr",
    "нота": "nota", "сцена": "sahna", "термометр": "termometr",
    "температура": "harorat", "барометр": "barometr", "давление": "bosim",
    "скорость": "tezlik", "расстояние": "masofa", "масса": "massa",
    "семя": "urug‘", "растение": "o‘simlik", "яйцо": "tuxum",
    "врач": "shifokor", "пациент": "bemor", "учитель": "o‘qituvchi",
    "ученик": "o‘quvchi", "книга": "kitob", "школа": "maktab",
    "урок": "dars", "секунда": "soniya", "минута": "daqiqa",
    "сантиметр": "santimetr", "метр": "metr", "линейка": "chizg‘ich",
    "километр": "kilometr", "грамм": "gramm", "аккаунт": "hisob",
    "вода": "suv", "воздух": "havo", "понедельник": "dushanba",
    "вторник": "seshanba", "среда": "chorshanba", "четверг": "payshanba",
    "пятница": "juma", "суббота": "shanba", "воскресенье": "yakshanba",
    "высота": "balandlik", "длина": "uzunlik", "земля": "yer",
    "клавиатура": "klaviatura", "клюв": "tumshuq", "лес": "o‘rmon",
    "объём": "hajm", "перо": "pat", "письмо": "xat", "экран": "ekran",
    "весы": "tarozi",
    "ключ": "kalit", "замок": "qulf", "пароль": "parol", "рыба": "baliq",
    "утра": "ertalab", "вечера": "kechqurun",
    "Нельзя определить": "Aniqlab bo‘lmaydi",
    "Недостаточно данных": "Ma’lumot yetarli emas",
    "это": "bu",
}


_RU_PHRASES = (
    ("✅ Ответ:", "✅ Javob:"),
    ("Найдите следующий член последовательности:", "Ketma-ketlikning keyingi hadini toping:"),
    ("Решите уравнение:", "Tenglamani yeching:"),
    ("Упростите выражение", "Ifodani soddalashtiring"),
    ("Вычислите:", "Hisoblang:"),
    ("Какое число следующее:", "Keyingi sonni toping:"),
    ("Найдите следующее число:", "Keyingi sonni toping:"),
    ("Какое число продолжает ряд:", "Qatorni davom ettiruvchi sonni toping:"),
    ("Какая буква продолжает ряд:", "Qatorni davom ettiruvchi harfni toping:"),
    ("Какая буква следующая:", "Keyingi harfni toping:"),
    ("Найдите площадь", "Yuzani toping"),
    ("Найдите среднее арифметическое", "O‘rta arifmetik qiymatni toping"),
    ("Найдите меньший корень уравнения", "Tenglamaning kichik ildizini toping:"),
    ("Найдите x + y, если", "x + y ni toping, agar"),
    ("Найдите следующий член", "Keyingi hadni toping"),
    ("Найдите", "Toping"),
    ("Какое значение имеет выражение", "Ifodaning qiymatini toping"),
    ("🧩 Книга — инструмент для чтения.", "🧩 Kitob o‘qish vositasidir."),
    ("🧮 Вилка — инструмент для еды.", "🧮 Sanchqi ovqatlanish uchun ishlatiladi."),
    ("🧩 Порядок роста: Али > Бор > Валя.", "🧩 Bo‘ylar tartibi: Ali > Bor > Vali."),
    ("🧮 Самая низкая — Валя.", "🧮 Eng past bo‘yli — Vali."),
    ("🧮 Птица живёт в гнезде; пчёлы живут в улье.", "🧮 Qush uyada, asalarilar esa uyada yashaydi."),
    ("🧮 Автор создаёт книгу; композитор создаёт музыку.", "🧮 Muallif kitob, bastakor esa musiqa yaratadi."),
    ("🧮 Термометр измеряет температуру; барометр измеряет давление.", "🧮 Termometr haroratni, barometr esa bosimni o‘lchaydi."),
    ("🧮 Принадлежность к А означает принадлежность к Б, а значит и к В.", "🧮 A ga tegishlilik B ga, demak V ga ham tegishlilikni anglatadi."),
    ("🧮 Те музыканты, которые являются преподавателями, умеют объяснять.", "🧮 O‘qituvchi bo‘lgan musiqachilar tushuntira oladi."),
    ("🧮 Зели входят в множество ранов, которое не пересекается с множеством силов.", "🧮 Zelilar ranlar to‘plamiga kiradi, ranlar to‘plami esa sillar to‘plami bilan kesishmaydi."),
    ("🧮 Каждый пилот проходит обучение, а каждый прошедший обучение сдаёт экзамен.", "🧮 Har bir uchuvchi tayyorgarlikdan o‘tadi va tayyorgarlikdan o‘tgan har bir kishi imtihon topshiradi."),
    ("🧮 Художники, которые являются архитекторами, не работают без чертежей.", "🧮 Me’mor bo‘lgan rassomlar chizmalarsiz ishlamaydi."),
    ("🧮 X является маяком, а каждый маяк заметен ночью.", "🧮 X mayoq hisoblanadi va har bir mayoq tunda ko‘rinadi."),
    ("🧮 Из семени развивается растение; из яйца может развиться птица.", "🧮 Urug‘dan o‘simlik, tuxumdan esa qush rivojlanishi mumkin."),
    ("🧮 Врач оказывает помощь пациенту; учитель обучает ученика.", "🧮 Shifokor bemorga yordam beradi, o‘qituvchi esa o‘quvchiga ta’lim beradi."),
    ("🧮 Минута состоит из секунд; метр состоит из сантиметров.", "🧮 Daqiqa soniyalardan, metr esa santimetrlardan tashkil topadi."),
    ("🧮 Ключ открывает замок; пароль даёт доступ к аккаунту.", "🧮 Kalit qulfni ochadi, parol esa hisobga kirish imkonini beradi."),
    ("🧮 Рыба передвигается в воде; птица передвигается в воздухе.", "🧮 Baliq suvda, qush esa havoda harakatlanadi."),
    ("🧮 Термометр измеряет температуру; весы измеряют массу.", "🧮 Termometr haroratni, tarozi esa massani o‘lchaydi."),
    ("Какова вероятность", "Ehtimollikni toping"),
    ("Какой вывод обязательно верен?", "Qaysi xulosa albatta to‘g‘ri?"),
    ("Какой вывод обязательно верен", "Qaysi xulosa albatta to‘g‘ri"),
    ("Кто младше всех из этих троих?", "Bu uch kishidan eng kichigi kim?"),
    ("Завершите аналогию:", "O‘xshatishni davom ettiring:"),
    ("Если операция", "Agar amal"),
    ("Сегодня", "Bugun"),
    ("Какой день недели будет через", "… kundan keyin haftaning qaysi kuni bo‘ladi"),
    ("Какое слово лишнее:", "Qaysi so‘z ortiqcha:"),
    ("У Маши", "Mashada"),
    ("Сколько это отдельных носков?", "Bu nechta dona paypoq bo‘ladi?"),
    ("Книга относится к чтению так же, как вилка к …", "Kitob o‘qish bilan qanday bog‘liq bo‘lsa, sanchqi ham … bilan shunday bog‘liq."),
    ("Число ", "Son "),
    (" разделили в отношении ", " nisbati bo‘yicha bo‘lindi. "),
    ("Чему равна меньшая часть?", "Kichik qismni toping."),
    ("Найдите следующий член последовательности", "Ketma-ketlikning keyingi hadini toping"),
    ("Найдите среднее арифметическое чисел", "Sonlarning o‘rta arifmetik qiymatini toping"),
    ("В мешке ", "Xaltada "),
    (" красных и ", " ta qizil va "),
    (" синих шаров. Какова вероятность вынуть красный шар?", " ta ko‘k shar bor. Qizil sharni olish ehtimoli qancha?"),
    ("Найдите площадь прямоугольника со сторонами ", "Tomonlari "),
    (" см и ", " sm va "),
    (" см.", " sm bo‘lgan to‘g‘ri to‘rtburchak yuzini toping."),
    ("Найдите следующий член последовательности:", "Ketma-ketlikning keyingi hadini toping:"),
    ("Автомобиль ехал со скоростью ", "Avtomobil "),
    (" км/ч в течение ", " km/soat tezlikda "),
    (" ч. Какой путь он прошёл?", " soat yurdi. U qancha masofani bosib o‘tdi?"),
    ("Радиус круга равен ", "Doira radiusi "),
    (" см. Чему равна площадь круга, если π оставить символом?", " sm. π ni ramz holida qoldirib, doira yuzini toping."),
    ("Первый мастер выполняет работу за ", "Birinchi usta ishni "),
    (" ч, второй — за ", " soatda, ikkinchisi esa "),
    (" ч. За сколько часов они выполнят её вместе?", " soatda bajaradi. Ular ishni birgalikda necha soatda tugatadi?"),
    ("Какое наименьшее целое число x удовлетворяет неравенству", "Tengsizlikni qanoatlantiradigan eng kichik butun x sonini toping"),
    ("Какое число следующее", "Keyingi sonni toping"),
    ("Какое число продолжает", "Davom ettiruvchi sonni toping"),
    ("Сегодня ", "Bugun "),
    (". Какой день недели будет через ", ". "),
    (" дней?", " kundan keyin haftaning qaysi kuni bo‘ladi?"),
    (" часа дня. Какое время будет через ", " kunduzgi soat. "),
    (" часа?", " soatdan keyin soat nechchi bo‘ladi?"),
    ("На столе ", "Stol ustida "),
    (" красных и ", " ta qizil va "),
    (" синих карандаша. Сколько всего карандашей?", " ta ko‘k qalam bor. Jami nechta qalam bor?"),
    ("Али выше Бора, а Бор выше Вали. Кто самый низкий?", "Ali Bekdan, Bek esa Valikdan baland. Eng past bo‘yli kim?"),
    ("относится к", "ga tegishli"),
    ("Найдите следующий член последовательности:", "Ketma-ketlikning keyingi hadini toping:"),
    ("Какой вывод обязательно верен?", "Qaysi xulosa albatta to‘g‘ri?"),
    ("Все лиры — моры.", "Barcha lira mor hisoblanadi."),
    ("Ни один мор не является тевом.", "Hech bir mor teva emas."),
    ("Ни одна лира не является тевом.", "Hech bir lira teva emas."),
    ("Некоторые лиры — тевы.", "Ba’zi liralar teva hisoblanadi."),
    ("Все тевы — лиры.", "Barcha tevalar lira hisoblanadi."),
    ("Все врачи имеют образование.", "Barcha shifokorlar ma’lumotga ega."),
    ("Некоторые исследователи — врачи.", "Ba’zi tadqiqotchilar shifokor."),
    ("Некоторые исследователи имеют образование.", "Ba’zi tadqiqotchilar ma’lumotga ega."),
    ("Все исследователи — врачи.", "Barcha tadqiqotchilar shifokor."),
    ("Ни один исследователь не образован.", "Hech bir tadqiqotchi ma’lumotga ega emas."),
    ("Ни один квадрат не является кругом.", "Hech bir kvadrat doira emas."),
    ("Фигура X — квадрат.", "X shakli kvadrat."),
    ("Фигура X не является кругом.", "X shakli doira emas."),
    ("Фигура X — круг.", "X shakli doira."),
    ("Все круги — квадраты.", "Barcha doiralar kvadrat."),
    ("Все А относятся к Б.", "Barcha A lar B ga tegishli."),
    ("Все Б относятся к В.", "Barcha B lar V ga tegishli."),
    ("Все А относятся к В.", "Barcha A lar V ga tegishli."),
    ("Все В относятся к А.", "Barcha V lar A ga tegishli."),
    ("Ни одно А не относится к В.", "Hech bir A V ga tegishli emas."),
    ("Некоторые музыканты — преподаватели.", "Ba’zi musiqachilar o‘qituvchi."),
    ("Все преподаватели умеют объяснять.", "Barcha o‘qituvchilar tushuntira oladi."),
    ("Некоторые музыканты умеют объяснять.", "Ba’zi musiqachilar tushuntira oladi."),
    ("Все музыканты — преподаватели.", "Barcha musiqachilar o‘qituvchi."),
    ("Ни один музыкант не умеет объяснять.", "Hech bir musiqachi tushuntira olmaydi."),
    ("Все зелы — раны.", "Barcha zel ran hisoblanadi."),
    ("Ни один ран не является силом.", "Hech bir ran sil emas."),
    ("Ни один зел не является силом.", "Hech bir zel sil emas."),
    ("Некоторые зели — силы.", "Ba’zi zelilar sil hisoblanadi."),
    ("Все силы — зелы.", "Barcha sillar zel hisoblanadi."),
    ("Все пилоты проходят обучение.", "Barcha uchuvchilar tayyorgarlikdan o‘tadi."),
    ("Все прошедшие обучение сдают экзамен.", "Tayyorgarlikdan o‘tganlarning barchasi imtihon topshiradi."),
    ("Все пилоты сдают экзамен.", "Barcha uchuvchilar imtihon topshiradi."),
    ("Все сдавшие экзамен — пилоты.", "Imtihon topshirganlarning barchasi uchuvchi."),
    ("Ни один пилот не сдаёт экзамен.", "Hech bir uchuvchi imtihon topshirmaydi."),
    ("Некоторые художники — архитекторы.", "Ba’zi rassomlar me’mor."),
    ("Ни один архитектор не работает без чертежей.", "Hech bir me’mor chizmalarsiz ishlamaydi."),
    ("Некоторые художники не работают без чертежей.", "Ba’zi rassomlar chizmalarsiz ishlamaydi."),
    ("Все художники — архитекторы.", "Barcha rassomlar me’mor."),
    ("Некоторые архитекторы работают без чертежей.", "Ba’zi me’morlar chizmalarsiz ishlaydi."),
    ("Все маяки заметны ночью.", "Barcha mayoqlar tunda ko‘rinadi."),
    ("Объект X — маяк.", "X obyekt mayoq."),
    ("Объект X заметен ночью.", "X obyekt tunda ko‘rinadi."),
    ("Объект X заметен только ночью.", "X obyekt faqat tunda ko‘rinadi."),
    ("Все заметные ночью объекты — маяки.", "Tunda ko‘rinadigan barcha obyektlar mayoq."),
    ("Ни один металл не является прозрачным.", "Hech bir metall shaffof emas."),
    ("Некоторые материалы прозрачны.", "Ba’zi materiallar shaffof."),
    ("Некоторые материалы не являются металлами.", "Ba’zi materiallar metall emas."),
    ("Все материалы — металлы.", "Barcha materiallar metall."),
    ("Некоторые металлы прозрачны.", "Ba’zi metallar shaffof."),
    ("Все участники получили номер.", "Barcha ishtirokchilar raqam oldi."),
    ("Ира — участник.", "Ira ishtirokchi."),
    ("Ира получила номер.", "Ira raqam oldi."),
    ("Все получившие номер — участники.", "Raqam olganlarning barchasi ishtirokchi."),
    ("Ира не получила номер.", "Ira raqam olmadi."),
    ("Некоторые книги — словари.", "Ba’zi kitoblar lug‘at."),
    ("Все словари содержат определения.", "Barcha lug‘atlarda ta’riflar bor."),
    ("Некоторые книги содержат определения.", "Ba’zi kitoblarda ta’riflar bor."),
    ("Все книги содержат определения.", "Barcha kitoblarda ta’riflar bor."),
    ("Ни одна книга не содержит определений.", "Hech bir kitobda ta’rif yo‘q."),
    ("Какое значение имеет выражение", "Ifodaning qiymatini toping"),
    ("Все лиры входят в множество моров, а моры не пересекаются с тевами.",
     "Barcha liralar morlar to‘plamiga kiradi, morlar to‘plami esa tevalar bilan kesishmaydi."),
    ("Некоторые исследователи являются врачами, а значит, имеют образование.",
     "Ba’zi tadqiqotchilar shifokor, demak ular ma’lumotga ega."),
    ("X принадлежит классу квадратов, который не пересекается с классом кругов.",
     "X kvadratlar sinfiga tegishli va bu sinf doiralar sinfi bilan kesishmaydi."),
    ("Принадлежность к А означает принадлежность к Б, а значит и к В.",
     "A ga tegishlilik B ga, demak V ga ham tegishlilikni anglatadi."),
    ("Те музыканты, которые являются преподавателями, умеют объяснять.",
     "O‘qituvchi bo‘lgan musiqachilar tushuntira oladi."),
    ("Зели входят в множество ранов, которое не пересекается с множеством силов.",
     "Zelilar ranlar to‘plamiga kiradi, bu to‘plam sillar to‘plami bilan kesishmaydi."),
    ("Каждый пилот проходит обучение, а каждый прошедший обучение сдаёт экзамен.",
     "Har bir uchuvchi tayyorgarlikdan o‘tadi va tayyorgarlikdan o‘tgan har bir kishi imtihon topshiradi."),
    ("Художники, которые являются архитекторами, не работают без чертежей.",
     "Me’mor bo‘lgan rassomlar chizmalarsiz ishlamaydi."),
    ("X является маяком, а каждый маяк заметен ночью.",
     "X mayoq hisoblanadi va har bir mayoq tunda ko‘rinadi."),
)


_RU_SENTENCES = {
    "🧩 Сначала выполняем умножение:": "🧩 Avval ko‘paytirishni bajaramiz:",
    "🧮 Затем прибавляем": "🧮 So‘ng qo‘shamiz",
    "🧩 Перенесём свободный член:": "🧩 Ozod hadni tenglamaning boshqa tomoniga o‘tkazamiz:",
    "🧮 Делим обе части на": "🧮 Tenglamaning har ikki tomonini",
    "🧩 Знаменатели одинаковые, поэтому складываем числители:": "🧩 Maxrajlar bir xil, shuning uchun suratlarni qo‘shamiz:",
    "🧮 Знаменатель остаётся": "🧮 Maxraj o‘zgarmaydi:",
    "Получаем": "Natijada",
    "🧩 Переводим процент в дробь:": "🧩 Foizni kasr ko‘rinishida yozamiz:",
    "🧮 Умножаем:": "🧮 Ko‘paytiramiz:",
    "🧩 Площадь прямоугольника равна произведению его сторон.": "🧩 To‘g‘ri to‘rtburchakning yuzi uning tomonlari ko‘paytmasiga teng.",
    "🧩 Всего частей:": "🧩 Jami ulushlar soni:",
    "🧮 Одна часть равна": "🧮 Bir ulush",
    "Меньшая часть:": "Kichik qism:",
    "🧩 Разность соседних членов постоянна:": "🧩 Ketma-ket hadlar orasidagi ayirma o‘zgarmas:",
    "🧮 Следующий член:": "🧮 Keyingi had:",
    "🧩 Складываем числа:": "🧩 Sonlarni qo‘shamiz:",
    "🧮 Делим сумму на количество чисел:": "🧮 Yig‘indini sonlar miqdoriga bo‘lamiz:",
    "🧩 Благоприятных исходов": "🧩 Qulay natijalar soni",
    "всего шаров": "sharlarning jami soni",
    "🧮 Вероятность = благоприятные исходы / все исходы =": "🧮 Ehtimollik = qulay natijalar / barcha natijalar =",
    "🧩 Подставляем x =": "🧩 x = qiymatini qo‘yamiz:",
    "🧮 Получаем": "🧮 Natijada",
    "🧩 Используем формулу пути:": "🧩 Masofa formulasidan foydalanamiz:",
    "🧩 Ищем два числа с суммой": "🧩 Yig‘indisi",
    "и произведением": "va ko‘paytmasi",
    "это": "bo‘lgan ikki son",
    "🧮 Уравнение раскладывается:": "🧮 Tenglamani ko‘paytuvchilarga ajratamiz:",
    "Корни": "Ildizlari",
    "меньший —": "kichigi —",
    "🧩 Во втором уравнении делим обе части на 2:": "🧩 Ikkinchi tenglamaning har ikki tomonini 2 ga bo‘lamiz:",
    "🧮 Требуемая сумма уже найдена:": "🧮 Kerakli yig‘indi topildi:",
    "🧩 Площадь круга вычисляется по формуле": "🧩 Doira yuzi quyidagi formula bilan hisoblanadi:",
    "🧮 Подставляем r =": "🧮 r = qiymatini qo‘yamiz:",
    "🧩 При возведении степени в степень показатели перемножаются:": "🧩 Darajani darajaga ko‘targanda darajalar ko‘paytiriladi:",
    "🧮 При делении степеней с одинаковым основанием показатели вычитаются:": "🧮 Asoslari bir xil darajalarni bo‘lganda darajalar ayiriladi:",
    "🧩 Их скорости работы:": "🧩 Ularning ish tezligi:",
    "работы в час.": "ish/soat.",
    "🧮 Вместе:": "🧮 Birgalikda:",
    "Время равно обратной величине:": "Vaqt teskari qiymatga teng:",
    "🧩 Делим обе части на положительное число": "🧩 Tengsizlikning har ikki tomonini musbat",
    "знак неравенства не меняется.": "songa bo‘lamiz; tengsizlik belgisi o‘zgarmaydi.",
    "🧮 Получаем x >": "🧮 Natijada x >",
    "Наименьшее целое решение —": "Eng kichik butun yechim —",
    "🧩 Каждый раз прибавляется": "🧩 Har safar",
    "🧩 Разность соседних чисел равна": "🧩 Qo‘shni sonlar ayirmasi",
    "🧩 Три слова обозначают геометрические фигуры.": "🧩 Uchta so‘z geometrik shakllarni bildiradi.",
    "🧮 Яблоко — фрукт, поэтому оно лишнее.": "🧮 Olma meva, shuning uchun u ortiqcha.",
    "🧩 В одной паре два носка.": "🧩 Bir juftda ikkita paypoq bor.",
    "🧩 Это последовательность нечётных чисел с шагом": "🧩 Bu ayirmasi",
    "🧩 Порядок роста:": "🧩 Bo‘ylar tartibi:",
    "🧮 Самая низкая —": "🧮 Eng past bo‘yli —",
    "🧩 Прибавляем": "🧩 Qo‘shamiz",
    "🧮 Получаем": "🧮 Natijada",
    "🧩 Складываем количество карандашей двух цветов.": "🧩 Ikki rangdagi qalamlar sonini qo‘shamiz.",
    "🧩 Буквы идут в алфавитном порядке.": "🧩 Harflar alifbo tartibida keladi.",
    "🧮 После": "🧮 Undan keyin",
    "идёт": "keladi",
    "🧩 Разности:": "🧩 Ayirmalar:",
    "— они увеличиваются на": "— ular har safar",
    "🧮 Следующая разность": "🧮 Keyingi ayirma",
    "значит": "demak",
    "🧩 Каждый член умножается на": "🧩 Har bir hadni",
    "🧮 Следующий член:": "🧮 Keyingi had:",
    "🧩 Здесь переплетены два ряда:": "🧩 Bu yerda ikki qator navbatma-navbat keladi:",
    "🧮 Продолжаем первый ряд:": "🧮 Birinchi qatorni davom ettiramiz:",
    "🧩 Члены ряда — квадраты последовательных чисел:": "🧩 Qator hadlari ketma-ket sonlarning kvadratlaridan iborat:",
    "🧮 Следующий член —": "🧮 Keyingi had —",
    "🧩 Позиции букв в английском алфавите увеличиваются на": "🧩 Ingliz alifbosidagi harflar o‘rni",
    "🧮 После": "🧮 Undan keyin",
    "пропускаем ещё": "ta harfni tashlab o‘tamiz va",
    "букв и получаем": "harfini olamiz:",
    "🧩 Используем только данные посылки; не добавляем предположений.": "🧩 Faqat berilgan shartlardan foydalanamiz, qo‘shimcha taxmin qilmaymiz.",
    "🧩 Из условий получаем цепочку:": "🧩 Shartlardan quyidagi tartib kelib chiqadi:",
    "старше": "undan katta",
    "а": "esa",
    "🧮 Следовательно, младше всех": "🧮 Demak, eng kichigi",
    "🧩 Определяем связь первой пары и применяем её ко второй.": "🧩 Birinchi juftlikdagi bog‘lanishni topib, ikkinchisiga qo‘llaymiz.",
    "🧩 По правилу": "🧩 Qoida bo‘yicha",
    "сначала умножаем второй аргумент на": "avval ikkinchi argumentni",
    "🧩 Дни недели повторяются циклом из": "🧩 Hafta kunlari",
    "дней.": "kunlik sikl bo‘yicha takrorlanadi.",
    "🧮 Сдвигаемся на": "🧮",
    "позиций вперёд от": "pog‘ona oldinga siljiymiz:",
    "получаем": "natijada",
    "🧩 Разности между квадратами увеличиваются на": "🧩 Kvadratlar orasidagi ayirma har safar",
    "🧮 Следующая разность": "🧮 Keyingi ayirma",
}


def _replace_patterns(text: str, patterns: tuple[tuple[str, str], ...]) -> str:
    for pattern, replacement in sorted(patterns, key=lambda pair: -len(pair[0])):
        text = text.replace(pattern, replacement)
    return text


def translate_topic(topic: str, language: str) -> str:
    return TOPICS_UZ.get(topic, topic)


def translate_russian(text: str) -> str:
    regex_patterns = (
        (r"Решите уравнение: \((.+?)\)/(\d+) = (\d+)\.",
         r"Tenglamani yeching: (\1)/\2 = \3."),
        (r"Найдите (\d+)% от (\d+)\.", r"\2 sonining \1% ini toping."),
        (r"Число (\d+) разделили в отношении (\d+):(\d+)\. Чему равна меньшая часть\?",
         r"\1 sonini \2:\3 nisbatda bo‘lishdi. Kichik qismini toping."),
        (r"Найдите среднее арифметическое чисел (.+), (.+) и (.+)\.",
         r"\1, \2 va \3 sonlarining o‘rta arifmetik qiymatini toping."),
        (r"Найдите площадь прямоугольника со сторонами (.+) см и (.+) см\.",
         r"Tomonlari \1 sm va \2 sm bo‘lgan to‘g‘ri to‘rtburchak yuzini toping."),
        (r"В мешке (\d+) красных и (\d+) синих шаров\. Какова вероятность вынуть красный шар\?",
         r"Xaltada \1 ta qizil va \2 ta ko‘k shar bor. Qizil sharni olish ehtimolini toping."),
        (r"Автомобиль ехал со скоростью (\d+) км/ч в течение (\d+) ч\. Какой путь он прошёл\?",
         r"Avtomobil \1 km/soat tezlikda \2 soat yurdi. U qancha masofani bosib o‘tdi?"),
        (r"Радиус круга равен (\d+) см\. Чему равна площадь круга, если π оставить символом\?",
         r"Doira radiusi \1 sm. π ni ramz holida qoldirib, doira yuzini toping."),
        (r"Первый мастер выполняет работу за (\d+) ч, второй — за (\d+) ч\. За сколько часов они выполнят её вместе\?",
         r"Birinchi usta ishni \1 soatda, ikkinchisi esa \2 soatda bajaradi. Ular ishni birgalikda necha soatda tugatadi?"),
        (r"Какое наименьшее целое число x удовлетворяет неравенству (.+)\?",
         r"Quyidagi tengsizlikni qanoatlantiradigan eng kichik butun x sonini toping: \1"),
        (r"У Маши (\d+) пары носков\. Сколько это отдельных носков\?",
         r"Mashada \1 juft paypoq bor. Bu nechta dona paypoq bo‘ladi?"),
        (r"Сегодня (.+)\. Какой день недели будет через (\d+) дней\?",
         r"Bugun \1. \2 kundan keyin haftaning qaysi kuni bo‘ladi?"),
        (r"Сейчас (\d+) часа дня\. Какое время будет через (\d+) часа\?",
         r"Hozir kunduzgi soat \1. \2 soatdan keyin soat nechchi bo‘ladi?"),
        (r"На столе (\d+) красных и (\d+) синих карандаша\. Сколько всего карандашей\?",
         r"Stol ustida \1 ta qizil va \2 ta ko‘k qalam bor. Jami nechta qalam bor?"),
        (r"Если операция ⊙ определена как a ⊙ b = a \+ b × (\d+), чему равно (\d+) ⊙ (\d+)\?",
         r"Agar ⊙ amali a ⊙ b = a + b × \1 qoidasi bilan berilgan bo‘lsa, \2 ⊙ \3 nimaga teng?"),
        (r"Какое значение имеет выражение (.+?) при x = (.+?)\?",
         r"x = \2 bo‘lganda quyidagi ifodaning qiymatini toping: \1"),
        (r"(.+?) старше (.+?)\. (.+?) старше (.+?)\. Кто младше всех из этих троих\?",
         r"\1 \2 dan katta. \3 esa \4 dan katta. Bu uch kishidan eng kichigi kim?"),
        (r"Завершите аналогию: (.+?) относится к «(.+?)», как (.+?) относится к …",
         r"O‘xshatishni davom ettiring: \1 «\2» bilan qanday bog‘liq bo‘lsa, \3 ham … bilan shunday bog‘liq."),
        (r"🧩 Ищем два числа с суммой (.+?) и произведением (.+?): это (.+?) и (.+?)\.",
         r"🧩 Yig‘indisi \1 va ko‘paytmasi \2 bo‘lgan sonlar \3 va \4."),
        (r"🧮 Уравнение раскладывается: (.+?) Корни (.+?) и (.+?); меньший — (.+?)\.",
         r"🧮 Tenglamani ko‘paytuvchilarga ajratamiz: \1 Ildizlari \2 va \3; kichigi — \4."),
        (r"🧩 Каждый раз прибавляется (\d+)\.", r"🧩 Har safar \1 qo‘shiladi."),
        (r"🧮 Затем прибавляем (\d+):", r"🧮 So‘ng \1 ni qo‘shamiz:"),
        (r"🧩 Прибавляем (\d+) часа к (\d+) часам дня\.",
         r"🧩 Kunduzgi soat \2 ga \1 soat qo‘shamiz."),
        (r"🧩 Из условий получаем цепочку: (.+?) старше (.+?), а (.+?) старше (.+?)\.",
         r"🧩 Tartib: \1 > \2 > \4."),
        (r"🧩 Делим обе части на положительное число (\d+); знак неравенства не меняется\.",
         r"🧩 Musbat \1 soniga bo‘lamiz; tengsizlik belgisi o‘zgarmaydi."),
        (r"🧩 По правилу ⊙ сначала умножаем второй аргумент на (\d+)\.",
         r"🧩 ⊙ qoidasiga ko‘ra, avval ikkinchi argumentni \1 ga ko‘paytiramiz."),
        (r"🧩 Подставляем x = (\d+):", r"🧩 x = \1 qiymatini ifodaga qo‘yamiz:"),
        (r"🧩 Разности увеличиваются на (\d+): (.+)\.",
         r"🧩 Ayirmalar \1 ga ortib boradi: \2."),
        (r"🧩 Умножаем обе части на (\d+):", r"🧩 Tenglamaning har ikki tomonini \1 ga ko‘paytiramiz:"),
        (r"🧮 Вычитаем (\d+), затем делим на (\d+): x = (\d+)\.",
         r"🧮 \1 ni ayirib, so‘ng \2 ga bo‘lamiz: x = \3."),
    )
    for pattern, replacement in regex_patterns:
        text = re.sub(pattern, replacement, text)
    text = _replace_patterns(text, _RU_PHRASES)
    text = text.replace(", а ", ", va ")
    for source, target in sorted(_RU_SENTENCES.items(), key=lambda pair: -len(pair[0])):
        if len(source) < 4:
            continue
        text = text.replace(source, target)
    text = re.sub(r"🧩 Har safar (\d+)\.", r"🧩 Har safar \1 qo‘shiladi.", text)
    for source, target in sorted(_RU_WORDS.items(), key=lambda pair: -len(pair[0])):
        text = re.sub(rf"(?<![A-Za-zА-Яа-яЁё]){re.escape(source)}(?![A-Za-zА-Яа-яЁё])", target, text)
    text = re.sub(r"(?<=\d)\s*см²\b", " sm²", text)
    text = re.sub(r"(?<=π)\s*см²\b", " sm²", text)
    text = re.sub(r"(?<=\d)\s*км/ч\b", " km/soat", text)
    text = re.sub(r"(?<=\d)\s*км\b", " km", text)
    text = re.sub(r"(?<=\d)\s*см\b", " sm", text)
    text = re.sub(r"(?<=\d)\s*ч\b", " soat", text)
    text = re.sub(r"(\d+) часов вечера", r"kechki soat \1", text)
    text = re.sub(r"(\d+) часа вечера", r"kechki soat \1", text)
    text = re.sub(r"(\d+) часов утра", r"ertalab soat \1", text)
    text = re.sub(r"(\d+) часа утра", r"ertalab soat \1", text)
    text = re.sub(r"(\d+) часов kechqurun", r"kechki soat \1", text)
    text = re.sub(r"(\d+) часа kechqurun", r"kechki soat \1", text)
    text = re.sub(r"(\d+) часов ertalab", r"ertalab soat \1", text)
    text = re.sub(r"(\d+) часа ertalab", r"ertalab soat \1", text)
    text = text.replace("(другой вариант)", "(boshqa variant)")
    text = text.replace(" и ", " va ")
    return text


def _match_translation(text: str, pattern: str, replacement: str) -> str:
    match = re.fullmatch(pattern, text, re.S)
    if match is None:
        raise ValueError(f"Unexpected question explanation format: {text}")
    return match.expand(replacement)


def _translate_math_explanation(item: dict) -> str:
    text = item["explanation"]
    match = re.fullmatch(r"✅ Ответ: (.+?)\n\n(.+)", text, re.S)
    if match is None:
        raise ValueError(f"Unexpected mathematics explanation format: {text}")
    answer, body = match.groups()
    topic = item["topic"]
    templates = {
        "Арифметика": (
            r"🧩 Сначала выполняем умножение: (.+?) × (.+?) = (.+?)\.\n"
            r"🧮 Затем прибавляем (.+?): (.+?) \+ (.+?) = (.+?)\.",
            r"🧩 Avval ko‘paytiramiz: \1 × \2 = \3.\n"
            r"🧮 So‘ng \4 ni qo‘shamiz: \5 + \4 = \7.",
        ),
        "Линейные уравнения": (
            r"🧩 Перенесём свободный член: (.+?)x = (.+?) − (.+?) = (.+?)\.\n"
            r"🧮 Делим обе части на (.+?): x = (.+?)\.",
            r"🧩 Ozod hadni tenglamaning boshqa tomoniga o‘tkazamiz: "
            r"\1x = \2 − \3 = \4.\n"
            r"🧮 Tenglamaning har ikki tomonini \5 ga bo‘lamiz: x = \6.",
        ),
        "Дроби": (
            r"🧩 Знаменатели одинаковые, поэтому складываем числители: "
            r"(.+?) \+ (.+?) = (.+?)\.\n🧮 Знаменатель остаётся (.+?)\. "
            r"Получаем (.+?)\.",
            r"🧩 Maxrajlar bir xil, shuning uchun suratlarni qo‘shamiz: "
            r"\1 + \2 = \3.\n🧮 Maxraj o‘zgarmaydi: \4. Natijada \5.",
        ),
        "Проценты": (
            r"🧩 Переводим процент в дробь: (.+?)% = (.+?)/(.+?)\.\n"
            r"🧮 Умножаем: (.+?) × (.+?)/(.+?) = (.+?)\.",
            r"🧩 Foizni kasr ko‘rinishida yozamiz: \1% = \2/\3.\n"
            r"🧮 Ko‘paytiramiz: \4 × \5/\6 = \7.",
        ),
        "Геометрия": (
            r"🧩 Площадь прямоугольника равна произведению его сторон\.\n"
            r"🧮 S = (.+?) × (.+?) = (.+?) см²\.",
            r"🧩 To‘g‘ri to‘rtburchakning yuzi uning tomonlari ko‘paytmasiga teng.\n"
            r"🧮 S = \1 × \2 = \3 sm².",
        ),
        "Пропорции": (
            r"🧩 Всего частей: (.+?) \+ (.+?) = (.+?)\.\n"
            r"🧮 Одна часть равна (.+?) ÷ (.+?)\. Меньшая часть: "
            r"(.+?) × (.+?)/(.+?) = (.+?)\.",
            r"🧩 Jami ulushlar soni: \1 + \2 = \3.\n"
            r"🧮 Bir ulush \4 ÷ \5 ga teng. Kichik qism: "
            r"\6 × \7/\8 = \9.",
        ),
        "Последовательности": (
            r"🧩 Разность соседних членов постоянна: (.+?) − (.+?) = (.+?)\.\n"
            r"🧮 Следующий член: (.+?) \+ (.+?) = (.+?)\.",
            r"🧩 Qo‘shni hadlar ayirmasi o‘zgarmas: \1 − \2 = \3.\n"
            r"🧮 Keyingi had: \4 + \5 = \6.",
        ),
        "Среднее арифметическое": (
            r"🧩 Складываем числа: (.+?) \+ (.+?) \+ (.+?) = (.+?)\.\n"
            r"🧮 Делим сумму на количество чисел: (.+?) ÷ (.+?) = (.+?)\.",
            r"🧩 Sonlarni qo‘shamiz: \1 + \2 + \3 = \4.\n"
            r"🧮 Yig‘indini sonlar miqdoriga bo‘lamiz: \5 ÷ \6 = \7.",
        ),
        "Вероятность": (
            r"🧩 Благоприятных исходов (.+?), всего шаров (.+?) \+ (.+?) = (.+?)\.\n"
            r"🧮 Вероятность = благоприятные исходы / все исходы = (.+?)\.",
            r"🧩 Qulay natijalar soni \1, jami sharlar soni \2 + \3 = \4.\n"
            r"🧮 Ehtimollik = qulay natijalar / barcha natijalar = \5.",
        ),
        "Разложение на множители": (
            r"🧩 Подставляем x = 1: (.+?)\.\n🧮 Получаем (.+?)\.",
            r"🧩 x = 1 qiymatini qo‘yamiz: \1.\n🧮 Natijada \2.",
        ),
        "Движение": (
            r"🧩 Используем формулу пути: s = v × t\.\n"
            r"🧮 s = (.+?) × (.+?) = (.+?) км\.",
            r"🧩 Masofa formulasidan foydalanamiz: s = v × t.\n"
            r"🧮 s = \1 × \2 = \3 km.",
        ),
        "Квадратные уравнения": (
            r"🧩 Ищем два числа с суммой (.+?) и произведением (.+?): "
            r"это (.+?) и (.+?)\.\n"
            r"🧮 Уравнение раскладывается: (.+?) Корни (.+?) и (.+?); "
            r"меньший — (.+?)\.",
            r"🧩 Yig‘indisi \1 va ko‘paytmasi \2 bo‘lgan sonlar — \3 va \4.\n"
            r"🧮 Tenglamani ko‘paytuvchilarga ajratamiz: \5 "
            r"Ildizlari \6 va \7; kichigi — \8.",
        ),
        "Системы уравнений": (
            r"🧩 Во втором уравнении делим обе части на 2: x \+ y = (.+?)\.\n"
            r"🧮 Требуемая сумма уже найдена: x \+ y = (.+?)\.",
            r"🧩 Ikkinchi tenglamaning har ikki tomonini 2 ga bo‘lamiz: "
            r"x + y = \1.\n🧮 Kerakli yig‘indi topildi: x + y = \2.",
        ),
        "Степени": (
            r"🧩 При возведении степени в степень показатели перемножаются: "
            r"(.+?)\.\n🧮 При делении степеней с одинаковым основанием "
            r"показатели вычитаются: (.+?)\.",
            r"🧩 Darajani darajaga ko‘targanda darajalar ko‘paytiriladi: \1.\n"
            r"🧮 Asoslari bir xil darajalarni bo‘lganda darajalar ayiriladi: \2.",
        ),
        "Совместная работа": (
            r"🧩 Их скорости работы: (.+?) и (.+?) работы в час\.\n"
            r"🧮 Вместе: (.+?) \+ (.+?) = (.+?)\. "
            r"Время равно обратной величине: (.+?) ч\.",
            r"🧩 Ularning ish tezligi: \1 va \2 ish/soat.\n"
            r"🧮 Birgalikda: \3 + \4 = \5. Ishni bajarish vaqti "
            r"bu tezliklar yig‘indisining teskari qiymati: \6 soat.",
        ),
        "Неравенства": (
            r"🧩 Делим обе части на положительное число (.+?); "
            r"знак неравенства не меняется\.\n"
            r"🧮 Получаем x > (.+?)\. Наименьшее целое решение — (.+?)\.",
            r"🧩 Tengsizlikning har ikki tomonini musbat \1 ga bo‘lamiz; "
            r"tengsizlik belgisi o‘zgarmaydi.\n"
            r"🧮 Natijada x > \2. Eng kichik butun yechim — \3.",
        ),
        "Дробно-рациональные уравнения": (
            r"🧩 Умножаем обе части на (.+?): (.+?) \+ (.+?) = (.+?)\.\n"
            r"🧮 Вычитаем (.+?), затем делим на (.+?): x = (.+?)\.",
            r"🧩 Tenglamaning har ikki tomonini \1 ga ko‘paytiramiz: "
            r"\2 + \3 = \4.\n🧮 \5 ni ayirib, so‘ng \6 ga bo‘lamiz: x = \7.",
        ),
    }
    if topic == "Геометрия" and body.startswith("🧩 Площадь круга"):
        pattern = (
            r"🧩 Площадь круга вычисляется по формуле S = πr²\.\n"
            r"🧮 Подставляем r = (.+?): S = π × (.+?)² = (.+?)π см²\."
        )
        translated = _match_translation(
            body,
            pattern,
            r"🧩 Doira yuzi S = πr² formulasi bilan hisoblanadi.\n"
            r"🧮 r = \1 qiymatini qo‘yamiz: S = π × \2² = \3π sm².",
        )
    else:
        pattern, replacement = templates[topic]
        translated = _match_translation(body, pattern, replacement)
    return f"✅ Javob: {translate_russian(answer)}\n\n{translated}"


_IQ_EXACT_LINES = {
    "🧩 Книга — инструмент для чтения.": "🧩 Kitob o‘qish uchun xizmat qiladi.",
    "🧮 Вилка — инструмент для еды.": "🧮 Sanchqi ovqat yeyish uchun ishlatiladi.",
    "🧩 Три слова обозначают геометрические фигуры.": "🧩 Uchta so‘z geometrik shaklni bildiradi.",
    "🧮 Яблоко — фрукт, поэтому оно лишнее.": "🧮 Olma meva, shuning uchun ortiqcha so‘z.",
    "🧩 В одной паре два носка.": "🧩 Bir juft paypoq ikkita paypoqdan iborat.",
    "🧩 Буквы идут в алфавитном порядке.": "🧩 Harflar alifbo tartibida joylashgan.",
    "🧩 Используем только данные посылки; не добавляем предположений.": "🧩 Faqat berilgan shartlardan foydalanamiz, qo‘shimcha taxmin qilmaymiz.",
    "🧩 Определяем связь первой пары и применяем её ко второй.": "🧩 Birinchi juftlikdagi bog‘lanishni topib, ikkinchisiga qo‘llaymiz.",
    "🧩 Дни недели повторяются циклом из 7 дней.": "🧩 Hafta kunlari 7 kunlik davr bilan takrorlanadi.",
    "🧩 Разности между квадратами увеличиваются на 2: 3, 5, 7, …": "🧩 Kvadratlar orasidagi ayirmalar 2 taga ortadi: 3, 5, 7, …",
}

_IQ_RULES = {
    "🧮 Птица живёт в гнезде; пчёлы живут в улье.": "🧮 Qush uyada, asalarilar esa asalari uyasida yashaydi.",
    "🧮 Автор создаёт книгу; композитор создаёт музыку.": "🧮 Muallif kitob yozadi, bastakor esa musiqa yaratadi.",
    "🧮 Термометр измеряет температуру; барометр измеряет давление.": "🧮 Termometr haroratni, barometr esa bosimni o‘lchaydi.",
    "🧮 Из семени развивается растение; из яйца может развиться птица.": "🧮 Urug‘dan o‘simlik, tuxumdan esa qush rivojlanadi.",
    "🧮 Врач оказывает помощь пациенту; учитель обучает ученика.": "🧮 Shifokor bemorga yordam beradi, o‘qituvchi esa o‘quvchiga ta’lim beradi.",
    "🧮 Минута состоит из секунд; метр состоит из сантиметров.": "🧮 Daqiqa soniyalardan, metr esa santimetrlardan tashkil topadi.",
    "🧮 Ключ открывает замок; пароль даёт доступ к аккаунту.": "🧮 Kalit qulfni ochadi, parol esa hisobga kirish imkonini beradi.",
    "🧮 Рыба передвигается в воде; птица передвигается в воздухе.": "🧮 Baliq suvda, qush esa havoda harakatlanadi.",
    "🧮 Термометр измеряет температуру; весы измеряют массу.": "🧮 Termometr haroratni, tarozi esa massani o‘lchaydi.",
    "🧮 Слова образуют предложение; кирпичи образуют стену.": "🧮 So‘zlar gapni, g‘ishtlar esa devorni hosil qiladi.",
    "🧮 Пчёлы производят мёд; коровы дают молоко.": "🧮 Asalarilar asal, sigirlar esa sut beradi.",
    "🧮 Глаз служит для зрения; ухо — для слуха.": "🧮 Ko‘z ko‘rish, quloq esa eshitish uchun xizmat qiladi.",
    "🧮 Пекарь изготавливает хлеб; гончар изготавливает горшки.": "🧮 Novvoy non, kulol esa ko‘za yasaydi.",
    "🧮 Все лиры входят в множество моров, а моры не пересекаются с тевами.": "🧮 Barcha lira morlar guruhiga kiradi, morlar esa tevalar bilan kesishmaydi.",
    "🧮 Некоторые исследователи являются врачами, а значит, имеют образование.": "🧮 Ba’zi tadqiqotchilar shifokor, demak, ular ma’lumotga ega.",
    "🧮 X принадлежит классу квадратов, который не пересекается с классом кругов.": "🧮 X kvadratlar sinfiga kiradi, kvadratlar va doiralar sinflari esa kesishmaydi.",
    "🧮 Принадлежность к А означает принадлежность к Б, а значит и к В.": "🧮 A ga tegishli bo‘lish B ga, demak V ga ham tegishli bo‘lishni anglatadi.",
    "🧮 Те музыканты, которые являются преподавателями, умеют объяснять.": "🧮 O‘qituvchi bo‘lgan musiqachilar tushuntira oladi.",
    "🧮 Зели входят в множество ранов, которое не пересекается с множеством силов.": "🧮 Zelilar ranlar guruhiga kiradi, ranlar esa sillar bilan kesishmaydi.",
    "🧮 Каждый пилот проходит обучение, а каждый прошедший обучение сдаёт экзамен.": "🧮 Har bir uchuvchi tayyorgarlikdan o‘tadi va undan o‘tgan har bir kishi imtihon topshiradi.",
    "🧮 Художники, которые являются архитекторами, не работают без чертежей.": "🧮 Me’mor bo‘lgan rassomlar chizmalarsiz ishlamaydi.",
    "🧮 X является маяком, а каждый маяк заметен ночью.": "🧮 X mayoq, barcha mayoqlar esa tunda ko‘rinadi.",
    "🧮 Прозрачные материалы не могут быть металлами, поэтому некоторые материалы не металлы.": "🧮 Shaffof materiallar metall bo‘la olmaydi, demak, ba’zi materiallar metall emas.",
    "🧮 Ира принадлежит группе участников, каждому из которых выдали номер.": "🧮 Ira raqam berilgan ishtirokchilar guruhiga kiradi.",
    "🧮 Книги, являющиеся словарями, содержат определения.": "🧮 Lug‘at bo‘lgan kitoblarda ta’riflar bor.",
}


def _translate_iq_line(line: str) -> str:
    if line in _IQ_EXACT_LINES:
        return _IQ_EXACT_LINES[line]
    if line in _IQ_RULES:
        return _IQ_RULES[line]
    match = re.fullmatch(r"🧩 Порядок роста: (.+?) > (.+?) > (.+?)\.", line)
    if match:
        names = (_UZ_NAMES[name] for name in match.groups())
        return f"🧩 Bo‘ylar tartibi: {' > '.join(names)}."
    match = re.fullmatch(r"🧮 Самая низкая — (.+?)\.", line)
    if match:
        return f"🧮 Bo‘yi eng past — {_UZ_NAMES[match.group(1)]}."
    match = re.fullmatch(
        r"🧩 Из условий получаем цепочку: (.+?) старше (.+?), "
        r"а (.+?) старше (.+?)\.",
        line,
    )
    if match:
        first, second, third, fourth = match.groups()
        return (
            f"🧩 Shartlarga ko‘ra: {_UZ_NAMES[first]} > "
            f"{_UZ_NAMES[second]} > {_UZ_NAMES[fourth]}."
        )
    match = re.fullmatch(r"🧮 Следовательно, младше всех (.+?)\.", line)
    if match:
        return f"🧮 Demak, eng kichigi — {_UZ_NAMES[match.group(1)]}."
    match = re.fullmatch(
        r"🧮 Сдвигаемся на (.+?) позиций вперёд от (.+?): получаем (.+?)\.",
        line,
    )
    if match:
        shift, start, result = match.groups()
        return (
            f"🧮 {translate_russian(start).capitalize()} kunidan boshlab {shift} kun o‘tib, "
            f"{translate_russian(result)} bo‘ladi."
        )
    patterns = (
        (r"🧩 Каждый раз прибавляется (.+?)\.", r"🧩 Har safar \1 qo‘shiladi."),
        (r"🧩 Разность соседних чисел равна (.+?)\.", r"🧩 Qo‘shni sonlar orasidagi ayirma \1 ga teng."),
        (r"🧩 Это последовательность нечётных чисел с шагом (.+?)\.", r"🧩 Bu toq sonlar ketma-ketligi; har bir keyingi son \1 ga ortadi."),
        (r"🧮 (.+?) носков\.", r"🧮 \1 ta paypoq."),
        (r"🧩 Прибавляем (.+?) часа к (.+?) часам дня\.", r"🧩 Kunduzgi soat \2 ga \1 soat qo‘shamiz."),
        (r"🧮 Получаем (.+?) часов вечера\.", r"🧮 Natijada kechki soat \1 bo‘ladi."),
        (r"🧩 Складываем количество карандашей двух цветов\.", r"🧩 Ikki rangdagi qalamlar sonini qo‘shamiz."),
        (r"🧩 По правилу ⊙ сначала умножаем второй аргумент на (.+?)\.", r"🧩 ⊙ amaliga ko‘ra, avval ikkinchi sonni \1 ga ko‘paytiramiz."),
        (r"🧮 После (.+?) идёт (.+?)\.", r"🧮 \1 harfidan keyin \2 keladi."),
        (r"🧩 Разности: (.+?) — они увеличиваются на (.+?)\.", r"🧩 Ayirmalar: \1. Har bir keyingi ayirma \2 ga ortadi."),
        (r"🧮 Следующая разность (.+?), значит (.+?) \+ (.+?) = (.+?)\.", r"🧮 Keyingi ayirma \1. Demak, \2 + \3 = \4."),
        (r"🧩 Каждый член умножается на (.+?): (.+?) ÷ (.+?) = (.+?)\.", r"🧩 Har bir had oldingisidan \1 marta katta: \2 ÷ \3 = \4."),
        (r"🧮 Следующий член: (.+?) × (.+?) = (.+?)\.", r"🧮 Keyingi had: \1 × \2 = \3."),
        (r"🧩 Здесь переплетены два ряда: (.+?) и (.+?)\.", r"🧩 Bu yerda ikki qator navbatma-navbat keladi: \1 va \2."),
        (r"🧮 Продолжаем первый ряд: (.+?) \+ (.+?) = (.+?)\.", r"🧮 Birinchi qatorni davom ettiramiz: \1 + \2 = \3."),
        (r"🧩 Члены ряда — квадраты последовательных чисел: (.+?)\.", r"🧩 Qator hadlari ketma-ket sonlarning kvadratlaridan iborat: \1."),
        (r"🧮 Следующий член — (.+?)² = (.+?)\.", r"🧮 Keyingi had: \1² = \2."),
        (r"🧩 Позиции букв в английском алфавите увеличиваются на (.+?)\.", r"🧩 Ingliz alifbosida harflar oralig‘i \1 pog‘onaga ortadi."),
        (r"🧮 После (.+?) пропускаем ещё (.+?) букв и получаем (.+?)\.", r"🧮 \1 harfidan keyin \2 ta harfni tashlab, \3 harfiga kelamiz."),
        (r"🧮 (.+?) ⊙ (.+?) = (.+?) \+ (.+?) × (.+?) = (.+?) \+ (.+?) = (.+?)\.", r"🧮 \1 ⊙ \2 = \3 + \4 × \5 = \6 + \7 = \8."),
        (r"🧩 Дни недели повторяются циклом из 7 дней\.", r"🧩 Hafta kunlari 7 kunlik davr bilan takrorlanadi."),
        (r"🧩 Разности увеличиваются на 2: (.+?)\.", r"🧩 Ayirmalar har safar 2 taga ortadi: \1."),
        (r"🧮 Следующая разность (.+?); (.+?) \+ (.+?) = (.+?)\.", r"🧮 Keyingi ayirma \1; \2 + \3 = \4."),
    )
    for pattern, replacement in patterns:
        if re.fullmatch(pattern, line):
            return re.sub(pattern, replacement, line)
    if not re.search(r"[А-Яа-яЁё]", line):
        return line
    raise ValueError(f"Untranslated IQ explanation line: {line}")


def _translate_iq_explanation(item: dict) -> str:
    text = item["explanation"]
    match = re.fullmatch(r"✅ Ответ: (.+?)\n\n(.+)", text, re.S)
    if match is None:
        raise ValueError(f"Unexpected IQ explanation format: {text}")
    answer, body = match.groups()
    translated_body = "\n".join(_translate_iq_line(line) for line in body.splitlines())
    return f"✅ Javob: {translate_russian(answer)}\n\n{translated_body}"


_UZ_NAMES = {
    "Али": "Ali", "Бек": "Bek", "Бор": "Bor", "Бора": "Bor",
    "Валя": "Vali", "Вали": "Vali", "Валю": "Vali", "Дина": "Dina",
    "Егор": "Yegor", "Лола": "Lola", "Малика": "Malika",
    "Тимур": "Temur", "Нодир": "Nodir", "Сара": "Sara", "Азиз": "Aziz",
}


def _translate_iq_question(text: str) -> str:
    match = re.fullmatch(
        r"(.+?) выше (.+?), а (.+?) выше (.+?)\. Кто самый низкий\?",
        text,
    )
    if match:
        first, second, third, fourth = match.groups()
        return (
            f"{_UZ_NAMES[first]} {_UZ_NAMES[second]}dan baland, "
            f"{_UZ_NAMES[third]} esa {_UZ_NAMES[fourth]}dan baland. "
            "Eng past bo‘yli kim?"
        )
    match = re.fullmatch(
        r"(.+?) старше (.+?)\. (.+?) старше (.+?)\. "
        r"Кто младше всех из этих троих\?",
        text,
    )
    if match:
        first, second, third, fourth = match.groups()
        return (
            f"{_UZ_NAMES[first]} {_UZ_NAMES[second]}dan katta. "
            f"{_UZ_NAMES[third]} esa {_UZ_NAMES[fourth]}dan katta. "
            "Bu uch kishidan eng kichigi kim?"
        )
    return translate_russian(text)


def translate_fields(item: dict) -> dict:
    language = item["language"]
    if language == "en":
        topic = item["topic"]
        question = item["question_text"]
        options = list(item["options"])
        explanation = item["explanation"]
    else:
        topic = translate_topic(item["topic"], language)
        question = (
            _translate_iq_question(item["question_text"])
            if item["subject"] == "iq"
            else translate_russian(item["question_text"])
        )
        options = [translate_russian(option) for option in item["options"]]
        if item["subject"] == "mathematics":
            explanation = _translate_math_explanation(item)
        elif item["subject"] == "iq":
            explanation = _translate_iq_explanation(item)
        else:
            explanation = translate_russian(item["explanation"])
    translated_fields = {
        "topic_uz": topic,
        "question_text_uz": question,
        "options_uz": options,
        "explanation_uz": explanation,
    }
    localized_text = [topic, question, explanation, *options]
    if language != "en" and any(
        any("\u0400" <= char <= "\u04ff" for char in value)
        for value in localized_text
    ):
        raise ValueError(f"Untranslated Cyrillic content in {item['subject']} question: {item['question_text']}")
    return translated_fields
