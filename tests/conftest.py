"""Golden fixtures for the grounding layer.

A small hand-written world instead of the real 964 KB data dump: fast,
deterministic, and every entity here exists to make one validation rule
observable.
"""

import pytest
from fake_mongo import FakeDb

from naming import killer_search_keys, perk_search_keys, survivor_search_keys


PERKS = [
    {
        "name": "Sprint Burst",
        "role": "Survivor",
        "character": "Meg",
        "description": "Break into a sprint.",
        "icon_url": "https://wiki.example/sprint.png",
        "icon_path": "/media/perks/sprint-burst.png",
    },
    {
        "name": "Adrenaline",
        "role": "Survivor",
        "character": "Meg",
        "description": "Heal one Health State.",
        "icon_url": "https://wiki.example/adrenaline.png",
    },
    {
        "name": "Windows of Opportunity",
        "role": "Survivor",
        "character": "Kate",
        "description": "Reveal pallets and windows.",
        "icon_url": "https://wiki.example/windows.png",
    },
    # Diacritics: the model and the user both type "Deja Vu".
    {
        "name": "Déjà Vu",
        "role": "Survivor",
        "character": "General",
        "description": "Reveal three Generators.",
        "icon_url": "https://wiki.example/dejavu.png",
    },
    {
        "name": "Hex: Ruin",
        "role": "Killer",
        "character": "Hag",
        "description": "Generators regress.",
        "icon_url": "https://wiki.example/ruin.png",
    },
    {
        "name": "Lethal Pursuer",
        "role": "Killer",
        "character": "Nemesis",
        "description": "See Survivor auras at the start.",
        "icon_url": "https://wiki.example/lethal.png",
    },
    {
        "name": "Corrupt Intervention",
        "role": "Killer",
        "character": "Plague",
        "description": "Block the three farthest Generators.",
        "icon_url": "https://wiki.example/corrupt.png",
    },
    {
        "name": "Barbecue & Chilli",
        "role": "Killer",
        "character": "Cannibal",
        "description": "Reveal distant Survivors after a hook.",
        "icon_url": "https://wiki.example/bbq.png",
    },
    {
        "name": "Nowhere to Hide",
        "role": "Killer",
        "character": "Trapper",
        "description": "Reveal generator auras after a hit.",
        "icon_url": "https://wiki.example/nowhere.png",
    },
    {
        "name": "Deadlock",
        "role": "Killer",
        "character": "Executioner",
        "description": "Block the most-progressed Generator.",
        "icon_url": "https://wiki.example/deadlock.png",
    },
    {
        "name": "Kindred",
        "role": "Survivor",
        "character": "Claudette",
        "description": "See the Killer's aura while on the hook.",
        "icon_url": "https://wiki.example/kindred.png",
    },
    {
        "name": "Iron Will",
        "role": "Survivor",
        "character": "David",
        "description": "Reduces grunts of pain.",
        "icon_url": "https://wiki.example/ironwill.png",
    },
]

