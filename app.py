from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
import random
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock

try:
    import swisseph as swe
except ImportError:
    swe = None

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
DATA_FILE = ROOT / "astro_data.json"
DATA_LOCK = Lock()
DISCLAIMER = "Вся информация носит развлекательный характер и не является профессиональной консультацией."


def load_local_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_local_env()

SIGNS = [
    ("Козерог", 120), ("Водолей", 219), ("Рыбы", 321), ("Овен", 420),
    ("Телец", 521), ("Близнецы", 621), ("Рак", 722), ("Лев", 823),
    ("Дева", 923), ("Весы", 1023), ("Скорпион", 1122), ("Стрелец", 1222),
    ("Козерог", 1231),
]
PLANETS = ["Солнце", "Луна", "Меркурий", "Венера", "Марс", "Юпитер", "Сатурн", "Уран", "Нептун", "Плутон"]
NUMBER_MEANINGS = {
    "1": {"title": "Единица — инициатива", "text": "Самостоятельность, воля и способность начинать новое. Тень: упрямство и желание всё контролировать."},
    "2": {"title": "Двойка — чувствительность", "text": "Дипломатия, эмпатия и умение сотрудничать. Тень: сомнения и зависимость от чужой оценки."},
    "3": {"title": "Тройка — самовыражение", "text": "Творчество, юмор и лёгкость общения. Тень: рассеянность и незавершённые дела."},
    "4": {"title": "Четвёрка — опора", "text": "Практичность, порядок и выносливость. Тень: излишняя жёсткость и страх перемен."},
    "5": {"title": "Пятёрка — свобода", "text": "Любознательность, движение и любовь к опыту. Тень: импульсивность и трудность с режимом."},
    "6": {"title": "Шестёрка — забота", "text": "Ответственность, красота и желание создавать уют. Тень: гиперопека и перфекционизм."},
    "7": {"title": "Семёрка — глубина", "text": "Аналитичность, интуиция и интерес к смыслам. Тень: закрытость и уход в изоляцию."},
    "8": {"title": "Восьмёрка — результат", "text": "Организация, влияние и умение обращаться с ресурсами. Тень: давление и чрезмерная ориентация на статус."},
    "9": {"title": "Девятка — мудрость", "text": "Щедрость, широкий взгляд и стремление приносить пользу. Тень: спасательство и эмоциональное выгорание."},
}
PLANET_MEANINGS = {
    "Солнце": "Личность, воля, самоощущение и способ сиять.",
    "Луна": "Эмоции, привычки, чувство безопасности и внутренний ребёнок.",
    "Меркурий": "Мышление, речь, обучение и обмен информацией.",
    "Венера": "Симпатии, отношения, вкус и способ принимать удовольствие.",
    "Марс": "Действие, желание, смелость и способ защищать границы.",
    "Юпитер": "Рост, вера, смысл, удача и расширение возможностей.",
    "Сатурн": "Дисциплина, ответственность, ограничения и зрелость.",
    "Уран": "Свобода, перемены, оригинальность и неожиданные повороты.",
    "Нептун": "Воображение, сострадание, идеалы и чувствительность.",
    "Плутон": "Глубокая трансформация, сила и обновление.",
}
HOUSE_MEANINGS = {
    1: "Я, внешность и способ начинать", 2: "Ресурсы, деньги и личные ценности",
    3: "Общение, обучение и близкое окружение", 4: "Дом, семья и внутренний фундамент",
    5: "Творчество, романтика и удовольствие", 6: "Ежедневность, навыки и забота о себе",
    7: "Партнёрство и зеркала отношений", 8: "Доверие, общие ресурсы и перемены",
    9: "Мировоззрение, путешествия и смысл", 10: "Призвание, карьера и репутация",
    11: "Друзья, сообщество и будущее", 12: "Отдых, подсознание и восстановление",
}
SIGN_STYLES = {
    "Овен": "прямо, быстро и через инициативу", "Телец": "последовательно, чувственно и через устойчивость",
    "Близнецы": "гибко, любознательно и через обмен идеями", "Рак": "бережно, интуитивно и через эмоциональную связь",
    "Лев": "ярко, творчески и через личное выражение", "Дева": "точно, практично и через улучшение деталей",
    "Весы": "дипломатично, эстетично и через поиск баланса", "Скорпион": "глубоко, интенсивно и через честность",
    "Стрелец": "широко, свободно и через поиск смысла", "Козерог": "сдержанно, структурно и через долгосрочную цель",
    "Водолей": "независимо, нестандартно и через идеи будущего", "Рыбы": "мягко, образно и через интуицию",
}
ASPECT_MEANINGS = {
    "тригон": "Тема проявляется естественно: её легче развивать через доверие к своим сильным сторонам.",
    "соединение": "Две силы работают одновременно и усиливают друг друга; важно направлять их в одну цель.",
    "квадрат": "Есть внутреннее трение: результат появляется, когда человек переводит напряжение в конкретное действие.",
    "оппозиция": "Требуется баланс между двумя полюсами и умение учитывать как себя, так и другого.",
}
TAROT_DISCLAIMER = "Карты Таро — инструмент для размышления, а не окончательный приговор. Всё в ваших руках."
TAROT_TOPICS = [
    {"id": "feelings", "title": "Отношения · чувства партнёра", "question": "Что партнёр чувствует ко мне и какова истинная динамика между нами?"},
    {"id": "future_relationship", "title": "Перспектива отношений", "question": "К чему приведут эти отношения и как они будут развиваться?"},
    {"id": "loneliness", "title": "Почему нет отношений", "question": "Что мешает мне строить отношения и какой партнёр мне подходит?"},
    {"id": "career", "title": "Карьера и работа", "question": "Какие перспективы у моей работы и что поможет профессиональному росту?"},
    {"id": "business", "title": "Бизнес и финансы", "question": "Что важно учесть в новом направлении и какие ресурсы помогут делу?"},
    {"id": "choice", "title": "Выбор между вариантами", "question": "Как осознанно сравнить варианты и какой критерий сейчас главный?"},
    {"id": "money", "title": "Финансовое положение", "question": "Что мешает улучшить финансовую ситуацию и где находится мой ресурс?"},
    {"id": "wellbeing", "title": "Самочувствие и баланс", "question": "Что поможет бережно поддержать мой ресурс и восстановить равновесие?"},
    {"id": "advice", "title": "Ситуация и совет", "question": "Как мне поступить в сложной ситуации и что важно увидеть яснее?"},
    {"id": "period", "title": "Общий расклад на период", "question": "Какие темы будут важны в ближайшие три месяца и на что направить внимание?"},
]
MAJOR_ARCANA = [
    ("Шут", "новый цикл, свобода, открытость", "осторожность, хаос, страх шага"),
    ("Маг", "инициатива, навыки, влияние", "манипуляция, рассеянность, сомнения"),
    ("Верховная Жрица", "интуиция, тишина, скрытое знание", "закрытость, игнорирование интуиции"),
    ("Императрица", "созидание, забота, изобилие", "застой, чрезмерная опека"),
    ("Император", "структура, границы, ответственность", "жёсткость, контроль"),
    ("Иерофант", "ценности, обучение, традиция", "догматизм, чужие правила"),
    ("Влюблённые", "выбор, близость, согласие с собой", "сомнения, разрыв ценностей"),
    ("Колесница", "воля, движение, собранность", "спешка, борьба направлений"),
    ("Сила", "мягкая смелость, самообладание", "подавление, неуверенность"),
    ("Отшельник", "поиск смысла, пауза, мудрость", "изоляция, избегание ответа"),
    ("Колесо Фортуны", "поворот, цикл, шанс", "сопротивление переменам"),
    ("Справедливость", "честность, последствия, баланс", "предвзятость, уход от ответственности"),
    ("Повешенный", "новый взгляд, отпускание, пауза", "застревание, жертвенность"),
    ("Смерть", "завершение этапа, трансформация", "цепляние за прошлое, страх перемен"),
    ("Умеренность", "ритм, восстановление, соединение", "крайности, нетерпение"),
    ("Дьявол", "желание, привязанность, честность с собой", "зависимость, иллюзия бессилия"),
    ("Башня", "освобождение от ложного, резкая ясность", "сопротивление неизбежному"),
    ("Звезда", "надежда, ориентир, вдохновение", "разочарование, потеря направления"),
    ("Луна", "чувства, подсознание, неопределённость", "прояснение страхов, выход из тумана"),
    ("Солнце", "ясность, энергия, радость", "завышенные ожидания, выгорание"),
    ("Суд", "осознание, призвание, новый ответ", "самокритика, откладывание решения"),
    ("Мир", "завершение, целостность, результат", "незакрытый цикл, рассеянность"),
]
MAJOR_ARCANA_NUMBER_NAMES = {
    1: "Маг", 2: "Верховная Жрица", 3: "Императрица", 4: "Император",
    5: "Иерофант", 6: "Влюблённые", 7: "Колесница", 8: "Сила",
    9: "Отшельник", 10: "Колесо Фортуны", 11: "Справедливость",
    12: "Повешенный", 13: "Смерть", 14: "Умеренность", 15: "Дьявол",
    16: "Башня", 17: "Звезда", 18: "Луна", 19: "Солнце", 20: "Суд",
    21: "Мир", 22: "Шут",
}
_major_meanings_by_name = {name: (upright, reversed_text) for name, upright, reversed_text in MAJOR_ARCANA}
MAJOR_ARCANA_BY_NUMBER = {
    number: {
        "name": name,
        "aliases": (["Верховный Жрец"] if name == "Иерофант" else ["Дурак"] if name == "Шут" else []),
        "shortUpright": _major_meanings_by_name[name][0].split(",")[0],
        "fullUpright": _major_meanings_by_name[name][0],
        "shortReversed": _major_meanings_by_name[name][1].split(",")[0],
        "fullReversed": _major_meanings_by_name[name][1],
    }
    for number, name in MAJOR_ARCANA_NUMBER_NAMES.items()
}
MINOR_SUITS = {"Жезлы": "воля и действие", "Кубки": "чувства и отношения", "Мечи": "мысли и решения", "Пентакли": "ресурсы и практика"}
TAROT_POSITIONS = [("Прошлое / корень ситуации", "Что сформировало текущий фон?"), ("Настоящее / суть вопроса", "Что происходит сейчас?"), ("Будущее / совет", "Куда направить внимание и какой шаг возможен?")]
TAROT_SPREADS = {
    "three": {
        "title": "Три карты",
        "description": "Прошлое — Настоящее — Будущее / совет",
        "positions": TAROT_POSITIONS,
    },
    "celtic_cross": {
        "title": "Кельтский крест",
        "description": "Глубокий анализ ситуации десятью позициями",
        "positions": [
            ("Суть ситуации", "Что происходит сейчас?"), ("Перекрёсток", "Что помогает или препятствует?"),
            ("Основание", "Какой корень у ситуации?"), ("Прошлое", "Что уже повлияло на неё?"),
            ("Цель", "К чему вы стремитесь сознательно?"), ("Ближайшее развитие", "Какой следующий этап вероятен?"),
            ("Ваша позиция", "Как вы входите в ситуацию?"), ("Внешняя среда", "Как влияют другие люди и обстоятельства?"),
            ("Надежды и опасения", "Чего вы ждёте или избегаете?"), ("Итог / совет", "Какой вывод и шаг наиболее осознанны?"),
        ],
    },
    "choice": {
        "title": "Выбор",
        "description": "Сравнение двух вариантов без фатального вердикта",
        "positions": [
            ("Суть выбора", "Что на самом деле нужно решить?"), ("Вариант A", "Ресурс и цена первого варианта"),
            ("Вариант B", "Ресурс и цена второго варианта"), ("Критерий выбора", "Что важно проверить перед решением?"),
            ("Совет", "Как сохранить свободу выбора и ясность?"),
        ],
    },
}
TAROT_UNSAFE_PATTERNS = (
    "смерт", "умр", "катастроф", "беремен", "аборт", "рак", "диагноз",
    "болезн", "лечен", "лекар", "инвестиц", "вложен", "кредит", "суд",
    "адвокат", "юрид", "уголов", "ставк", "зависим"
)
TAROT_SAFETY_MESSAGE = "Карты не отвечают на вопросы о смерти, диагнозах, лечении, инвестициях и юридических решениях. Переформулируйте вопрос как безопасный вопрос для размышления о своих чувствах, границах или возможных шагах."


