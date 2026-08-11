import json
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from wiki_utils import clean_text, embedding_element_text, parse_rarity, save_json


BASE_URL = "https://deadbydaylight.wiki.gg"
KILLERS_URL = f"{BASE_URL}/wiki/Killers"
SAMPLE_KILLER_NAME = "Caleb Quinn"

SKIP_METADATA_KEYS = {
    "Voice Actor",
    "Breathing",
    "Menu Music",
    "Terror Radius Music",
    "Cost",
}


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


def find_heading_startswith(content, prefix, tag_name="h3"):
    for heading in content.find_all(tag_name):
        text = clean_text(heading)

        if text.startswith(prefix):
            return heading

    return None


def parse_global_intro(content):
    list_heading = find_heading(content, "List of Killers")

    if list_heading is None:
        raise ValueError("List of Killers heading was not found")

    intro_parts = []
    allowed_tags = ["h2", "h3", "p", "ul", "ol", "dl"]

    for element in content.children:
        if element.name not in allowed_tags:
            continue

        text = clean_text(element)

        if text:
            intro_parts.append(text)

        if element == list_heading:
            description = list_heading.find_next_sibling("p")

            if description is not None:
                intro_parts.append(clean_text(description))

            break

    return "\n\n".join(intro_parts)


def parse_killer_links(content):
    list_heading = find_heading(content, "List of Killers")

    if list_heading is None:
        raise ValueError("List of Killers heading was not found")

    description = list_heading.find_next_sibling("p")

    if description is None:
        raise ValueError("List of Killers description was not found")

    killer_list = description.find_next_sibling("div")

    if killer_list is None:
        raise ValueError("Killer list was not found")

    killer_links = []

    for link in killer_list.select("a[href]"):
        name = clean_text(link)

        if not name:
            continue

        killer = {
            "name": name,
            "url": urljoin(BASE_URL, link["href"]),
        }

        if killer not in killer_links:
            killer_links.append(killer)

    return killer_links


def should_skip_metadata_key(key):
    if key in SKIP_METADATA_KEYS:
        return True

    lowered = key.lower()

    if "voice" in lowered or "music" in lowered or "breathing" in lowered:
        return True

    return False


def parse_killer_metadata(soup):
    infobox = soup.select_one(
        "table.infoboxtable.charInfoboxTable.killerInfobox"
    )

    if infobox is None:
        raise ValueError("Killer infobox was not found")

    title = infobox.select_one("tr.infoboxTitle")
    portrait = infobox.select_one(".charInfoboxImage img")

    if title is None:
        raise ValueError("Killer name was not found")

    if portrait is None or not portrait.get("src"):
        raise ValueError("Killer portrait URL was not found")

    metadata = {
        "Title": clean_text(title),
        "portrait_url": urljoin(BASE_URL, portrait["src"]),
    }

    for row in infobox.select("tr"):
        if row.select("audio"):
            continue

        key_cell = row.select_one("td.titleColumn")

        if key_cell is None:
            continue

        value_cell = key_cell.find_next_sibling("td")

        if value_cell is None:
            continue

        key = clean_text(key_cell)
        value = clean_text(value_cell)

        if should_skip_metadata_key(key):
            continue

        if key and value:
            metadata[key] = value

    return metadata


def parse_text_sections(content):
    section_names = ["Overview", "Lore", "Trivia"]
    sections = {}

    for section_name in section_names:
        heading = find_heading(content, section_name)

        if heading is None:
            sections[section_name] = None
            continue

        subheadings = []
        text_parts = []
        skip_unwanted = False
        element = heading.find_next_sibling()

        while element is not None and element.name != "h2":
            if element.name == "h3":
                subheading = clean_text(element)

                if subheading.startswith("Voice Actor"):
                    skip_unwanted = True
                    element = element.find_next_sibling()
                    continue

                skip_unwanted = False
                subheadings.append(subheading)
                text_parts.append(subheading)
            elif (
                not skip_unwanted
                and element.name in ["p", "ul", "ol", "dl", "table", "blockquote"]
            ):
                text = embedding_element_text(element)

                if text:
                    text_parts.append(text)

            element = element.find_next_sibling()

        sections[section_name] = {
            "subheadings": subheadings,
            "text": "\n\n".join(text_parts),
        }

    return sections


def parse_power(content):
    power_heading = find_heading_startswith(content, "Power:")

    if power_heading is None:
        raise ValueError("Power heading was not found")

    power_name = clean_text(power_heading).replace("Power:", "", 1).strip()
    icon_url = None
    text_parts = []
    element = power_heading.find_next_sibling()

    while element is not None and element.name not in ["h2", "h3"]:
        if element.name == "h4" and clean_text(element) == "Power Trivia":
            break

        if element.name == "div" and icon_url is None:
            icon = element.find("img")

            if icon is not None and icon.get("src"):
                icon_url = urljoin(BASE_URL, icon["src"])

        if element.name in ["p", "ul", "ol", "dl", "table", "blockquote"]:
            text = embedding_element_text(element)

            if text:
                text_parts.append(text)

        element = element.find_next_sibling()

    return {
        "name": power_name,
        "icon_url": icon_url,
        "description": "\n\n".join(text_parts),
    }