KILLERS = [
    {
        "name": "Anna",
        "metadata": {
            "Title": "The Huntress",
            "Name": "Anna",
            "Game Alias(es)": '"Bear"',
            "portrait_url": "https://wiki.example/huntress.png",
            "portrait_path": "/media/killers/the-huntress.png",
        },
        "power": {"name": "Hunting Hatchets", "description": "Throw hatchets."},
        "addons": [
            {"name": "Iridescent Head", "description": "One hatchet.", "rarity": "Ultra Rare"},
            {"name": "Infantry Belt", "description": "Carry more hatchets.", "rarity": "Rare"},
            {"name": "Soldier's Puttee", "description": "Reload faster.", "rarity": "Common"},
        ],
    },
    {
        "name": "Bubba Sawyer",
        "metadata": {
            "Title": "The Cannibal",
            "Name": "Bubba Sawyer",
            "Game Alias(es)": '"Leatherface"',
            "portrait_url": "https://wiki.example/cannibal.png",
        },
        "power": {"name": "Bubba's Chainsaw", "description": "Sweep with a chainsaw."},
        "addons": [
            {"name": "Depth Gauge Rake", "description": "Longer Tantrum.", "rarity": "Common"},
            {"name": "Carburettor Tuning Guide", "description": "Faster sweep.", "rarity": "Rare"},
            {"name": "Grisly Chains", "description": "Longer chainsaw dash.", "rarity": "Uncommon"},
        ],
    },
    {
        "name": "Michael Myers",
        "metadata": {
            "Title": "The Shape",
            "Name": "Michael Myers",
            "portrait_url": "https://wiki.example/shape.png",
        },
        "power": {"name": "Evil Within", "description": "Stalk Survivors."},
        "addons": [
            {"name": "Judith's Tombstone", "description": "Mori Survivors.", "rarity": "Ultra Rare"}
        ],
    },
    {
        "name": "Sadako Yamamura",
        "metadata": {
            "Title": "The Onryō",
            "Name": "Sadako Yamamura",
            "portrait_url": "https://wiki.example/onryo.png",
        },
        "power": {"name": "Deluge of Fears", "description": "Teleport to televisions."},
        "addons": [
            {"name": "Ring Drawing", "description": "Condemn faster.", "rarity": "Very Rare"}
        ],
    },
    {
        "name": "Unknown",
        "metadata": {
            "Title": "The Unknown",
            "portrait_url": "https://wiki.example/unknown.png",
        },
        "power": {"name": "Unknown's Power", "description": "Throw UVX."},
        "addons": [
            {"name": "Blurry Photo", "description": "Faster hallucination.", "rarity": "Common"}
        ],
    },
]

SURVIVORS = [
    {
        "name": "Meg Thomas",
        "metadata": {"Name": "Meg Thomas", "portrait_url": "https://wiki.example/meg.png"},
    },
    {
        "name": "Kate Denson",
        "metadata": {"Name": "Kate Denson", "portrait_url": "https://wiki.example/kate.png"},
    },
]

ITEMS_ADDONS = [
    {
        "type_name": "Med-Kits",
        "items": [
            {"name": "Emergency Med-Kit", "description": "Heal fast.", "rarity": "Very Rare"},
            {"name": "First Aid Kit", "description": "Heal.", "rarity": "Uncommon"},
        ],
        "addons": [
            {"name": "Gauze Roll", "description": "Faster healing.", "rarity": "Common"},
            {"name": "Medical Gauze", "description": "More charges.", "rarity": "Uncommon"},
            {"name": "Butterfly Tape", "description": "Better skill checks.", "rarity": "Rare"},
        ],
    },
    {
        "type_name": "Toolboxes",
        "items": [{"name": "Toolbox", "description": "Repair.", "rarity": "Common"}],
        "addons": [
            {"name": "Wire Spool", "description": "More charges.", "rarity": "Uncommon"},
            {"name": "Clean Rag", "description": "Faster repair.", "rarity": "Common"},
        ],
    },
]


def indexed_db(perks, killers, survivors, items_addons):
    """A FakeDb carrying the same lookup keys mongo_loader stores at ingest."""
    for perk in perks:
        perk["search_keys"] = perk_search_keys(perk)

    for killer in killers:
        killer["search_keys"], killer["phrase_keys"] = killer_search_keys(killer)

    for survivor in survivors:
        survivor["search_keys"] = survivor_search_keys(survivor)

    return FakeDb(
        {
            "perks": perks,
            "killers": killers,
            "survivors": survivors,
            "items_addons": items_addons,
        }
    )


@pytest.fixture
def db():
    return indexed_db(PERKS, KILLERS, SURVIVORS, ITEMS_ADDONS)


def choices(*names):
    """Perk or addon choices from bare names, for tests that only assert names."""
    return [{"name": name, "reason": f"why {name}"} for name in names]


