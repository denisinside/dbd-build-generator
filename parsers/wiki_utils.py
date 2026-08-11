import json
import os
import re


RARITY_FROM_CLASS = {
    "common-item-element": "Common",
    "uncommon-item-element": "Uncommon",
    "rare-item-element": "Rare",
    "very-rare-item-element": "Very Rare",
    "visceral-item-element": "Visceral",
    "ultra-rare-item-element": "Ultra Rare",
    "event-item-element": "Event",
}


def clean_text(element):
    text = element.get_text(" ", strip=True)
    text = " ".join(text.split())
    text = re.sub(r"\s+([.,:;!?])", r"\1", text)

    return text


def parse_rarity(row):
    rarity_div = row.select_one(".game-element-bg-settings")

    if rarity_div is None:
        return None

    for class_name in rarity_div.get("class", []):
        if class_name in RARITY_FROM_CLASS:
            return RARITY_FROM_CLASS[class_name]

    return None


def save_json(data, filename):
    project_root = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)

    file_path = os.path.join(data_dir, filename)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    print(f"Saved JSON cache: {file_path}")
    return file_path


def expand_table_grid(table):
    rows = table.select("tr")
    grid = []
    # Tracks unfinished rowspans: column_index -> [rows_left, value]
    active_rowspans = {}

    for row in rows:
        grid_row = []
        cells = row.select("th, td")
        cell_index = 0
        col = 0

        while True:
            if col in active_rowspans and active_rowspans[col][0] > 0:
                value = active_rowspans[col][1]
                grid_row.append(value)
                active_rowspans[col][0] -= 1

                if active_rowspans[col][0] == 0:
                    del active_rowspans[col]

                col += 1
                continue

            if cell_index >= len(cells):
                break

            cell = cells[cell_index]
            cell_index += 1

            value = clean_text(cell)
            rowspan = int(cell.get("rowspan") or 1)
            colspan = int(cell.get("colspan") or 1)

            for offset in range(colspan):
                current_col = col + offset
                grid_row.append(value)

                if rowspan > 1:
                    active_rowspans[current_col] = [rowspan - 1, value]

            col += colspan

        while col in active_rowspans and active_rowspans[col][0] > 0:
            value = active_rowspans[col][1]
            grid_row.append(value)
            active_rowspans[col][0] -= 1

            if active_rowspans[col][0] == 0:
                del active_rowspans[col]

            col += 1

        grid.append(grid_row)

    return grid


def format_table_as_key_value(table):
    grid = expand_table_grid(table)

    if not grid:
        return ""

    headers = grid[0]

    if not headers:
        return clean_text(table)

    if len(grid) == 1:
        return clean_text(table)

    formatted_rows = []

    for row_values in grid[1:]:
        pairs = []

        for index, value in enumerate(row_values):
            if index >= len(headers):
                break

            header = headers[index]

            if not header or not value:
                continue

            pairs.append(f"{header}: {value}")

        if pairs:
            formatted_rows.append(" | ".join(pairs))

    return "\n".join(formatted_rows)


def embedding_element_text(element):
    if element.name == "table":
        return format_table_as_key_value(element)

    return clean_text(element)
