import json
import sys
from urllib.parse import urljoin

from media_mirror import mirror_survivors_media
from wiki_utils import (
    clean_text,
    embedding_element_text,
    get_page_soup,
    save_json,
)


BASE_URL = "https://deadbydaylight.wiki.gg"
SURVIVORS_URL = f"{BASE_URL}/wiki/Survivors"
SAMPLE_SURVIVOR_NAME = "Dwight Fairfield"


def find_heading(content, heading_name):
    for heading in content.find_all("h2", recursive=False):
        if clean_text(heading) == heading_name:
            return heading

    return None


def parse_global_intro(content):
    list_heading = find_heading(content, "List of Survivors")

    if list_heading is None:
        raise ValueError("List of Survivors heading was not found")

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


def parse_survivor_links(content):
    list_heading = find_heading(content, "List of Survivors")

    if list_heading is None:
        raise ValueError("List of Survivors heading was not found")

    description = list_heading.find_next_sibling("p")

    if description is None:
        raise ValueError("List of Survivors description was not found")

    survivor_list = description.find_next_sibling("div")

    if survivor_list is None:
        raise ValueError("Survivor list was not found")

    survivor_links = []

    for link in survivor_list.select("a[href]"):
        name = clean_text(link)

        if not name:
            continue

        survivor = {
            "name": name,
            "url": urljoin(BASE_URL, link["href"]),
        }

        if survivor not in survivor_links:
            survivor_links.append(survivor)

    return survivor_links


def parse_survivor_metadata(soup):
    infobox = soup.select_one(
        "table.infoboxtable.charInfoboxTable.survivorInfobox"
    )

    if infobox is None:
        raise ValueError("Survivor infobox was not found")

    title = infobox.select_one("tr.infoboxTitle")
    portrait = infobox.select_one(".charInfoboxImage img")

    if title is None:
        raise ValueError("Survivor name was not found")

    if portrait is None or not portrait.get("src"):
        raise ValueError("Survivor portrait URL was not found")

    metadata = {
        "Name": clean_text(title),
        "portrait_url": urljoin(BASE_URL, portrait["src"]),
    }

    for row in infobox.select("tr"):
        key_cell = row.select_one("td.titleColumn")

        if key_cell is None:
            continue

        value_cell = key_cell.find_next_sibling("td")

        if value_cell is None:
            continue

        key = clean_text(key_cell)
        value = clean_text(value_cell)

        if key == "Voice Actor":
            continue

        if key and value:
            metadata[key] = value

    return metadata


def parse_survivor_sections(content):
    section_names = ["Overview", "Lore", "Trivia"]
    sections = {}

    for section_name in section_names:
        heading = find_heading(content, section_name)

        if heading is None:
            sections[section_name] = None
            continue

        subheadings = []
        text_parts = []
        skip_voice_actor = False
        element = heading.find_next_sibling()

        while element is not None and element.name != "h2":
            if element.name == "h3":
                subheading = clean_text(element)

                # Skip Voice Actor and related subsections (e.g. Voice Actor Change)
                if subheading.startswith("Voice Actor"):
                    skip_voice_actor = True
                    element = element.find_next_sibling()
                    continue

                skip_voice_actor = False
                subheadings.append(subheading)
                text_parts.append(subheading)
            elif (
                not skip_voice_actor
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


def parse_one_survivor(survivor):
    soup = get_page_soup(survivor["url"])
    content = soup.select_one("#mw-content-text .mw-parser-output")

    if content is None:
        raise ValueError("Survivor page content was not found")

    metadata = parse_survivor_metadata(soup)
    sections = parse_survivor_sections(content)

    return {
        "name": survivor["name"],
        "url": survivor["url"],
        "metadata": metadata,
        "sections": sections,
    }


def check_survivor_result(result):
    problems = []
    metadata = result["metadata"]
    sections = result["sections"]

    if "Voice Actor" in metadata:
        problems.append("Voice Actor still present in metadata")

    if not metadata.get("Name"):
        problems.append("missing Name")

    if not metadata.get("portrait_url"):
        problems.append("missing portrait_url")
    elif not metadata["portrait_url"].startswith(BASE_URL):
        problems.append("portrait_url is not absolute")

    trivia = sections.get("Trivia")

    if trivia is not None:
        for subheading in trivia["subheadings"]:
            if subheading.startswith("Voice Actor"):
                problems.append("Voice Actor still present in Trivia")
                break

    return problems


def print_sample(result):
    section_samples = {}

    for section_name, section in result["sections"].items():
        if section is None:
            section_samples[section_name] = None
            continue

        text = section["text"]

        if len(text) > 700:
            text = text[:700] + "..."

        section_samples[section_name] = {
            "subheadings": section["subheadings"],
            "text_sample": text,
        }

    print("SAMPLE SURVIVOR METADATA")
    print(json.dumps(result["metadata"], indent=2, ensure_ascii=False))
    print()
    print("SAMPLE SURVIVOR SECTIONS")
    print(json.dumps(section_samples, indent=2, ensure_ascii=False))


def parse_all_survivors_data():
    global_soup = get_page_soup(SURVIVORS_URL)
    global_content = global_soup.select_one("#mw-content-text .mw-parser-output")

    if global_content is None:
        raise ValueError("Main Survivors page content was not found")

    global_intro = parse_global_intro(global_content)
    survivor_links = parse_survivor_links(global_content)

    survivors = []
    ok_count = 0
    fail_count = 0
    missing_sections = {
        "Overview": 0,
        "Lore": 0,
        "Trivia": 0,
    }
    failures = []
    sample_result = None

    print("GLOBAL INTRO TEXT")
    print(global_intro)
    print()
    print(f"FOUND {len(survivor_links)} SURVIVOR LINKS")
    print(json.dumps(survivor_links[:5], indent=2, ensure_ascii=False))
    print()

    for index, survivor in enumerate(survivor_links, start=1):
        print(f"[{index}/{len(survivor_links)}] Parsing {survivor['name']}...")

        try:
            result = parse_one_survivor(survivor)
            problems = check_survivor_result(result)

            for section_name, section in result["sections"].items():
                if section is None:
                    missing_sections[section_name] += 1

            if problems:
                fail_count += 1
                failures.append(
                    {
                        "name": survivor["name"],
                        "url": survivor["url"],
                        "problems": problems,
                    }
                )
            else:
                ok_count += 1
                survivors.append(result)

            if survivor["name"] == SAMPLE_SURVIVOR_NAME:
                sample_result = result
        except Exception as error:
            fail_count += 1
            failures.append(
                {
                    "name": survivor["name"],
                    "url": survivor["url"],
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
                "total": len(survivor_links),
                "ok": ok_count,
                "failed": fail_count,
                "missing_sections": missing_sections,
                "failures": failures,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    if fail_count > 0:
        raise ValueError(f"Survivor parsing failed for {fail_count} page(s)")

    return {
        "global_intro": global_intro,
        "survivors": survivors,
    }


def main():
    data = parse_all_survivors_data()
    mirror_survivors_media(data)
    save_json(data, "survivors.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
