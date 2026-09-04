"""The Lucide icon set is defined once in Python (`schemas.ALLOWED_ICONS`) and
copied by hand into the frontend's icon-registry.tsx, since a Python list and
a TypeScript component map cannot share one source across languages. This is
the automatic check that catches the two drifting, instead of relying on
whoever edits one file to remember the other.
"""

import re
from pathlib import Path

from schemas import ALLOWED_ICONS


REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent / "frontend" / "lib" / "icon-registry.tsx"
)


def registry_keys():
    source = REGISTRY_PATH.read_text(encoding="utf-8")
    block = re.search(r"const registry:.*?=\s*\{(.*?)\n\}", source, re.DOTALL).group(1)

    return set(re.findall(r'^\s*"?([\w-]+)"?:', block, re.MULTILINE))


def test_the_frontend_icon_registry_matches_the_backend_allow_list():
    assert registry_keys() == set(ALLOWED_ICONS)
