import type { Character } from "@/types/build"
import { SmartImage } from "./smart-image"
import { cn } from "@/lib/utils"

interface CharacterCardProps {
  character: Character
}

export function CharacterCard({ character }: CharacterCardProps) {
  const segments = Array.from({ length: character.maxDifficulty }, (_, i) => i < character.difficulty)

  return (
    <div className="flex items-center gap-4">
      <div className="relative shrink-0">
        <div className="absolute -inset-1 rounded-lg bg-dbd-purple/25 blur-md" aria-hidden />
        <SmartImage
          src={character.image}
          alt={character.name}
          fallbackLabel={character.name}
          className="relative h-16 w-16 rounded-md border border-dbd-border md:h-[70px] md:w-[70px]"
        />
      </div>

      <div className="min-w-0">
        <h2 className="font-[family-name:var(--font-oswald)] text-xl font-semibold leading-tight text-dbd-text md:text-[22px]">
          {character.name}
        </h2>
        <p className="mt-1 text-xs font-semibold uppercase tracking-wider text-dbd-purple">
          {character.role}
        </p>

        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-dbd-muted">
            Difficulty:
          </span>
          <div className="flex items-center gap-1" role="img" aria-label={`Difficulty ${character.difficulty} of ${character.maxDifficulty}`}>
            {segments.map((filled, i) => (
              <span
                key={i}
                className={cn(
                  "h-3 w-6 rounded-[3px] border border-dbd-border/60",
                  filled ? "bg-dbd-diff-medium" : "bg-white/5",
                )}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
