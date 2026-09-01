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


/**
 * The breakdown the headline score averages.
 *
 * A single number a model gave itself lands on 7 or 8 whatever the build is
 * and says nothing. Four named axes, each with a reason, can at least be
 * argued with — and they make two builds for the same role comparable.
 */
export function BuildAxes({ evaluation }: BuildEvaluationProps) {
  if (evaluation.axes.length === 0) {
    return null
  }

  return (
    <section aria-labelledby="axes-heading" className="rounded-lg border border-dbd-border bg-dbd-panel p-5">
      <h2
        id="axes-heading"
        className="font-[family-name:var(--font-oswald)] text-sm font-bold uppercase tracking-wider text-dbd-text"
      >
        Strengths
      </h2>

      <ul className="mt-4 grid gap-4 md:grid-cols-2">
        {evaluation.axes.map((axis) => (
          <li key={axis.label}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-dbd-text">
                {axis.label}
              </span>
              <span className="text-xs text-dbd-muted">
                {axis.score}/{axis.maxScore}
              </span>
            </div>

            <div
              className="mt-1.5 flex gap-1"
              role="img"
              aria-label={`${axis.label}: ${axis.score} of ${axis.maxScore}. ${axis.reason}`}
            >
              {Array.from({ length: axis.maxScore }, (_, step) => (
                <span
                  key={step}
                  className={`h-1.5 flex-1 rounded-full ${
                    step < axis.score ? "bg-dbd-purple" : "bg-dbd-border"
                  }`}
                />
              ))}
            </div>

            <p className="mt-2 text-[11px] leading-relaxed text-dbd-muted">{axis.reason}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
