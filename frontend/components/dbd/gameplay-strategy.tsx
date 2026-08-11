import type { Strategy, StrategyStep } from "@/types/build"
import { SectionHeading } from "./section-heading"
import { cn } from "@/lib/utils"

interface GameplayStrategyProps {
  strategy: Strategy
}

const STAGES: { key: keyof Strategy; label: string; accent: string }[] = [
  { key: "early", label: "Early Game", accent: "text-dbd-accent" },
  { key: "mid", label: "Mid Game", accent: "text-dbd-accent" },
  { key: "late", label: "Late Game", accent: "text-dbd-con" },
]

export function GameplayStrategy({ strategy }: GameplayStrategyProps) {
  return (
    <section aria-label="Game tactics">
      <SectionHeading>Game Tactics</SectionHeading>
      <div className="flex flex-col gap-5">
        {STAGES.map(({ key, label, accent }) => {
          const steps = strategy[key]
          if (!steps || steps.length === 0) return null
          return <StrategyStage key={key} label={label} accent={accent} steps={steps} />
        })}
      </div>
    </section>
  )
}

function StrategyStage({ label, accent, steps }: { label: string; accent: string; steps: StrategyStep[] }) {
  return (
    <div>
      <h3 className="mb-2.5 font-[family-name:var(--font-oswald)] text-base font-semibold uppercase tracking-wide text-dbd-muted">
        {label}:
      </h3>
      <div className="flex flex-col gap-3">
        {steps.map((step, i) => (
          <div key={i}>
            <h4 className={cn("text-sm font-bold", accent)}>{step.title}</h4>
            <p className="mt-0.5 text-sm leading-relaxed text-dbd-text/85">{step.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
