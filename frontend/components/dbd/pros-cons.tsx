import type { BuildPoint } from "@/types/build"
import { getIcon } from "@/lib/icon-registry"
import { Plus, Minus } from "lucide-react"
import { cn } from "@/lib/utils"

interface ProsConsProps {
  pros: BuildPoint[]
  cons: BuildPoint[]
}

export function ProsCons({ pros, cons }: ProsConsProps) {
  return (
    <section aria-label="Pros and cons" className="grid gap-4 md:grid-cols-2">
      <PointsPanel variant="pro" points={pros} />
      <PointsPanel variant="con" points={cons} />
    </section>
  )
}

function PointsPanel({
  variant,
  points,
}: {
  variant: "pro" | "con"
  points: BuildPoint[]
}) {
  const isPro = variant === "pro"
  const BadgeIcon = isPro ? Plus : Minus

  return (
    <div
      className={cn(
        "relative flex items-center gap-5 overflow-hidden rounded-lg border p-5 md:p-6",
        isPro ? "border-dbd-pro/25 bg-dbd-pro/[0.08]" : "border-dbd-con/25 bg-dbd-con/[0.08]",
      )}
    >
      <div
        aria-hidden
        className={cn(
          "pointer-events-none absolute -left-16 -top-16 h-40 w-40 rounded-full blur-3xl",
          isPro ? "bg-dbd-pro/15" : "bg-dbd-con/15",
        )}
      />

      <span
        className={cn(
          "relative flex h-12 w-12 shrink-0 items-center justify-center rounded-full border",
          isPro
            ? "border-dbd-pro/40 bg-dbd-pro/15 text-dbd-pro"
            : "border-dbd-con/40 bg-dbd-con/15 text-dbd-con",
        )}
      >
        <BadgeIcon className="h-6 w-6" aria-hidden />
      </span>

      <div className="relative flex-1">
        <h2 className="mb-3 font-[family-name:var(--font-oswald)] text-sm font-bold uppercase tracking-wider text-dbd-text">
          {isPro ? "Pros" : "Cons"}
        </h2>
        <ul className="flex flex-col gap-3">
        {points.map((point, i) => {
          const Icon = getIcon(point.icon)
          return (
            <li key={i} className="flex items-start gap-2.5">
              <Icon
                className={cn("mt-0.5 h-5 w-5 shrink-0", isPro ? "text-dbd-pro" : "text-dbd-con")}
                aria-hidden
              />
              <div>
                <h3 className="text-xs font-semibold leading-tight text-dbd-text">
                  {point.title}
                </h3>
                {point.description ? (
                  <p className="mt-1 text-[11px] leading-relaxed text-dbd-muted">
                    {point.description}
                  </p>
                ) : null}
              </div>
            </li>
          )
        })}
        </ul>
      </div>
    </div>
  )
}
