import type { Difficulty } from "@/types/build"

// Single source of truth for difficulty presentation, so colors and labels
// are never hardcoded inside individual cards.
export const DIFFICULTY_CONFIG: Record<
  Difficulty,
  { label: string; dotClass: string; textClass: string }
> = {
  low: {
    label: "Low Difficulty",
    dotClass: "bg-dbd-diff-low",
    textClass: "text-dbd-diff-low",
  },
  medium: {
    label: "Medium Difficulty",
    dotClass: "bg-dbd-diff-medium",
    textClass: "text-dbd-diff-medium",
  },
  high: {
    label: "High Difficulty",
    dotClass: "bg-dbd-diff-high",
    textClass: "text-dbd-diff-high",
  },
}

export const DIFFICULTY_ORDER: Difficulty[] = ["low", "medium", "high"]
