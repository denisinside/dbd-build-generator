import json
import sys
from urllib.parse import urljoin

from media_mirror import mirror_items_media
from wiki_utils import (
    clean_text,
    embedding_element_text,
    get_page_soup,
    parse_rarity,
    save_json,
)


BASE_URL = "https://deadbydaylight.wiki.gg"
ITEMS_URL = f"{BASE_URL}/wiki/Items"
SAMPLE_ITEM_TYPE_NAME = "Med-Kits"

EXCLUDED_SECTION_WORDS = ["halloween", "lunar", "anniversary", "limited"]
SKIP_ITEM_TYPES = ["firecrackers"]


def find_heading(content, heading_name, tag_name="h2"):
    for heading in content.find_all(tag_name, recursive=False):
        if clean_text(heading) == heading_name:
            return heading

    return None


def section_is_excluded(title):
    lowered = title.lower()

    for word in EXCLUDED_SECTION_WORDS:
        if word in lowered:
            return True

    return False


def parse_items_overview(content):
    overview = find_heading(content, "Overview")

    if overview is None:
        raise ValueError("Overview heading was not found on Items page")

    text_parts = []
    element = overview.find_next_sibling()

    while element is not None and element.name != "h2":
        if element.name in ["h3", "h4", "p", "ul", "ol", "dl"]:
            text = clean_text(element)

            if text:
                text_parts.append(text)

        element = element.find_next_sibling()

    return "\n\n".join(text_parts)


def parse_item_type_links(content):
    item_types_heading = find_heading(content, "Item Types")

    if item_types_heading is None:
        raise ValueError("Item Types heading was not found")

    regular_items_heading = None
    element = item_types_heading.find_next_sibling()

    while element is not None and element.name != "h2":
        if element.name == "h3" and clean_text(element) == "Regular Items":
            regular_items_heading = element
            break

        element = element.find_next_sibling()

    if regular_items_heading is None:
        raise ValueError("Regular Items heading was not found")

    links_list = regular_items_heading.find_next_sibling("ul")

    if links_list is None:
        raise ValueError("Regular Items link list was not found")

    item_types = []

    for link in links_list.select("a[href]"):
        name = clean_text(link)

        if not name:
            continue

        if name.lower() in SKIP_ITEM_TYPES:
            continue

        item_type = {
            "name": name,
            "url": urljoin(BASE_URL, link["href"]),
        }

        if item_type not in item_types:
            item_types.append(item_type)

    return item_types


def parse_category_overview(content):
    overview = find_heading(content, "Overview")

    if overview is None:
        raise ValueError("Overview heading was not found on item type page")

    text_parts = []
    element = overview.find_next_sibling()

    while element is not None and element.name != "h2":
        if element.name in ["h3", "h4", "p", "ul", "ol", "dl"]:
            text = clean_text(element)

            if text:
                text_parts.append(text)

        element = element.find_next_sibling()

    return "\n\n".join(text_parts)


def parse_item_rows_from_table(table):
    items = []
    rows = table.select("tr")

    for row in rows:
        cells = row.select("th, td")

        if len(cells) != 3:
            continue

        first_text = clean_text(cells[0])
        second_text = clean_text(cells[1])

        # Skip header rows like Icon | Name | Description
        if first_text.lower() == "icon" and second_text.lower() == "name":
            continue

        icon = cells[0].find("img")
        name = second_text
        description = clean_text(cells[2])
        rarity = parse_rarity(row)

        if icon is None or not icon.get("src"):
            continue

        if not name or not description:
            continue

        items.append(
            {
                "name": name,
                "description": description,
                "rarity": rarity,
                "icon_url": urljoin(BASE_URL, icon["src"]),
            }
        )

    return items


def find_addons_heading(content):
    for heading in content.find_all("h2", recursive=False):
        title = clean_text(heading)

        if title == "Add-ons" or title.endswith("Add-ons"):
            return heading

    return None


def parse_items_from_page(content):
    overview = find_heading(content, "Overview")
    addons_heading = find_addons_heading(content)

    if overview is None:
        raise ValueError("Overview heading was not found")

    items = []
    skip_section = False
    element = overview.find_next_sibling()

    while element is not None:
        if element == addons_heading:
            break

        if element.name == "h2":
            title = clean_text(element)
            skip_section = section_is_excluded(title)
        elif element.name == "h3":
            title = clean_text(element)
            skip_section = section_is_excluded(title)
        elif (
            not skip_section
            and element.name == "table"
            and "wikitable" in (element.get("class") or [])
        ):
            items.extend(parse_item_rows_from_table(element))

        element = element.find_next_sibling()

    return items