def tarot_deck() -> list[dict]:
    deck = [{
        "id": f"major-{number}", "name": card["name"], "number": number, "suit": None,
        "aliases": card["aliases"],
        "arcana": "Старший Аркан", "element": "дух", **card,
        "upright": card["fullUpright"], "reversed": card["fullReversed"],
    } for number, card in MAJOR_ARCANA_BY_NUMBER.items()]
    for suit, theme in MINOR_SUITS.items():
        for number in range(1, 11):
            label = "Туз" if number == 1 else str(number)
            element = {"Жезлы": "огонь", "Кубки": "вода", "Мечи": "воздух", "Пентакли": "земля"}[suit]
            deck.append({"id": f"minor-{suit}-{number}", "name": f"{label} {suit}", "number": number, "suit": suit, "arcana": "Младший Аркан", "element": element, "shortUpright": f"{theme}", "fullUpright": f"начало и развитие темы {theme}", "shortReversed": f"блок {theme}", "fullReversed": f"задержка или переоценка темы {theme}", "upright": f"начало и развитие темы {theme}", "reversed": f"задержка или переоценка темы {theme}"})
        for court in ("Паж", "Рыцарь", "Королева", "Король"):
            element = {"Жезлы": "огонь", "Кубки": "вода", "Мечи": "воздух", "Пентакли": "земля"}[suit]
            deck.append({"id": f"minor-{suit}-{court}", "name": f"{court} {suit}", "number": court, "suit": suit, "arcana": "Младший Аркан", "element": element, "shortUpright": theme, "fullUpright": f"зрелое проявление: {theme}", "shortReversed": f"дисбаланс: {theme}", "fullReversed": f"неуверенное или чрезмерное проявление: {theme}", "upright": f"зрелое проявление: {theme}", "reversed": f"неуверенное или чрезмерное проявление: {theme}"})
    return deck


