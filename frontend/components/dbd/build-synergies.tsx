import { Fragment } from "react"
import type { Loadout, Perk, Power, Synergy } from "@/types/build"
import { SectionHeading } from "./section-heading"
import { EntityTooltip } from "./entity-tooltip"
import { SmartImage } from "./smart-image"

interface BuildSynergiesProps {
  synergies: Synergy[]
  /** Where a synergy's entity names are looked up for their tooltip and icon. */
  perks: Perk[]
  loadouts: Loadout[]
  power?: Power
}

interface EntityInfo {
  image: string
  imageFallback?: string
  description?: string
  character?: string
}

/** Every entity a synergy is allowed to name, keyed by its exact display name. */
function buildEntityLookup(perks: Perk[], loadouts: Loadout[], power?: Power) {
  const lookup = new Map<string, EntityInfo>()

  for (const perk of perks) {
    lookup.set(perk.name, {
      image: perk.image,
      imageFallback: perk.imageFallback,
      description: perk.description,
      character: perk.character,
    })
  }

  for (const loadout of loadouts) {
    if (loadout.item) {
      lookup.set(loadout.item.name, {
        image: loadout.item.image,
        imageFallback: loadout.item.imageFallback,
        description: loadout.item.description,
      })
    }

    for (const addon of loadout.addons) {
      lookup.set(addon.name, {
        image: addon.image,
        imageFallback: addon.imageFallback,
        description: addon.description,
      })
    }
  }

  if (power) {
    lookup.set(power.name, {
      image: power.image,
      imageFallback: power.imageFallback,
      description: power.description,
    })
  }

  return lookup
}

/**
 * What makes the four perks a build rather than four perks.
 *
 * Every name here was checked against the rest of the loadout server-side, so
 * a combo can only ever talk about pieces that are actually equipped — which
 * is what makes looking each one up by its exact name safe.
 */
export function BuildSynergies({ synergies, perks, loadouts, power }: BuildSynergiesProps) {
  if (synergies.length === 0) {
    return null
  }

  const lookup = buildEntityLookup(perks, loadouts, power)

  return (
    <section aria-labelledby="synergies-heading">
      <SectionHeading id="synergies-heading">Synergies</SectionHeading>

      <ul className="mt-5 grid gap-3 md:grid-cols-2">
        {synergies.map((synergy, index) => (
          <li
            key={index}
            className="rounded-lg border border-dbd-border bg-dbd-panel p-4"
          >
            <div className="flex flex-wrap items-center gap-1.5">
              {synergy.entities.map((entity, position) => {
                const info = lookup.get(entity)

                return (
                  <Fragment key={entity}>
                    {position > 0 ? (
                      <span aria-hidden className="text-dbd-muted/60">
                        +
                      </span>
                    ) : null}

                    {/* ponytail: falls back to a plain badge if a name somehow
                        is not in the loadout — grounding already guarantees it
                        is, so this is just a safety net, not the normal path. */}
                    {info ? (
                      <EntityTooltip
                        name={entity}
                        description={info.description}
                        character={info.character}
                      >
                        <span className="inline-flex items-center gap-1.5 rounded-md border border-dbd-purple/30 bg-dbd-purple/10 px-2 py-0.5 text-xs font-semibold text-dbd-text underline decoration-dotted decoration-dbd-purple/60 underline-offset-2 cursor-help">
                          <SmartImage
                            src={info.image}
                            fallbackSrc={info.imageFallback}
                            alt=""
                            className="h-4 w-4 rounded-full"
                          />
                          {entity}
                        </span>
                      </EntityTooltip>
                    ) : (
                      <span className="rounded-md border border-dbd-purple/30 bg-dbd-purple/10 px-2 py-0.5 text-xs font-semibold text-dbd-text">
                        {entity}
                      </span>
                    )}
                  </Fragment>
                )
              })}
            </div>
            <p className="mt-3 text-sm leading-relaxed text-dbd-muted">
              {synergy.explanation}
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}
