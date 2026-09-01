import type { Synergy } from "@/types/build"
import { SectionHeading } from "./section-heading"

interface BuildSynergiesProps {
  synergies: Synergy[]
}

/**
 * What makes the four perks a build rather than four perks.
 *
 * Every name here was checked against the rest of the loadout server-side, so
 * a combo can only ever talk about pieces that are actually equipped.
 */
export function BuildSynergies({ synergies }: BuildSynergiesProps) {
  if (synergies.length === 0) {
    return null
  }

  return (
    <section aria-labelledby="synergies-heading">
      <SectionHeading id="synergies-heading">Synergies</SectionHeading>

      <ul className="mt-5 grid gap-3 md:grid-cols-2">
        {synergies.map((synergy, index) => (
          <li
            key={index}
            className="rounded-lg border border-dbd-border bg-dbd-panel p-4"
          >
            <p className="flex flex-wrap items-center gap-1.5">
              {synergy.entities.map((entity, position) => (
                <span key={entity} className="flex items-center gap-1.5">
                  {position > 0 ? (
                    <span aria-hidden className="text-dbd-muted/60">
                      +
                    </span>
                  ) : null}
                  <span className="rounded-md border border-dbd-purple/30 bg-dbd-purple/10 px-2 py-0.5 text-xs font-semibold text-dbd-text">
                    {entity}
                  </span>
                </span>
              ))}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-dbd-muted">
              {synergy.explanation}
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}
