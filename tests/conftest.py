"""Golden fixtures for the grounding layer.

A small hand-written world instead of the real 964 KB data dump: fast,
deterministic, and every entity here exists to make one validation rule
observable.
"""

import pytest
from fake_mongo import FakeDb


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


@pytest.fixture
def db():
    return FakeDb(
        {
            "perks": PERKS,
            "killers": KILLERS,
            "survivors": SURVIVORS,
            "items_addons": ITEMS_ADDONS,
        }
    )


def survivor_build(**overrides):
    """A valid Survivor build payload, ready for DbDBuildSchema."""
    build = {
        "build_title": "Швидкий ремонт",
        "character_name": "Meg Thomas",
        "role": "Survivor",
        "difficulty_rating": 2,
        "build_score": 8,
        "perks": ["Sprint Burst", "Adrenaline", "Windows of Opportunity", "Déjà Vu"],
        "item_kits": [
            {
                "kit_title": "Лікування",
                "item_name": "Emergency Med-Kit",
                "addons": ["Gauze Roll", "Medical Gauze"],
            },
            {
                "kit_title": "Ремонт",
                "item_name": "Toolbox",
                "addons": ["Wire Spool", "Clean Rag"],
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
        "build_score": 7,
        "perks": [
            "Hex: Ruin",
            "Lethal Pursuer",
            "Corrupt Intervention",
            "Barbecue & Chilli",
        ],
        "item_kits": [
            {
                "kit_title": "Дальній бій",
                "item_name": None,
                "addons": ["Iridescent Head", "Infantry Belt"],
            },
            {
                "kit_title": "Швидке перезаряджання",
                "item_name": None,
                "addons": ["Soldier's Puttee", "Infantry Belt"],
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
        "counter_killers": None,
    }
    build.update(overrides)
    return build
