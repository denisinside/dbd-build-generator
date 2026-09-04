"""Mirror wiki images into frontend/public/media.

The parsers call these helpers right before writing data/*.json, and
download_media.py calls the same helpers to backfill an existing cache
without re-scraping the wiki. Every mirrored image adds a `*_path` field
next to the original `*_url`; the remote URL stays as a runtime fallback.
"""

from wiki_utils import download_media


# Widths requested from the wiki's thumbnailer, sized for 2x displays.
# Portraits render at 70-92 px, item and add-on icons at 36-48 px.
PORTRAIT_WIDTH = 192
POWER_WIDTH = 128
ICON_WIDTH = 96

# Not entity data — generic rarity-frame chrome the wiki reuses everywhere.
# Mirrored the same way as everything else so the frontend never hotlinks the
# wiki (frontend/lib/rarity.ts reads the resulting local paths).
RARITY_FRAME_SOURCES = {
    "Common": "https://deadbydaylight.wiki.gg/images/Dbd-addons-common.png",
    "Uncommon": "https://deadbydaylight.wiki.gg/images/Dbd-addons-uncommon.png",
    "Rare": "https://deadbydaylight.wiki.gg/images/Dbd-addons-rare.png",
    "Very Rare": "https://deadbydaylight.wiki.gg/images/Dbd-addons-veryrare.png",
    "Ultra Rare": "https://deadbydaylight.wiki.gg/images/Dbd-addons-ultrarare.png",
    "Event": "https://deadbydaylight.wiki.gg/images/BP_BG_Event.png",
}


def mirror_one(container, url_key, path_key, category, name, force=False, width=None):
    """Download container[url_key] and store the public path in container."""
    url = container.get(url_key)

    if not url:
        return False

    public_path = download_media(url, category, name, force=force, width=width)

    if public_path is None:
        return False

    container[path_key] = public_path
    return True


def mirror_perks_media(data, force=False):
    count = 0

    for perk in data["perks"]:
        # Perk icons are already linked as 96 px thumbnails.
        if mirror_one(perk, "icon_url", "icon_path", "perks", perk["name"], force):
            count += 1

    print(f"Mirrored {count}/{len(data['perks'])} perk icons.")
    return count


def mirror_killers_media(data, force=False):
    count = 0

    for killer in data["killers"]:
        metadata = killer.get("metadata") or {}
        title = metadata.get("Title") or killer["name"]

        if mirror_one(
            metadata,
            "portrait_url",
            "portrait_path",
            "killers",
            title,
            force,
            width=PORTRAIT_WIDTH,
        ):
            count += 1

        power = killer.get("power") or {}

        if mirror_one(
            power, "icon_url", "icon_path", "powers", title, force, width=POWER_WIDTH
        ):
            count += 1

        for addon in killer.get("addons", []):
            addon_name = f"{title} {addon['name']}"

            if mirror_one(
                addon,
                "icon_url",
                "icon_path",
                "killer-addons",
                addon_name,
                force,
                width=ICON_WIDTH,
            ):
                count += 1

    print(f"Mirrored {count} killer images (portraits, powers, add-ons).")
    return count


def mirror_survivors_media(data, force=False):
    count = 0

    for survivor in data["survivors"]:
        metadata = survivor.get("metadata") or {}

        if mirror_one(
            metadata,
            "portrait_url",
            "portrait_path",
            "survivors",
            survivor["name"],
            force,
            width=PORTRAIT_WIDTH,
        ):
            count += 1

    print(f"Mirrored {count}/{len(data['survivors'])} survivor portraits.")
    return count


def mirror_items_media(data, force=False):
    count = 0

    for item_type in data["item_types"]:
        type_name = item_type["name"]

        for item in item_type.get("items", []):
            if mirror_one(
                item,
                "icon_url",
                "icon_path",
                "items",
                item["name"],
                force,
                width=ICON_WIDTH,
            ):
                count += 1

        for addon in item_type.get("addons", []):
            addon_name = f"{type_name} {addon['name']}"

            if mirror_one(
                addon,
                "icon_url",
                "icon_path",
                "item-addons",
                addon_name,
                force,
                width=ICON_WIDTH,
            ):
                count += 1

    print(f"Mirrored {count} item and item add-on icons.")
    return count


def mirror_rarity_frames(force=False):
    """Mirror the fixed set of rarity-frame backgrounds. No data file to update:
    the local path is deterministic (`media_target_path`), so
    `frontend/lib/rarity.ts` hardcodes it directly."""
    count = 0

    for rarity, url in RARITY_FRAME_SOURCES.items():
        if download_media(url, "rarity", rarity, force=force):
            count += 1

    print(f"Mirrored {count}/{len(RARITY_FRAME_SOURCES)} rarity frames.")
    return count