def parse_addons_from_page(content):
    addons_heading = find_addons_heading(content)

    if addons_heading is None:
        raise ValueError("Add-ons heading was not found")

    table = addons_heading.find_next_sibling("table")

    if table is None:
        raise ValueError("Add-ons table was not found")

    addons = []
    skipped_deprecated = 0
    rows = table.select("tr")[1:]

    for row in rows:
        cells = row.select("th, td")

        if len(cells) != 3:
            continue

        icon = cells[0].find("img")
        name = clean_text(cells[1])
        description = clean_text(cells[2])
        rarity = parse_rarity(row)

        if icon is None or not icon.get("src"):
            continue

        if not name or not description:
            continue

        if "is no longer available" in description.lower():
            skipped_deprecated += 1
            continue

        addons.append(
            {
                "name": name,
                "description": description,
                "rarity": rarity,
                "icon_url": urljoin(BASE_URL, icon["src"]),
            }
        )

    return addons, skipped_deprecated


def parse_post_addons_embedding_text(content):
    addons_heading = find_addons_heading(content)

    if addons_heading is None:
        return None

    stop_names = {"History", "Change Log", "Gallery", "Trivia", "References"}
    text_parts = []
    started = False
    element = addons_heading.find_next_sibling()

    while element is not None:
        if element.name == "h2":
            title = clean_text(element)

            if title in stop_names:
                break

            # First h2 after Add-ons starts the embedding block
            started = True
            text_parts.append(title)
        elif started and element.name in ["h3", "h4", "p", "ul", "ol", "dl", "table", "blockquote"]:
            text = embedding_element_text(element)

            if text:
                text_parts.append(text)

        element = element.find_next_sibling()

    if not text_parts:
        return None

    return "\n\n".join(text_parts)


def parse_item_type_page(item_type):
    soup = get_page_soup(item_type["url"])
    content = soup.select_one("#mw-content-text .mw-parser-output")

    if content is None:
        raise ValueError(f"Content missing for item type: {item_type['name']}")

    addons, skipped_deprecated = parse_addons_from_page(content)

    return {
        "name": item_type["name"],
        "url": item_type["url"],
        "overview": parse_category_overview(content),
        "items": parse_items_from_page(content),
        "addons": addons,
        "skipped_deprecated_addons": skipped_deprecated,
        "post_addons_text": parse_post_addons_embedding_text(content),
    }


def shorten_text(text, limit=700):
    if len(text) > limit:
        return text[:limit] + "..."

    return text


def print_results(main_overview, item_types, sample):
    print("MAIN ITEMS OVERVIEW")
    print(shorten_text(main_overview, 900))
    print()
    print(f"FOUND {len(item_types)} ITEM TYPE LINKS (Firecrackers excluded)")
    print(json.dumps(item_types, indent=2, ensure_ascii=False))
    print()
    print(f"SAMPLE ITEM TYPE: {sample['name']}")
    print(sample["url"])
    print()
    print("CATEGORY OVERVIEW")
    print(sample["overview"])
    print()
    print(f"PARSED ITEMS ({len(sample['items'])})")
    print(json.dumps(sample["items"], indent=2, ensure_ascii=False))
    print()
    print(
        f"PARSED ADD-ONS ({len(sample['addons'])}, "
        f"skipped deprecated: {sample['skipped_deprecated_addons']})"
    )
    print(json.dumps(sample["addons"][:5], indent=2, ensure_ascii=False))
    print()
    print("POST ADD-ONS EMBEDDING TEXT")
    if sample["post_addons_text"] is None:
        print(None)
    else:
        print(shorten_text(sample["post_addons_text"], 900))


def parse_all_items_data():
    soup = get_page_soup(ITEMS_URL)
    content = soup.select_one("#mw-content-text .mw-parser-output")

    if content is None:
        raise ValueError("Items page content was not found")

    main_overview = parse_items_overview(content)
    item_types = parse_item_type_links(content)
    parsed_item_types = []
    sample = None

    print("MAIN ITEMS OVERVIEW")
    print(shorten_text(main_overview, 900))
    print()
    print(f"FOUND {len(item_types)} ITEM TYPE LINKS (Firecrackers excluded)")
    print(json.dumps(item_types, indent=2, ensure_ascii=False))
    print()

    for index, item_type in enumerate(item_types, start=1):
        print(f"[{index}/{len(item_types)}] Parsing {item_type['name']}...")
        result = parse_item_type_page(item_type)
        parsed_item_types.append(result)

        if item_type["name"] == SAMPLE_ITEM_TYPE_NAME:
            sample = result

    if sample is not None:
        print()
        print_results(main_overview, item_types, sample)

    return {
        "overview": main_overview,
        "item_types": parsed_item_types,
    }


def main():
    data = parse_all_items_data()
    mirror_items_media(data)
    save_json(data, "items.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
