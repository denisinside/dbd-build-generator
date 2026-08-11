export const RARITY_BACKGROUND_URLS: Record<string, string> = {
  Common: "https://deadbydaylight.wiki.gg/images/Dbd-addons-common.png",
  Uncommon: "https://deadbydaylight.wiki.gg/images/Dbd-addons-uncommon.png",
  Rare: "https://deadbydaylight.wiki.gg/images/Dbd-addons-rare.png",
  "Very Rare": "https://deadbydaylight.wiki.gg/images/Dbd-addons-veryrare.png",
  "Ultra Rare": "https://deadbydaylight.wiki.gg/images/Dbd-addons-ultrarare.png",
  Visceral: "https://deadbydaylight.wiki.gg/images/Dbd-addons-ultrarare.png",
  Event: "https://deadbydaylight.wiki.gg/images/BP_BG_Event.png",
}


export function getRarityBackgroundUrl(rarity?: string) {
  if (!rarity) {
    return undefined
  }

  return RARITY_BACKGROUND_URLS[rarity]
}