def personal_arcana(birth_date: str) -> dict:
    parsed = date.fromisoformat(birth_date) if "-" in birth_date else datetime.strptime(birth_date, "%d.%m.%Y").date()
    by_number = MAJOR_ARCANA_BY_NUMBER
    def reduce_arcana(value: int) -> int:
        while value > 22:
            value -= 22
        # In the Rider-Waite convention 0 is the equivalent of 22: the Fool.
        return 22 if value == 0 else value
    personality = reduce_arcana(parsed.day)
    destiny = reduce_arcana(sum(int(char) for char in birth_date if char.isdigit()))
    additional = reduce_arcana(sum(int(char) for char in f"{parsed.month:02d}{parsed.year:04d}"))
    result = {}
    role_descriptions = {
        "personality": "Показывает ваш характер: как вы проявляетесь, принимаете решения и раскрываете сильные стороны.",
        "destiny": "Задаёт общий жизненный урок: какую тему важно проживать осознанно, не перекладывая выбор на обстоятельства.",
        "additional": "Показывает социальную реализацию: как ваши качества проявляются в работе, обществе и совместных проектах.",
    }
    for key, number in (("personality", personality), ("destiny", destiny), ("additional", additional)):
        card = by_number[number]
        result[key] = {
            "number": number,
            "name": card["name"],
            "description": f"{role_descriptions[key]} Ваша карта — «{card['shortUpright']}». В плюсе это проявляется через «{card['shortUpright']}», а в тени — через «{card['shortReversed']}».",
            "light": card["shortUpright"],
            "shadow": card["shortReversed"],
        }
    return result


