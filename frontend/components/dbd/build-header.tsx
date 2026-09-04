import type { Build } from "@/types/build"
import { CharacterCard } from "./character-card"
import { PerksGrid } from "./perks-grid"
import { LoadoutCard } from "./loadout-card"
import { PowerCard } from "./power-card"
import { BuildEvaluation } from "./build-evaluation"

interface BuildHeaderProps {
  build: Build
}

export function BuildHeader({ build }: BuildHeaderProps) {
  return (
    <section
      aria-label="Build overview"
      className="rounded-lg border border-dbd-border bg-[oklch(0.09_0.012_285)] p-3 shadow-[0_0_40px_-24px_var(--dbd-purple)] sm:p-4 md:p-5"
    >
      <div className="grid gap-7 sm:grid-cols-[minmax(160px,1fr)_auto_minmax(200px,1.2fr)_auto_100px] sm:items-center sm:gap-4 md:grid-cols-[minmax(220px,1fr)_auto_minmax(320px,1.35fr)_auto_140px] md:gap-5">
        {/* LEFT — character + perks */}
        <div className="mx-auto flex w-full max-w-sm flex-col gap-4 sm:mx-0">
          <CharacterCard character={build.character} />
          <PerksGrid perks={build.perks} />
        </div>

        <Divider />

        {/* CENTER — loadouts */}
        <div className="flex flex-col items-center gap-3">
          {/* Wraps rather than stacking: the two add-on variants belong side by
              side, and on a phone they only just fit. Anything narrower than
              they need drops the last one onto its own line by itself. */}
          <div className="flex flex-wrap items-start justify-center gap-3 sm:gap-5">
            {/* The power is fixed by the Killer, so it appears once beside the
                two add-on pairs rather than being repeated inside each. */}
            {build.power ? <PowerCard power={build.power} /> : null}
            {build.loadouts.map((loadout, i) => (
              <LoadoutCard key={i} loadout={loadout} />
            ))}
          </div>
        </div>

        <Divider />

        {/* RIGHT — evaluation */}
        <BuildEvaluation evaluation={build.evaluation} />
      </div>
    </section>
  )
}

function Divider() {
  return <div className="hidden h-28 w-px self-center bg-dbd-border/70 sm:block" aria-hidden />
}
