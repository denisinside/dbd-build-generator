// Central data model for the DBD Build Generator template.
// The entire page is driven by a single `Build` object — swap the object,
// and every section of the page updates automatically.

export type Difficulty = "low" | "medium" | "high"
export type Role = "Survivor" | "Killer"

export interface Character {
  name: string
  image: string
  /** Remote source used only if `image` fails to load. */
  imageFallback?: string
  role: Role
  /** Current difficulty rating (e.g. 2) */
  difficulty: number
  /** Maximum difficulty rating used to render the indicator track (e.g. 3) */
  maxDifficulty: number
}

export interface Perk {
  name: string
  image: string
  imageFallback?: string
  description?: string
  /** Which character teaches it, so a new player knows whose Bloodweb to grind. */
  character?: string
  /** Why the generator put this perk in this build. */
  reason?: string
}

export interface Addon {
  name: string
  image: string
  imageFallback?: string
  description?: string
  rarity?: string
  showPlus?: boolean
  reason?: string
}

export interface Item {
  name: string
  image: string
  imageFallback?: string
  description?: string
  rarity?: string
  reason?: string
}

/** The Killer power every add-on in the build modifies. Absent for Survivors. */
export interface Power {
  name: string
  image: string
  imageFallback?: string
  description?: string
}

export interface Axis {
  label: string
  score: number
  maxScore: number
  reason: string
}

export interface Synergy {
  entities: string[]
  explanation: string
}

export interface Loadout {
  item?: Item
  addons: Addon[]
  caption: string
}

export interface Evaluation {
  score: number
  maxScore: number
  /** Breakdown the headline score is averaged from. Empty on older builds. */
  axes: Axis[]
}

/** Icon names map to lucide-react icons via the icon registry. */
export interface AudienceItem {
  icon: string
  title: string
  description: string
}

export interface StrategyStep {
  title: string
  description: string
}

export interface Strategy {
  early: StrategyStep[]
  mid: StrategyStep[]
  late: StrategyStep[]
}

export interface BuildPoint {
  icon: string
  title: string
  description?: string
}

/** A perk the other side brings that blunts this build. */
export interface CounterPerk {
  name: string
  image: string
  imageFallback?: string
  description?: string
  character?: string
  explanation: string
}

export interface CounterMatchup {
  name: string
  image: string
  imageFallback?: string
  difficulty: Difficulty
  reason: string
}

export interface Build {
  id: string
  title: string
  /** The request this build was generated from. */
  prompt?: string
  role: Role
  character: Character
  perks: Perk[]
  power?: Power
  loadouts: Loadout[]
  evaluation: Evaluation
  synergies: Synergy[]
  targetAudience: AudienceItem[]
  strategy: Strategy
  pros: BuildPoint[]
  cons: BuildPoint[]
  counters: CounterMatchup[]
  counterPerks: CounterPerk[]
}

export interface GeneratedPerk {
  name: string
  icon_url: string | null
  /** Locally mirrored copy under /media, when it exists. */
  icon_path: string | null
  description: string | null
  character?: string | null
  reason?: string | null
}

export interface GeneratedAddon {
  name: string
  icon_url: string | null
  icon_path: string | null
  description: string | null
  rarity: string | null
  reason?: string | null
}

export interface GeneratedItemKit {
  kit_title: string
  item_name: string | null
  item_icon_url: string | null
  item_icon_path: string | null
  item_description: string | null
  item_rarity: string | null
  item_reason?: string | null
  addons: GeneratedAddon[]
}

export interface GeneratedPower {
  name: string
  description: string | null
  icon_url: string | null
  icon_path: string | null
}

export interface GeneratedAxis {
  axis: string
  score: number
  reason: string
}

export interface GeneratedSynergy {
  entities: string[]
  explanation: string
}

export interface GeneratedTextBlock {
  title: string
  description: string
  icon: string
}

export interface GeneratedTacticStep {
  title: string
  description: string
}

export interface GeneratedCounterPerk {
  perk_name: string
  explanation: string
  icon_url: string | null
  icon_path: string | null
  description: string | null
  character?: string | null
}

export interface GeneratedCounterKiller {
  killer_name: string
  difficulty_level: "Low Difficulty" | "Medium Difficulty" | "High Difficulty"
  explanation: string
  portrait_url: string | null
  portrait_path: string | null
}

export interface GeneratedBuild {
  id: string
  prompt?: string
  build_title: string
  character_name: string
  character_portrait_url: string | null
  character_portrait_path: string | null
  character_power?: GeneratedPower | null
  role: Role
  difficulty_rating: number
  build_score: number
  axes?: GeneratedAxis[]
  synergies?: GeneratedSynergy[]
  perks: GeneratedPerk[]
  item_kits: GeneratedItemKit[]
  target_audience: GeneratedTextBlock[]
  tactics: {
    early_game: GeneratedTacticStep[]
    mid_game: GeneratedTacticStep[]
    late_game: GeneratedTacticStep[]
  }
  pros: Array<{
    label: string
    icon: string
    tooltip_text: string
  }>
  cons: Array<{
    label: string
    icon: string
    tooltip_text: string
  }>
  counter_killers: GeneratedCounterKiller[] | null
  counter_perks?: GeneratedCounterPerk[]
  created_at: string
}

export interface BuildSummary {
  id: string
  build_title: string
  character_name: string
  role: Role
  build_score: number
  created_at: string
  /** Denormalised at creation, so the feed can credit an author without a join. */
  author_name?: string | null
  author_avatar_url?: string | null
}
