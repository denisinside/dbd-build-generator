import type { Perk } from "@/types/build"
import { SmartImage } from "./smart-image"
import { EntityTooltip } from "./entity-tooltip"

interface PerksGridProps {
  perks: Perk[]
}

/** Row of circular perk icons, matching the reference header. */
export function PerksGrid({ perks }: PerksGridProps) {
  return (
    <ul className="grid grid-cols-2 gap-3">
      {perks.map((perk, i) => (
        <li key={`${perk.name}-${i}`} className="flex min-w-0 flex-col items-center gap-1.5 text-center">
          <EntityTooltip name={perk.name} description={perk.description}>
            <SmartImage
              src={perk.image}
              fallbackSrc={perk.imageFallback}
              alt={perk.name}
              fallbackLabel={perk.name}
              className="h-12 w-12 rounded-full border border-dbd-border bg-dbd-panel-2 md:h-[52px] md:w-[52px]"
            />
          </EntityTooltip>
          <span className="max-w-20 text-[10px] leading-tight text-dbd-muted">
            {perk.name}
          </span>
        </li>
      ))}
    </ul>
  )
}
