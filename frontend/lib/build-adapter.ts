import type { Build, Difficulty, GeneratedBuild } from "@/types/build"


function getDifficulty(value: "Medium Difficulty" | "High Difficulty"): Difficulty {
  if (value === "High Difficulty") {
    return "high"
  }

  return "medium"
}


export function adaptGeneratedBuild(build: GeneratedBuild): Build {
  return {
    id: build.id,
    title: build.build_title,
    role: build.role,
    character: {
      name: build.character_name,
      image: build.character_portrait_url ?? "",
      role: build.role,
      difficulty: build.difficulty_rating,
      maxDifficulty: 4,
    },
    perks: build.perks.map((perk) => ({
      name: perk.name,
      image: perk.icon_url ?? "",
      description: perk.description ?? undefined,
    })),
    loadouts: build.item_kits.map((kit) => ({
      item: kit.item_name
        ? {
            name: kit.item_name,
            image: kit.item_icon_url ?? "",
            description: kit.item_description ?? undefined,
            rarity: kit.item_rarity ?? undefined,
          }
        : undefined,
      addons: kit.addons.map((addon) => ({
        name: addon.name,
        image: addon.icon_url ?? "",
        description: addon.description ?? undefined,
        rarity: addon.rarity ?? undefined,
        showPlus: build.role === "Survivor",
      })),
      caption: kit.kit_title,
    })),
    evaluation: {
      score: build.build_score,
      maxScore: 10,
    },
    targetAudience: build.target_audience,
    strategy: {
      early: build.tactics.early_game,
      mid: build.tactics.mid_game,
      late: build.tactics.late_game,
    },
    pros: build.pros.map((point) => ({
      icon: point.icon,
      title: point.label,
      description: point.tooltip_text,
    })),
    cons: build.cons.map((point) => ({
      icon: point.icon,
      title: point.label,
      description: point.tooltip_text,
    })),
    counters: (build.counter_killers ?? []).map((counter) => ({
      name: counter.killer_name,
      image: counter.portrait_url ?? "",
      difficulty: getDifficulty(counter.difficulty_level),
      reason: counter.explanation,
    })),
  }
}