def parse_addons(content):
    addons_heading = find_heading_startswith(content, "Add-ons for")

    if addons_heading is None:
        raise ValueError("Add-ons heading was not found")

    table = addons_heading.find_next_sibling("table")

    if table is None:
        raise ValueError("Add-ons table was not found")

    addons = []
    rows = table.select("tr")[1:]

    for row in rows:
        cells = row.select("th, td")

        if len(cells) != 3:
            raise ValueError("Unexpected number of columns in Add-ons table")

        icon = cells[0].find("img")
        name = clean_text(cells[1])
        description = clean_text(cells[2])
        rarity = parse_rarity(row)

        if icon is None or not icon.get("src"):
            raise ValueError(f"Add-on icon URL is missing for: {name}")

        if not name or not description:
            raise ValueError(f"Required add-on data is missing for: {name}")

        addons.append(
            {
                "name": name,
                "description": description,
                "rarity": rarity,
                "icon_url": urljoin(BASE_URL, icon["src"]),
            }
        )

    return addons


def parse_one_killer(killer):
    soup = get_page_soup(killer["url"])
    content = soup.select_one("#mw-content-text .mw-parser-output")

    if content is None:
        raise ValueError("Killer page content was not found")

    return {
        "name": killer["name"],
        "url": killer["url"],
        "metadata": parse_killer_metadata(soup),
        "sections": parse_text_sections(content),
        "power": parse_power(content),
        "addons": parse_addons(content),
    }


def shorten_text(text, limit=700):
    if len(text) > limit:
        return text[:limit] + "..."

    return text


def check_killer_result(result):
    problems = []
    metadata = result["metadata"]
    power = result["power"]
    addons = result["addons"]

    if "Cost" in metadata:
        problems.append("Cost still present in metadata")

    if not metadata.get("Title"):
        problems.append("missing Title")

    if not metadata.get("portrait_url"):
        problems.append("missing portrait_url")
    elif not metadata["portrait_url"].startswith(BASE_URL):
        problems.append("portrait_url is not absolute")

    if not power.get("name"):
        problems.append("missing power name")

    if not power.get("description"):
        problems.append("missing power description")

    if power.get("icon_url") and not power["icon_url"].startswith(BASE_URL):
        problems.append("power icon_url is not absolute")

    if not addons:
        problems.append("no add-ons parsed")

    for addon in addons:
        if not addon.get("name") or not addon.get("description") or not addon.get("icon_url"):
            problems.append(f"incomplete add-on: {addon.get('name')}")
            break

        if not addon["icon_url"].startswith(BASE_URL):
            problems.append(f"non-absolute add-on icon: {addon.get('name')}")
            break

    trivia = result["sections"].get("Trivia")

    if trivia is not None:
        for subheading in trivia["subheadings"]:
            if subheading.startswith("Voice Actor"):
                problems.append("Voice Actor still present in Trivia")
                break

    return problems


def print_sample(sample):
    section_samples = {}

    for section_name, section in sample["sections"].items():
        if section is None:
            section_samples[section_name] = None
            continue

        section_samples[section_name] = {
            "subheadings": section["subheadings"],
            "text_sample": shorten_text(section["text"]),
        }

    print("SAMPLE KILLER METADATA")
    print(json.dumps(sample["metadata"], indent=2, ensure_ascii=False))
    print()
    print("SAMPLE KILLER SECTIONS")
    print(json.dumps(section_samples, indent=2, ensure_ascii=False))
    print()
    print("SAMPLE POWER")
    print(
        json.dumps(
            {
                "name": sample["power"]["name"],
                "icon_url": sample["power"]["icon_url"],
                "description_sample": shorten_text(sample["power"]["description"]),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print()
    print(f"SAMPLE ADD-ONS ({len(sample['addons'])} total, showing first 3)")
    print(json.dumps(sample["addons"][:3], indent=2, ensure_ascii=False))


def parse_all_killers_data():
    global_soup = get_page_soup(KILLERS_URL)
    global_content = global_soup.select_one("#mw-content-text .mw-parser-output")

    if global_content is None:
        raise ValueError("Main Killers page content was not found")

    global_intro = parse_global_intro(global_content)
    killer_links = parse_killer_links(global_content)

    killers = []
    ok_count = 0
    fail_count = 0
    missing_sections = {
        "Overview": 0,
        "Lore": 0,
        "Trivia": 0,
    }
    addon_counts = []
    failures = []
    sample_result = None

    print("GLOBAL INTRO TEXT")
    print(global_intro)
    print()
    print(f"FOUND {len(killer_links)} KILLER LINKS")
    print(json.dumps(killer_links[:5], indent=2, ensure_ascii=False))
    print()

    for index, killer in enumerate(killer_links, start=1):
        print(f"[{index}/{len(killer_links)}] Parsing {killer['name']}...")

        try:
            result = parse_one_killer(killer)
            problems = check_killer_result(result)

            for section_name, section in result["sections"].items():
                if section is None:
                    missing_sections[section_name] += 1

            addon_counts.append(len(result["addons"]))

            if problems:
                fail_count += 1
                failures.append(
                    {
                        "name": killer["name"],
                        "url": killer["url"],
                        "problems": problems,
                    }
                )
            else:
                ok_count += 1
                killers.append(result)

            if killer["name"] == SAMPLE_KILLER_NAME:
                sample_result = result
        except Exception as error:
            fail_count += 1
            failures.append(
                {
                    "name": killer["name"],
                    "url": killer["url"],
                    "problems": [str(error)],
                }
            )

    print()

    if sample_result is not None:
        print_sample(sample_result)
        print()

    print("VALIDATION SUMMARY")
    print(
        json.dumps(
            {
                "total": len(killer_links),
                "ok": ok_count,
                "failed": fail_count,
                "missing_sections": missing_sections,
                "addons_min": min(addon_counts) if addon_counts else 0,
                "addons_max": max(addon_counts) if addon_counts else 0,
                "failures": failures,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    if fail_count > 0:
        raise ValueError(f"Killer parsing failed for {fail_count} page(s)")

    return {
        "global_intro": global_intro,
        "killers": killers,
    }


def main():
    data = parse_all_killers_data()
    save_json(data, "killers.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
