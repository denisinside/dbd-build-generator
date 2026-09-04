// Mirrored locally like every other wiki image (see parsers/media_mirror.py:
// mirror_rarity_frames) instead of hotlinking the wiki. Re-run
// `uv run python download_media.py` after clearing frontend/public/media/rarity.
export const RARITY_BACKGROUND_URLS: Record<string, string> = {
  Common: "/media/rarity/common.png",
  Uncommon: "/media/rarity/uncommon.png",
  Rare: "/media/rarity/rare.png",
  "Very Rare": "/media/rarity/very-rare.png",
  "Ultra Rare": "/media/rarity/ultra-rare.png",
  Visceral: "/media/rarity/ultra-rare.png",
  Event: "/media/rarity/event.png",
}


export function getRarityBackgroundUrl(rarity?: string) {
  if (!rarity) {
    return undefined
  }

  return RARITY_BACKGROUND_URLS[rarity]
}
