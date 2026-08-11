import type { Evaluation } from "@/types/build"

interface BuildEvaluationProps {
  evaluation: Evaluation
}

export function BuildEvaluation({ evaluation }: BuildEvaluationProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 text-center">
      <span className="text-xs font-semibold uppercase tracking-[0.15em] text-dbd-muted">
        Build Score
      </span>
      <div className="font-[family-name:var(--font-oswald)] leading-none">
        <span className="text-5xl font-bold text-dbd-text md:text-6xl">{evaluation.score}</span>
        <span className="text-2xl font-semibold text-dbd-muted md:text-3xl">/{evaluation.maxScore}</span>
      </div>
    </div>
  )
}