def build_tarot_prompt(question: str, spread: str, cards: list[dict], arcana: dict | None) -> str:
    return (
        "Ты бережный консультант по Таро. Это инструмент саморефлексии, не предсказание. "
        "Не делай фатальных выводов и не давай медицинских, финансовых или юридических рекомендаций. "
        f"Вопрос: {question}\nСхема: {TAROT_SPREADS[spread]['title']}\n"
        f"Персональные Арканы: {json.dumps(arcana or {}, ensure_ascii=False)}\n"
        f"Карты по позициям: {json.dumps(cards, ensure_ascii=False)}\n"
        "Для каждой карты учти положение, значение позиции и взаимодействие с соседними картами. "
        "Затем дай прямой, но вероятностный ответ на вопрос, общий итог и 2-3 практичных шага. "
        "Верни JSON: cardInterpretations, interactions, answer, summary, recommendations."
    )


def tarot_interpretation(card: dict, position: str, question: str, reversed_card: bool, index: int, cards: list[dict]) -> str:
    meaning = card["fullReversed"] if reversed_card else card["fullUpright"]
    context = {
        "Прошлое / корень ситуации": "Эта карта показывает опыт, привычку или решение, которые создали нынешний фон.",
        "Настоящее / суть вопроса": "Она описывает центральную динамику вопроса и то, что сейчас важно заметить.",
        "Будущее / совет": "Она не фиксирует судьбу, а подсказывает направление внимания и возможный осознанный шаг.",
    }.get(position, f"В позиции «{position}» карта раскрывает отдельный слой вопроса и помогает увидеть его без фатальных выводов.")
    neighbors = [item["name"] for item in cards[max(0, index - 1):index] + cards[index + 1:index + 2]]
    relation = f"В сочетании с {', '.join(neighbors)} карта уточняет общий контекст расклада." if neighbors else "Карта задаёт основной тон расклада."
    return f"Вопрос: «{question}». {context} {card['name']} ({'перевёрнутая' if reversed_card else 'прямая'}) раскрывает тему «{meaning}». {relation} Практический фокус: выберите один небольшой шаг, который зависит от вас."


def tarot_spread(payload: dict) -> dict:
    topic = next((item for item in TAROT_TOPICS if item["id"] == payload.get("topicId")), TAROT_TOPICS[0])
    question = (payload.get("question") or topic["question"]).strip()[:500]
    lowered_question = question.casefold()
    if any(pattern in lowered_question for pattern in TAROT_UNSAFE_PATTERNS):
        raise ValueError(TAROT_SAFETY_MESSAGE)
    spread_id = payload.get("spreadType", "three")
    spread = TAROT_SPREADS.get(spread_id, TAROT_SPREADS["three"])
    deck = tarot_deck()
    drawn = random.SystemRandom().sample(deck, len(spread["positions"]))
    arcana = personal_arcana(payload["birthDate"]) if payload.get("birthDate") else None
    cards = []
    for index, (card, (position, prompt)) in enumerate(zip(drawn, spread["positions"])):
        reversed_card = bool(random.SystemRandom().getrandbits(1))
        cards.append({"position": position, "positionPrompt": prompt, **{key: card[key] for key in ("id", "name", "number", "suit", "arcana", "element")}, "reversed": reversed_card, "meaning": card["fullReversed"] if reversed_card else card["fullUpright"]})
    for index, item in enumerate(cards):
        item["interpretation"] = tarot_interpretation(drawn[index], item["position"], question, item["reversed"], index, cards)
    return {"topic": topic, "spread": {"id": spread_id, "title": spread["title"], "description": spread["description"]}, "question": question, "cards": cards, "personalArcana": arcana, "aiPrompt": build_tarot_prompt(question, spread_id, cards, arcana), "summary": "Карты показывают возможные акценты и взаимосвязи, а не фиксированный исход. Итоговое решение и ответственность остаются у вас.", "disclaimer": TAROT_DISCLAIMER}


