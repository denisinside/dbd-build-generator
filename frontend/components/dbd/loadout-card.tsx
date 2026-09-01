import type { Loadout } from "@/types/build"
import { EntityTooltip } from "./entity-tooltip"
import { RarityIcon } from "./rarity-icon"

interface LoadoutCardProps {
  loadout: Loadout
}

/**
 * A single item + add-ons loadout group. Fully data-driven: item image,
 * name, any number of add-ons, caption and description all come from props.
 */
export function LoadoutCard({ loadout }: LoadoutCardProps) {
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <div className="flex items-end justify-center gap-1.5 rounded-md border border-dbd-border bg-dbd-panel-2 px-3.5 py-2.5">
        {loadout.item ? (
          <EntityTooltip
            name={loadout.item.name}
            description={loadout.item.description}
            reason={loadout.item.reason}
          >
            <RarityIcon
              src={loadout.item.image}
              fallbackSrc={loadout.item.imageFallback}
              alt={loadout.item.name}
              rarity={loadout.item.rarity}
              fallbackLabel={loadout.item.name}
              className="h-12 w-12 overflow-hidden rounded-[4px]"
            />
          </EntityTooltip>
        ) : null}
        <div className="flex items-end gap-1.5">
          {loadout.addons.map((addon, i) => (
            <EntityTooltip
              key={`${addon.name}-${i}`}
              name={addon.name}
              description={addon.description}
              reason={addon.reason}
            >
              <RarityIcon
                src={addon.image}
                fallbackSrc={addon.imageFallback}
                alt={addon.name}
                rarity={addon.rarity}
                showPlus={addon.showPlus}
                fallbackLabel={addon.name}
                className={
                  loadout.item
                    ? "h-9 w-9 overflow-hidden rounded-[3px] border border-dbd-border/60"
                    : "h-11 w-11 overflow-hidden rounded-[4px] border border-dbd-border/60"
                }
              />
            </EntityTooltip>
          ))}
        </div>
      </div>
      <span className="max-w-32 text-[11px] leading-tight text-dbd-muted text-balance">
        {loadout.caption}
      </span>
    </div>
  )
}