def survivor_build(**overrides):
    """A valid Survivor build payload, ready for DbDBuildSchema."""
    build = {
        "build_title": "Швидкий ремонт",
        "character_name": "Meg Thomas",
        "role": "Survivor",
        "difficulty_rating": 2,
        "perks": [
            {"name": "Sprint Burst", "reason": "Відрив на початку чейсу."},
            {"name": "Adrenaline", "reason": "Друге життя на фінальному генераторі."},
            {"name": "Windows of Opportunity", "reason": "Показує безпечні лупи."},
            {"name": "Déjà Vu", "reason": "Підсвічує три згенеровані генератори."},
        ],
        "item_kits": [
            {
                "kit_title": "Лікування",
                "item_name": "Emergency Med-Kit",
                "item_reason": "Швидке самолікування після чейсу.",
                "addons": [
                    {"name": "Gauze Roll", "reason": "Пришвидшує лікування."},
                    {"name": "Medical Gauze", "reason": "Додає зарядів."},
                ],
            },
            {
                "kit_title": "Ремонт",
                "item_name": "Toolbox",
                "item_reason": "Тиск на генератори.",
                "addons": [
                    {"name": "Wire Spool", "reason": "Більше зарядів."},
                    {"name": "Clean Rag", "reason": "Швидший ремонт."},
                ],
            },
        ],
        "axes": [
            {"axis": "Chase", "score": 4, "reason": "Sprint Burst і вікна."},
            {"axis": "Information", "score": 2, "reason": "Мало інформації."},
            {"axis": "Objective", "score": 3, "reason": "Toolbox допомагає."},
            {"axis": "Team Utility", "score": 2, "reason": "Білд переважно соло."},
        ],
        "synergies": [
            {
                "entities": ["Sprint Burst", "Windows of Opportunity"],
                "explanation": "Відрив плюс знання найближчого лупа.",
            },
            {
                "entities": ["Emergency Med-Kit", "Gauze Roll"],
                "explanation": "Найшвидше самолікування в грі.",
            },
        ],
        "target_audience": [
            {"title": "Новачки", "description": "Простий білд.", "icon": "users"},
            {"title": "Соло", "description": "Не потребує команди.", "icon": "eye"},
        ],
        "tactics": {
            "early_game": [{"title": "Ремонт", "description": "Почни з генератора."}],
            "mid_game": [{"title": "Чейс", "description": "Використовуй вікна."}],
            "late_game": [{"title": "Втеча", "description": "Тримайся біля виходу."}],
        },
        "pros": [
            {"label": "Швидкість", "icon": "zap", "tooltip_text": "Сильна мобільність."},
            {"label": "Гнучкість", "icon": "gauge", "tooltip_text": "Працює на будь-якій мапі."},
        ],
        "cons": [
            {"label": "Разовий", "icon": "timer", "tooltip_text": "Sprint Burst має відкат."},
            {"label": "Без інфо", "icon": "radar", "tooltip_text": "Мало інформації про вбивцю."},
        ],
        "counter_perks": [
            {
                "perk_name": "Hex: Ruin",
                "explanation": "Регресія карає повільний ремонт.",
            },
            {
                "perk_name": "Lethal Pursuer",
                "explanation": "Ранній аура-рід ламає стелс на старті.",
            },
            {
                "perk_name": "Corrupt Intervention",
                "explanation": "Змушує починати з невигідних генераторів.",
            },
            {
                "perk_name": "Barbecue & Chilli",
                "explanation": "Видає позиції після кожного гака.",
            },
            {
                "perk_name": "Nowhere to Hide",
                "explanation": "Видає генератори одразу після влучення.",
            },
            {
                "perk_name": "Deadlock",
                "explanation": "Блокує генератор, на якому найбільше прогресу.",
            },
        ],
        "counter_killers": [
            {
                "killer_name": name,
                "difficulty_level": "High Difficulty",
                "explanation": "Тисне на позиціювання.",
            }
            for name in [
                "The Huntress",
                "The Cannibal",
                "The Shape",
                "The Onryō",
                "The Unknown",
            ]
        ],
    }
    build.update(overrides)
    return build


