import type { CounterPerk, Role } from "@/types/build"
import { SmartImage } from "./smart-image"
import { EntityTooltip } from "./entity-tooltip"

interface CounterPerksProps {
  counterPerks: CounterPerk[]
  role: Role
}

/**
 * What the other side brings against this build.
 *
 * For a Killer build this is the whole answer to "what beats it": maps are not
 * in the data, so a list of bad maps would be invention, while every perk here
 * is checked against MongoDB and against the opposing role.
 */
export function CounterPerks({ counterPerks, role }: CounterPerksProps) {
  if (counterPerks.length === 0) {
    return null
  }

  const opposing = role === "Survivor" ? "Killer" : "Survivor"

  return (
    <section aria-labelledby="counter-perks-heading" className="flex flex-col items-center">
      <h2
        id="counter-perks-heading"
        className="text-center font-[family-name:var(--font-oswald)] text-lg font-bold uppercase tracking-wide text-dbd-text md:text-2xl"
      >
        Counter Perks
      </h2>
      <p className="mt-1 text-center text-xs text-dbd-muted">
        {opposing} perks that blunt this build, and how to play around them
      </p>

      <ul className="mt-6 grid w-full gap-4 sm:grid-cols-3">
        {counterPerks.map((counter) => (
          <li
            key={counter.name}
            className="flex flex-col items-center rounded-lg border border-dbd-border bg-dbd-panel p-5 text-center"
          >
            <SmartImage
              src={counter.image}
              fallbackSrc={counter.imageFallback}
              alt={counter.name}
              fallbackLabel={counter.name}
              className="h-14 w-14 rounded-full border border-dbd-border bg-dbd-panel-2"
            />
            <EntityTooltip
              name={counter.name}
              description={counter.description}
              character={counter.character}
            >
              <h3 className="mt-3 cursor-help text-sm font-semibold text-dbd-text underline decoration-dotted decoration-dbd-text/40 underline-offset-2">
                {counter.name}
              </h3>
            </EntityTooltip>

            {counter.character ? (
              <p className="mt-0.5 text-[10px] font-semibold uppercase tracking-wider text-dbd-purple">
                {counter.character}
              </p>
            ) : null}

            <p className="mt-3 border-t border-dbd-border/70 pt-3 text-[11px] leading-relaxed text-dbd-text/90">
              {counter.explanation}
            </p>
          </li>
        ))}
      </ul>
    </section>
  )
}