def read_data() -> dict:
    with DATA_LOCK:
        if not DATA_FILE.exists():
            return {"users": {}, "interpretations": {}, "events": []}
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def write_data(data: dict) -> None:
    with DATA_LOCK:
        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def reduce_number(value: int) -> int:
    while value > 9 and value not in (11, 22, 33):
        value = sum(int(char) for char in str(value))
    return value


def life_path(birth_date: str) -> int:
    return reduce_number(sum(int(char) for char in birth_date if char.isdigit()))


def name_number(name: str) -> int:
    alphabet = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    return reduce_number(sum((alphabet.index(letter.upper()) % 9) + 1 for letter in name if letter.upper() in alphabet))


def zodiac(month: int, day: int) -> str:
    value = month * 100 + day
    return next(sign for sign, end in SIGNS if value <= end)


def matrix_for(birth_date: str) -> dict[str, int]:
    digits = "".join(char for char in birth_date if char.isdigit())
    return {str(number): digits.count(str(number)) for number in range(1, 10)}


def degree(seed: str, maximum: float = 360) -> float:
    return round(int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF * maximum, 2)


def validate_telegram_init_data(init_data: str) -> dict:
    if not init_data or not os.getenv("BOT_TOKEN"):
        raise ValueError("Telegram initData is required")
    values = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    auth_date = int(values.get("auth_date", "0"))
    if not received_hash or datetime.now(timezone.utc).timestamp() - auth_date > 86400:
        raise ValueError("Expired Telegram initData")
    data_check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", os.environ["BOT_TOKEN"].encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise ValueError("Invalid Telegram initData signature")
    return json.loads(values["user"]) if values.get("user") else {}


def coordinates_for(place: str, payload: dict) -> tuple[float, float]:
    if "latitude" in payload and "longitude" in payload:
        return float(payload["latitude"]), float(payload["longitude"])
    known = {
        "москва": (55.7558, 37.6173), "санкт-петербург": (59.9343, 30.3351),
        "тамбов": (52.7212, 41.4523), "киев": (50.4501, 30.5234),
    }
    return known.get(place.lower(), (55.7558, 37.6173))