def killer_build(**overrides):
    """A valid Killer build payload, ready for DbDBuildSchema."""
    build = {
        "build_title": "Тиск на генератори",
        "character_name": "The Huntress",
        "role": "Killer",
        "difficulty_rating": 3,
        "perks": [
            {"name": "Hex: Ruin", "reason": "Регресія без патрулювання."},
            {"name": "Lethal Pursuer", "reason": "Перший чейс одразу зі старту."},
            {"name": "Corrupt Intervention", "reason": "Блокує далекі генератори."},
            {"name": "Barbecue & Chilli", "reason": "Інформація після гака."},
        ],
        "item_kits": [
            {
                "kit_title": "Дальній бій",
                "item_name": None,
                "item_reason": None,
                "addons": [
                    {"name": "Iridescent Head", "reason": "Ваншот сокирою."},
                    {"name": "Infantry Belt", "reason": "Більше сокир у запасі."},
                ],
            },
            {
                "kit_title": "Швидке перезаряджання",
                "item_name": None,
                "item_reason": None,
                "addons": [
                    {"name": "Soldier's Puttee", "reason": "Швидше перезаряджання."},
                    {"name": "Infantry Belt", "reason": "Більше сокир у запасі."},
                ],
            },
        ],
        "axes": [
            {"axis": "Chase", "score": 5, "reason": "Сокири закривають луп."},
            {"axis": "Map Pressure", "score": 3, "reason": "Повільне пересування."},
            {"axis": "Slowdown", "score": 4, "reason": "Ruin і Corrupt."},
            {"axis": "Anti-Loop", "score": 4, "reason": "Кидок через укриття."},
        ],
        "synergies": [
            {
                "entities": ["Hunting Hatchets", "Iridescent Head"],
                "explanation": "Сила вбивці перетворюється на ваншот.",
            },
            {
                "entities": ["Lethal Pursuer", "Barbecue & Chilli"],
                "explanation": "Інформація на старті і після кожного гака.",
            },
        ],
        "target_audience": [
            {"title": "Досвідчені", "description": "Треба вміти кидати.", "icon": "target"},
            {"title": "Ранкед", "description": "Сильно в соло-кю.", "icon": "trophy"},
        ],
        "tactics": {
            "early_game": [{"title": "Контроль", "description": "Тримай центр мапи."}],
            "mid_game": [{"title": "Тиск", "description": "Не відпускай генератори."}],
            "late_game": [{"title": "Закриття", "description": "Патруль виходів."}],
        },
        "pros": [
            {"label": "Тиск", "icon": "zap", "tooltip_text": "Постійний тиск на мапу."},
            {"label": "Дальність", "icon": "target", "tooltip_text": "Дістає крізь укриття."},
        ],
        "cons": [
            {"label": "Складність", "icon": "gauge", "tooltip_text": "Потрібна точність."},
            {"label": "Аддони", "icon": "cog", "tooltip_text": "Залежить від рідких аддонів."},
        ],
        "counter_perks": [
            {
                "perk_name": "Sprint Burst",
                "explanation": "Миттєвий відрив псує перший чейс.",
            },
            {
                "perk_name": "Windows of Opportunity",
                "explanation": "Виживший завжди знає найближчий безпечний луп.",
            },
            {
                "perk_name": "Adrenaline",
                "explanation": "Повертає здоров'я саме тоді, коли ви тиснете.",
            },
            {
                "perk_name": "Déjà Vu",
                "explanation": "Одразу видає, які генератори варто патрулювати.",
            },
            {
                "perk_name": "Kindred",
                "explanation": "Команда бачить вас і одна одну біля гака.",
            },
            {
                "perk_name": "Iron Will",
                "explanation": "Гасить звукові підказки під час чейсу.",
            },
        ],
        "counter_killers": None,
    }
    build.update(overrides)
    return build
