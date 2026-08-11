import type { CounterMatchup } from "@/types/build"
import { KillerCard } from "./killer-card"
import { DIFFICULTY_CONFIG, DIFFICULTY_ORDER } from "@/lib/difficulty"
import { cn } from "@/lib/utils"

interface CounterMatchupsProps {
  counters: CounterMatchup[]
}

export function CounterMatchups({ counters }: CounterMatchupsProps) {
  if (counters.length === 0) {
    return null
  }

  return (
    <section aria-label="Counter killers" className="flex flex-col items-center">
      <h2 className="mb-6 text-center font-[family-name:var(--font-oswald)] text-lg font-bold uppercase tracking-wide text-dbd-text md:text-2xl">
        Counter Killers
      </h2>

      <div className="flex w-full flex-wrap items-center justify-center gap-x-6 gap-y-6 md:gap-x-8">
        {counters.map((counter, i) => (
          <KillerCard key={`${counter.name}-${i}`} counter={counter} />
        ))}
      </div>

      {/* Difficulty legend */}
      <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-8 gap-y-3">
        {DIFFICULTY_ORDER.map((key) => {
          const diff = DIFFICULTY_CONFIG[key]
          return (
            <li key={key} className="flex items-center gap-2">
              <span className={cn("h-3.5 w-3.5 rounded-full", diff.dotClass)} aria-hidden />
              <span className="text-sm text-dbd-muted">{diff.label}</span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
