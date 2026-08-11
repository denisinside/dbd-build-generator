// Central data model for the DBD Build Generator template.
// The entire page is driven by a single `Build` object — swap the object,
// and every section of the page updates automatically.

export type Difficulty = "medium" | "high"
export type Role = "Survivor" | "Killer"

export interface Character {
  name: string
  image: string
  role: Role
  /** Current difficulty rating (e.g. 2) */
  difficulty: number
  /** Maximum difficulty rating used to render the indicator track (e.g. 3) */
  maxDifficulty: number
}

export interface Perk {
  name: string
  image: string
  description?: string
}

export interface Addon {
  name: string
  image: string
  description?: string
  rarity?: string
  showPlus?: boolean
}

export interface Item {
  name: string
  image: string
  description?: string
  rarity?: string
}

export interface Loadout {
  item?: Item
  addons: Addon[]
  caption: string
}

export interface Evaluation {
  score: number
  maxScore: number
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

export interface CounterMatchup {
  name: string
  image: string
  difficulty: Difficulty
  reason: string
}

export interface Build {
  id: string
  title: string
  role: Role
  character: Character
  perks: Perk[]
  loadouts: Loadout[]
  evaluation: Evaluation
  targetAudience: AudienceItem[]
  strategy: Strategy
  pros: BuildPoint[]
  cons: BuildPoint[]
  counters: CounterMatchup[]
}

export interface GeneratedPerk {
  name: string
  icon_url: string | null
  description: string | null
}

export interface GeneratedAddon {
  name: string
  icon_url: string | null
  description: string | null
  rarity: string | null
}

export interface GeneratedItemKit {
  kit_title: string
  item_name: string | null
  item_icon_url: string | null
  item_description: string | null
  item_rarity: string | null
  addons: GeneratedAddon[]
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

export interface GeneratedCounterKiller {
  killer_name: string
  difficulty_level: "Medium Difficulty" | "High Difficulty"
  explanation: string
  portrait_url: string | null
}

export interface GeneratedBuild {
  id: string
  prompt?: string
  build_title: string
  character_name: string
  character_portrait_url: string | null
  role: Role
  difficulty_rating: number
  build_score: number
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
  created_at: string
}

export interface BuildSummary {
  id: string
  build_title: string
  character_name: string
  role: Role
  build_score: number
  created_at: string
}