def swiss_positions(payload: dict, latitude: float, longitude: float) -> tuple[list[dict], dict]:
    if swe is None or not payload.get("birthTime"):
        return [], {}
    parsed = datetime.fromisoformat(f"{payload['birthDate']}T{payload['birthTime']}")
    julian = swe.julday(parsed.year, parsed.month, parsed.day, parsed.hour + parsed.minute / 60)
    planet_ids = [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO]
    positions = []
    for name, planet_id in zip(PLANETS, planet_ids):
        values, _ = swe.calc_ut(julian, planet_id)
        longitude_value = values[0] % 360
        positions.append({
            "name": name, "sign": SIGNS[int(longitude_value // 30)][0],
            "degree": round(longitude_value % 30, 2), "longitude": round(longitude_value, 4),
            "house": None, "retrograde": values[3] < 0,
            "meaning": PLANET_MEANINGS[name],
        })
    cusps, angles = swe.houses(julian, latitude, longitude, b"P")
    for item in positions:
        item["house"] = int(((item["longitude"] - angles[0]) % 360) // 30) + 1
        item["houseMeaning"] = HOUSE_MEANINGS[item["house"]]
    return positions, {"ascendant": round(angles[0], 4), "mc": round(angles[1], 4), "system": "Placidus"}


def build_interpretation(positions: list[dict], path: int, sign: str, matrix: dict[str, int], aspects: list[dict]) -> dict:
    by_name = {item["name"]: item for item in positions}
    sun, moon = by_name["Солнце"], by_name["Луна"]
    venus, mars = by_name["Венера"], by_name["Марс"]
    dominant = sorted(matrix.items(), key=lambda pair: pair[1], reverse=True)[0]
    sections = [
        {
            "title": "Главная тема",
            "text": f"Ваш базовый стиль — действовать {SIGN_STYLES[sign]}. Число жизненного пути {path} добавляет задачу развивать этот стиль через опыт, а не через ожидание идеальных условий. Важный ориентир: выбирать не самый быстрый вариант, а тот, который можно поддерживать регулярно.",
        },
        {
            "title": "Личность и самореализация",
            "text": f"Солнце в {sun['sign']} в {sun['house']}-м доме показывает, что самоощущение раскрывается в теме «{HOUSE_MEANINGS[sun['house']].lower()}». Вы проявляетесь {SIGN_STYLES[sun['sign']]}. Сильная сторона — видеть, как превратить личное качество в заметный результат. Риск — оценивать себя только по внешнему признанию или продуктивности.",
        },
        {
            "title": "Эмоции и внутренняя опора",
            "text": f"Луна в {moon['sign']} в {moon['house']}-м доме описывает эмоциональную реакцию {SIGN_STYLES[moon['sign']]}. Безопасность для вас связана с темой «{HOUSE_MEANINGS[moon['house']].lower()}». В перегрузе полезно сначала назвать своё состояние и вернуть базовый ритм, а уже потом принимать важные решения.",
        },
        {
            "title": "Мышление и общение",
            "text": f"Меркурий в {by_name['Меркурий']['sign']} в {by_name['Меркурий']['house']}-м доме даёт способ думать и говорить {SIGN_STYLES[by_name['Меркурий']['sign']]}. Лучше всего вы объясняете сложное, когда связываете идею с конкретным примером. Важная практика — фиксировать договорённости письменно и не перегружать собеседника несколькими задачами сразу.",
        },
        {
            "title": "Любовь и близость",
            "text": f"Венера в {venus['sign']} в {venus['house']}-м доме показывает, что симпатия выражается {SIGN_STYLES[venus['sign']]}, а ценность отношений раскрывается в теме «{HOUSE_MEANINGS[venus['house']].lower()}». Вам подходят отношения, где есть одновременно уважение к границам и понятные проявления заботы. Не подменяйте гармонию замалчиванием неудобных вопросов.",
        },
        {
            "title": "Действие, деньги и карьера",
            "text": f"Марс в {mars['sign']} в {mars['house']}-м доме показывает, как вы добиваетесь целей: {SIGN_STYLES[mars['sign']]}. Энергию легче направить в проекты, связанные с темой «{HOUSE_MEANINGS[mars['house']].lower()}». Для финансовых и рабочих решений используйте проверяемые данные, сроки и лимиты; карта не заменяет профессиональную консультацию.",
        },
        {
            "title": "Ресурс и зона внимания",
            "text": f"В психоматрице сильнее всего представлена цифра {dominant[0]} ({dominant[1]} повторения): {NUMBER_MEANINGS[dominant[0]]['text']} Если какой-то цифры нет, это не «приговор», а навык, который полезно развивать намеренно через маленькие повторяемые действия.",
        },
    ]
    aspect_sections = [
        {"title": f"{item['first']} — {item['second']}: {item['type']}", "text": ASPECT_MEANINGS.get(item["type"], "Связь двух тем карты требует осознанного баланса.")}
        for item in aspects
    ]
    actions = [
        "Выберите одну цель на ближайшие 7 дней и заранее определите минимальный ежедневный шаг.",
        f"Важные разговоры проводите с учётом своей эмоциональной реакции Луны в {moon['sign']}: сначала пауза, затем формулировка просьбы.",
        "Раз в неделю сверяйте решения с тремя критериями: польза, цена и соответствие вашим ценностям.",
    ]
    return {"sections": sections, "aspects": aspect_sections, "actions": actions}


def calculate(payload: dict) -> dict:
    parsed = date.fromisoformat(payload["birthDate"])
    place = payload.get("placeName", "Не указан").strip() or "Не указан"
    sign = zodiac(parsed.month, parsed.day)
    latitude, geo_longitude = coordinates_for(place, payload)
    seed = f"{payload['birthDate']}|{payload.get('birthTime', '')}|{place}"
    positions = []
    for index, planet in enumerate(PLANETS):
        planet_longitude = degree(f"{seed}|{planet}")
        positions.append({
            "name": planet,
            "sign": SIGNS[int(planet_longitude // 30)][0],
            "degree": round(planet_longitude % 30, 2),
            "longitude": planet_longitude,
            "house": (int(planet_longitude // 30) % 12) + 1,
            "retrograde": index in (6, 7, 8, 9),
            "meaning": PLANET_MEANINGS[planet],
            "houseMeaning": HOUSE_MEANINGS[(int(planet_longitude // 30) % 12) + 1],
        })
    swiss, swiss_houses = swiss_positions(payload, latitude, geo_longitude)
    calculation_mode = "swiss-ephemeris" if swiss else "demo-fallback"
    if swiss:
        positions = swiss
    aspects = [
        {"first": "Солнце", "second": "Луна", "type": "тригон", "orb": 2.4},
        {"first": "Венера", "second": "Марс", "type": "соединение", "orb": 1.8},
    ]
    path = life_path(payload["birthDate"])
    matrix = matrix_for(payload["birthDate"])
    detailed = build_interpretation(positions, path, sign, matrix, aspects)
    return {
        "birthDate": payload["birthDate"], "birthTime": payload.get("birthTime") or "не указано",
        "place": place, "zodiac": sign, "lifePath": path,
        "personalArcana": personal_arcana(payload["birthDate"]),
        "soulNumber": reduce_number(sum(int(char) for char in payload["birthDate"].replace("-", ""))),
        "nameNumber": name_number(payload.get("fullName", "")) if payload.get("fullName") else None,
        "matrix": matrix, "planets": positions, "aspects": aspects,
        "numberMeanings": NUMBER_MEANINGS,
        "houseMeanings": HOUSE_MEANINGS,
        "houses": swiss_houses or {"ascendant": round(degree(seed + "|asc", 360), 2), "system": "Placidus"},
        "coordinates": {"latitude": latitude, "longitude": geo_longitude},
        "interpretation": detailed["sections"][0]["text"],
        "interpretationSections": detailed["sections"],
        "interpretationAspects": detailed["aspects"],
        "practicalActions": detailed["actions"],
        "disclaimer": DISCLAIMER,
        "calculationMode": calculation_mode,
    }


def forecast(chart: dict, period: str) -> dict:
    key = f"{chart['birthDate']}:{period}:{date.today().isoformat()}"
    luck = int(hashlib.sha256(key.encode()).hexdigest()[:2], 16) % 10 + 1
    texts = {
        "day": "День подходит для спокойного завершения начатого и честного разговора с собой.",
        "week": "Неделя раскрывается через последовательные шаги: не торопите события и фиксируйте приоритеты.",
        "month": "Месяц предлагает укрепить личные границы, пересмотреть ресурсы и оставить место для вдохновения.",
    }
    return {
        "period": period,
        "luck": luck,
        "text": texts.get(period, texts["day"]),
        "areas": {
            "Любовь": "Говорите о чувствах прямо и оставляйте место для взаимности.",
            "Деньги": "Проверьте приоритеты и избегайте решений на эмоциях.",
            "Карьера": "Полезно завершить один важный шаг, а не распыляться.",
            "Здоровье": "Поддержите базовый режим сна, отдыха и спокойного движения.",
        },
        "disclaimer": DISCLAIMER,
    }


def compatibility(first: dict, second: dict) -> dict:
    score = 50 + (life_path(first["birthDate"]) * 7 + life_path(second["birthDate"]) * 3) % 46
    return {"score": score, "summary": "Связь раскрывается через уважение к разным темпам и открытый диалог.", "disclaimer": DISCLAIMER}


def make_interpretation(chart: dict, kind: str) -> str:
    data = read_data()
    cache_key = hashlib.sha256(json.dumps([chart, kind], sort_keys=True).encode()).hexdigest()
    if cache_key in data["interpretations"]:
        return data["interpretations"][cache_key]
    text = f"{chart['interpretation']} Формат: {kind}. Это подсказка для саморефлексии, а не предсказание."
    data["interpretations"][cache_key] = text
    write_data(data)
    return text


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, file_path: Path) -> None:
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(file_path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def payload(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length))

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/health":
            self.send_json(200, {"status": "ok", "service": "astro-app", "mode": "local"})
        elif path == "/api/config":
            self.send_json(200, {"telegram": bool(os.getenv("BOT_TOKEN")), "ai": bool(os.getenv("AI_API_KEY")), "stars": bool(os.getenv("BOT_TOKEN"))})
        elif path == "/api/tarot/topics":
            self.send_json(200, {"topics": TAROT_TOPICS, "spreads": TAROT_SPREADS, "decks": ["classic", "midnight", "gold"], "disclaimer": TAROT_DISCLAIMER})
        elif path.startswith("/api/tarot/history"):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            user_id = query.get("userId", ["local"])[0]
            data = read_data()
            self.send_json(200, {"history": data["users"].get(str(user_id), {}).get("tarotHistory", [])})
        elif path.startswith("/api/tarot/card-of-day"):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            user_id = query.get("userId", ["local"])[0]
            deck = tarot_deck()
            card = deck[int(hashlib.sha256(f"{user_id}:{date.today().isoformat()}".encode()).hexdigest(), 16) % len(deck)]
            self.send_json(200, {"date": date.today().isoformat(), "card": card, "message": "Карта дня — повод для осознанного вопроса, а не готовый прогноз.", "disclaimer": TAROT_DISCLAIMER})
        elif path.startswith("/api/tarot/arcana"):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            birth_date = query.get("birthDate", [""])[0]
            if not birth_date:
                raise ValueError("birthDate is required")
            self.send_json(200, {"birthDate": birth_date, "personalArcana": personal_arcana(birth_date)})
        elif path.startswith("/api/forecast/"):
            self.send_json(200, forecast({"birthDate": "1990-05-17"}, path.rsplit("/", 1)[-1]))
        else:
            relative = "index.html" if path == "/" else path.removeprefix("/")
            file_path = (STATIC / relative).resolve()
            if file_path.is_file() and STATIC.resolve() in file_path.parents:
                self.send_file(file_path)
            else:
                self.send_error(404, "Not found")

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        try:
            payload = self.payload()
            if path == "/api/calculate":
                if not payload.get("birthDate"):
                    raise ValueError("birthDate is required")
                init_data = self.headers.get("X-Telegram-Init-Data", "")
                telegram_user = validate_telegram_init_data(init_data) if init_data else {}
                if telegram_user:
                    payload["telegramUser"] = telegram_user
                    payload["userId"] = str(telegram_user["id"])
                chart = calculate(payload)
                user_id = payload.get("userId", "local")
                data = read_data()
                user = data["users"].setdefault(user_id, {"freeAttemptUsed": False, "subscription": None, "telegramId": user_id})
                if telegram_user:
                    user["telegramId"] = telegram_user["id"]
                    user["firstName"] = telegram_user.get("first_name", "")
                if user["freeAttemptUsed"] and not user.get("subscription"):
                    chart["locked"] = True
                user["freeAttemptUsed"] = True
                user["chart"] = chart
                write_data(data)
                self.send_json(200, chart)
            elif path == "/api/interpretation":
                self.send_json(200, {"text": make_interpretation(payload["chart"], payload.get("kind", "day")), "cached": True})
            elif path == "/api/tarot/spread":
                user_id = str(payload.get("userId", "local"))
                init_data = self.headers.get("X-Telegram-Init-Data", "")
                telegram_user = validate_telegram_init_data(init_data) if init_data else {}
                if telegram_user:
                    user_id = str(telegram_user["id"])
                data = read_data()
                user = data["users"].setdefault(user_id, {"freeAttemptUsed": False, "subscription": None})
                today = date.today().isoformat()
                tarot_usage = user.setdefault("tarotUsage", {"date": today, "count": 0})
                if tarot_usage.get("date") != today:
                    tarot_usage = {"date": today, "count": 0}
                    user["tarotUsage"] = tarot_usage
                if tarot_usage["count"] >= 1 and not user.get("subscription"):
                    self.send_json(402, {"error": "daily_tarot_limit", "message": "Бесплатный расклад на сегодня уже использован.", "disclaimer": TAROT_DISCLAIMER})
                    return
                if user.get("chart", {}).get("birthDate"):
                    payload["birthDate"] = user["chart"]["birthDate"]
                spread = tarot_spread(payload)
                tarot_usage["count"] += 1
                user.setdefault("tarotHistory", []).append({"createdAt": datetime.utcnow().isoformat(), "spread": spread})
                write_data(data)
                self.send_json(200, spread)
            elif path == "/api/compatibility":
                self.send_json(200, compatibility(payload["first"], payload["second"]))
            elif path == "/api/subscribe":
                user_id = payload.get("userId", "local")
                data = read_data()
                data["users"].setdefault(user_id, {})["subscription"] = {
                    "plan": payload.get("plan", "monthly"), "status": "active",
                    "expiresAt": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                    "paymentMode": "demo-stars",
                }
                write_data(data)
                self.send_json(200, {"status": "active", "plan": payload.get("plan", "monthly"), "expiresAt": data["users"][user_id]["subscription"]["expiresAt"], "paymentMode": "demo-stars"})
            elif path == "/api/invoice":
                if not os.getenv("BOT_TOKEN"):
                    raise ValueError("BOT_TOKEN is not configured")
                user_id = str(payload.get("userId", "local"))
                request_body = json.dumps({
                    "title": "Astro App · месяц",
                    "description": "Персональные прогнозы, совместимость и ежедневные подсказки.",
                    "payload": f"subscription:monthly:{user_id}",
                    "currency": "XTR",
                    "prices": [{"label": "Месячная подписка", "amount": int(os.getenv("MONTHLY_STARS", "300"))}],
                }).encode()
                request = urllib.request.Request(
                    f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}/createInvoiceLink",
                    data=request_body, headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=10) as response:
                    invoice = json.loads(response.read())
                if not invoice.get("ok"):
                    raise ValueError("Telegram invoice creation failed")
                self.send_json(200, {"invoiceUrl": invoice["result"]})
            elif path == "/api/analytics":
                data = read_data()
                data["events"].append({"name": payload.get("name"), "at": datetime.utcnow().isoformat()})
                write_data(data)
                self.send_json(200, {"ok": True})
            elif path == "/api/geocode":
                query = urllib.parse.quote(payload.get("query", ""))
                request = urllib.request.Request(f"https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q={query}", headers={"User-Agent": "astro-app-local/1.0"})
                with urllib.request.urlopen(request, timeout=5) as response:
                    result = json.loads(response.read())
                self.send_json(200, {"results": result})
            else:
                self.send_error(404, "Not found")
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error)})
        except Exception as error:
            self.send_json(502, {"error": f"External service unavailable: {error}"})

    def do_DELETE(self) -> None:
        if urllib.parse.urlparse(self.path).path != "/api/account":
            self.send_error(404, "Not found")
            return
        try:
            user_id = self.payload().get("userId", "local")
            data = read_data()
            data["users"].pop(user_id, None)
            write_data(data)
            self.send_json(200, {"deleted": True})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error)})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"Astro App running at http://127.0.0.1:{port}")
    host = os.getenv("HOST", "127.0.0.1")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
