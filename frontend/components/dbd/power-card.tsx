import type { Power } from "@/types/build"
import { EntityTooltip } from "./entity-tooltip"
import { SmartImage } from "./smart-image"

interface PowerCardProps {
  power: Power
}

/**
 * The Killer power the build's add-ons modify.
 *
 * Shown once rather than beside each kit: unlike a Survivor item, the power
 * is fixed by the Killer, so repeating it per kit would only say the same
 * thing twice.
 */
export function PowerCard({ power }: PowerCardProps) {
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <div className="flex items-center justify-center rounded-md border border-dbd-border bg-dbd-panel-2 px-2 py-2 sm:px-3.5 sm:py-2.5">
        <EntityTooltip name={power.name} description={power.description}>
          <SmartImage
            src={power.image}
            fallbackSrc={power.imageFallback}
            alt={power.name}
            fallbackLabel={power.name}
            className="h-12 w-12 rounded-[4px]"
          />
        </EntityTooltip>
      </div>
      <span className="max-w-32 text-[11px] leading-tight text-dbd-muted text-balance">
        {power.name}
      </span>
    </div>
  )
}
