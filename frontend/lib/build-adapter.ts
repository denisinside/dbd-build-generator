import type { Build, Difficulty, GeneratedBuild } from "@/types/build"


function getDifficulty(value: string): Difficulty {
  if (value === "High Difficulty") {
    return "high"
  }

  if (value === "Low Difficulty") {
    return "low"
  }

  return "medium"
}


/**
 * Locally mirrored image first, wiki URL only as a fallback.
 *
 * Hotlinking every icon straight from the wiki means the whole UI degrades to
 * initials the moment that host throttles us, so `/media/...` is preferred
 * whenever the ingest step managed to download the file.
 */
function pickImage(localPath: string | null, remoteUrl: string | null) {
  const image = localPath ?? remoteUrl ?? ""
  const fallback = localPath && remoteUrl ? remoteUrl : undefined

  return { image, imageFallback: fallback }
}


export function adaptGeneratedBuild(build: GeneratedBuild): Build {
  return {
    id: build.id,
    title: build.build_title,
    prompt: build.prompt,
    role: build.role,
    character: {
      ...pickImage(build.character_portrait_path, build.character_portrait_url),
      name: build.character_name,
      role: build.role,
      difficulty: build.difficulty_rating,
      maxDifficulty: 4,
    },
    perks: build.perks.map((perk) => ({
      ...pickImage(perk.icon_path, perk.icon_url),
      name: perk.name,
      description: perk.description ?? undefined,
      character: perk.character ?? undefined,
      reason: perk.reason ?? undefined,
    })),
    power: build.character_power
      ? {
          ...pickImage(build.character_power.icon_path, build.character_power.icon_url),
          name: build.character_power.name,
          description: build.character_power.description ?? undefined,
        }
      : undefined,
    loadouts: build.item_kits.map((kit) => ({
      item: kit.item_name
        ? {
            ...pickImage(kit.item_icon_path, kit.item_icon_url),
            name: kit.item_name,
            description: kit.item_description ?? undefined,
            rarity: kit.item_rarity ?? undefined,
            reason: kit.item_reason ?? undefined,
          }
        : undefined,
      addons: kit.addons.map((addon) => ({
        ...pickImage(addon.icon_path, addon.icon_url),
        name: addon.name,
        description: addon.description ?? undefined,
        rarity: addon.rarity ?? undefined,
        reason: addon.reason ?? undefined,
        showPlus: build.role === "Survivor",
      })),
      caption: kit.kit_title,
    })),
    evaluation: {
      score: build.build_score,
      maxScore: 10,
      axes: (build.axes ?? []).map((axis) => ({
        label: axis.axis,
        score: axis.score,
        maxScore: 5,
        reason: axis.reason,
      })),
    },
    synergies: build.synergies ?? [],
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
    counterPerks: (build.counter_perks ?? []).map((counter) => ({
      ...pickImage(counter.icon_path, counter.icon_url),
      name: counter.perk_name,
      description: counter.description ?? undefined,
      character: counter.character ?? undefined,
      explanation: counter.explanation,
    })),
    counters: (build.counter_killers ?? []).map((counter) => ({
      ...pickImage(counter.portrait_path, counter.portrait_url),
      name: counter.killer_name,
      difficulty: getDifficulty(counter.difficulty_level),
      reason: counter.explanation,
    })),
  }
}
