import json
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from wiki_utils import clean_text, embedding_element_text, save_json


BASE_URL = "https://deadbydaylight.wiki.gg"
PERKS_URL = f"{BASE_URL}/wiki/Perks"


def get_page_soup(url):
    headers = {
        "User-Agent": "DbDBuildGenerator/0.1 (educational project)",
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def find_heading(content, heading_name, tag_name="h2"):
    for heading in content.find_all(tag_name, recursive=False):
        if clean_text(heading) == heading_name:
            return heading

    return None


def parse_perk_table(table, role):
    perks = []
    rows = table.select("tr")[1:]

    for row in rows:
        cells = row.select("th, td")

        if len(cells) != 4:
            raise ValueError(f"Unexpected number of columns in {role} perk table")

        icon = cells[0].find("img")
        name = clean_text(cells[1])
        description = clean_text(cells[2])
        character = clean_text(cells[3])

        if character == ". All":
            character = "General"

        if icon is None or not icon.get("src"):
            raise ValueError(f"Icon URL is missing for perk: {name}")

        if not name or not description or not character:
            raise ValueError(f"Required data is missing for perk: {name}")

        perk = {
            "name": name,
            "role": role,
            "character": character,
            "description": description,
            "icon_url": urljoin(BASE_URL, icon["src"]),
        }
        perks.append(perk)

    return perks


def parse_perk_list(content):
    tables = content.select("table.wikitable.overflowScroll.sortable")

    if len(tables) != 2:
        raise ValueError(f"Expected 2 perk tables, found {len(tables)}")

    survivor_perks = parse_perk_table(tables[0], "Survivor")
    killer_perks = parse_perk_table(tables[1], "Killer")

    return survivor_perks + killer_perks


def parse_overview_perk_slots(content):
    overview = find_heading(content, "Overview")

    if overview is None:
        raise ValueError("Overview heading was not found")

    text_parts = []
    collect_perk_slots = False
    element = overview.find_next_sibling()

    while element is not None and element.name != "h2":
        if element.name == "h3":
            heading_text = clean_text(element)

            if heading_text == "Perk Slots":
                collect_perk_slots = True
                text_parts.append(heading_text)
            else:
                # Skip Obtaining Perks and any other Overview subsections
                collect_perk_slots = False
        elif collect_perk_slots and element.name in ["p", "ul", "ol", "dl"]:
            text = clean_text(element)

            if text:
                text_parts.append(text)
        elif (
            not collect_perk_slots
            and element.name == "p"
            and not text_parts
        ):
            # Keep the short Overview intro paragraph before Perk Slots
            text = clean_text(element)

            if text:
                text_parts.append(text)

        element = element.find_next_sibling()

    if "Perk Slots" not in text_parts:
        raise ValueError("Perk Slots subsection was not found")

    return "\n\n".join(text_parts)


def detect_available_for(text):
    lowered = text.lower()

    if "available to both" in lowered or "both killers and survivors" in lowered:
        return "Both"

    if "unique to survivors" in lowered:
        return "Survivors"

    if "unique to killers" in lowered:
        return "Killers"

    return None


def parse_perk_classes_summary(content):
    classes_heading = find_heading(content, "Perk Classes")

    if classes_heading is None:
        raise ValueError("Perk Classes heading was not found")

    classes = []
    intro_parts = []
    current_class = None
    element = classes_heading.find_next_sibling()

    while element is not None and element.name != "h2":
        if element.name == "h3":
            if current_class is not None:
                classes.append(current_class)

            class_name = clean_text(element)
            current_class = {
                "name": class_name,
                "url": None,
                "available_for": None,
                "summary": "",
            }
        elif current_class is None and element.name == "p":
            text = clean_text(element)

            if text:
                intro_parts.append(text)
        elif current_class is not None:
            if element.name == "dl":
                link = element.find("a", href=True)

                if link is not None:
                    current_class["url"] = urljoin(BASE_URL, link["href"])

            if element.name in ["p", "ul", "ol", "dl"]:
                text = clean_text(element)

                if text:
                    if current_class["summary"]:
                        current_class["summary"] += "\n\n" + text
                    else:
                        current_class["summary"] = text

                    if current_class["available_for"] is None:
                        current_class["available_for"] = detect_available_for(text)

        element = element.find_next_sibling()

    if current_class is not None:
        classes.append(current_class)

    for perk_class in classes:
        if perk_class["url"] is None:
            raise ValueError(f"Detail URL missing for class: {perk_class['name']}")

        if perk_class["available_for"] is None:
            raise ValueError(
                f"Could not detect available_for for class: {perk_class['name']}"
            )

    return {
        "intro": "\n\n".join(intro_parts),
        "classes": classes,
    }


def parse_perk_class_page(perk_class):
    soup = get_page_soup(perk_class["url"])
    content = soup.select_one("#mw-content-text .mw-parser-output")

    if content is None:
        raise ValueError(f"Content missing for class page: {perk_class['name']}")

    stop_heading = find_heading(content, perk_class["name"])

    if stop_heading is None:
        raise ValueError(
            f"Perk list heading '{perk_class['name']}' was not found on detail page"
        )

    text_parts = []

    for element in content.children:
        if element == stop_heading:
            break

        if element.name not in ["h2", "h3", "h4", "p", "ul", "ol", "dl", "table", "blockquote"]:
            continue

        # Skip table of contents
        if element.name == "div" or (
            element.get("id") == "toc" if element.name == "div" else False
        ):
            continue

        if element.name == "div":
            continue

        text = embedding_element_text(element)

        if text and text != "Contents" and not text.startswith("Contents "):
            text_parts.append(text)

    detail_text = "\n\n".join(text_parts)

    if not detail_text:
        raise ValueError(f"Empty detail text for class: {perk_class['name']}")

    return {
        "name": perk_class["name"],
        "url": perk_class["url"],
        "available_for": perk_class["available_for"],
        "summary": perk_class["summary"],
        "detail_text": detail_text,
    }


def parse_embedding_texts(content):
    overview_perk_slots = parse_overview_perk_slots(content)
    classes_summary = parse_perk_classes_summary(content)

    detailed_classes = []

    for perk_class in classes_summary["classes"]:
        print(f"Parsing perk class page: {perk_class['name']}...")
        detailed_classes.append(parse_perk_class_page(perk_class))

    return {
        "overview_perk_slots": overview_perk_slots,
        "perk_classes_intro": classes_summary["intro"],
        "perk_classes": detailed_classes,
    }


def shorten_text(text, limit=500):
    if len(text) > limit:
        return text[:limit] + "..."

    return text


def print_samples(perks, embedding_texts):
    survivor_perks = [perk for perk in perks if perk["role"] == "Survivor"]
    killer_perks = [perk for perk in perks if perk["role"] == "Killer"]
    survivor_general = [perk for perk in survivor_perks if perk["character"] == "General"][0]
    killer_general = [perk for perk in killer_perks if perk["character"] == "General"][0]
    perk_samples = survivor_perks[:2] + [survivor_general, killer_perks[0], killer_general]

    class_samples = []

    for perk_class in embedding_texts["perk_classes"]:
        class_samples.append(
            {
                "name": perk_class["name"],
                "url": perk_class["url"],
                "available_for": perk_class["available_for"],
                "summary": perk_class["summary"],
                "detail_text_sample": shorten_text(perk_class["detail_text"]),
            }
        )

    print(f"Parsed {len(perks)} perks.")
    print(json.dumps(perk_samples, indent=2, ensure_ascii=False))
    print()
    print("OVERVIEW / PERK SLOTS")
    print(embedding_texts["overview_perk_slots"])
    print()
    print("PERK CLASSES INTRO")
    print(embedding_texts["perk_classes_intro"])
    print()
    print(f"PERK CLASSES ({len(class_samples)})")
    print(json.dumps(class_samples, indent=2, ensure_ascii=False))


def parse_all_perks_data():
    soup = get_page_soup(PERKS_URL)
    content = soup.select_one("#mw-content-text .mw-parser-output")

    if content is None:
        raise ValueError("Perks page content was not found")

    perks = parse_perk_list(content)
    embedding_texts = parse_embedding_texts(content)

    return {
        "perks": perks,
        "embedding_texts": embedding_texts,
    }


def main():
    data = parse_all_perks_data()
    print_samples(data["perks"], data["embedding_texts"])
    save_json(data, "perks.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
