import type { ReactNode } from "react"


interface EntityTooltipProps {
  name: string
  description?: string
  children: ReactNode
}


export function EntityTooltip({ name, description, children }: EntityTooltipProps) {
  return (
    <div
      className="entity-tooltip-trigger relative inline-flex rounded-md outline-none focus-visible:ring-2 focus-visible:ring-dbd-purple"
      tabIndex={0}
      aria-label={`${name}. ${description ?? "Description unavailable."}`}
    >
      {children}

      <div
        role="tooltip"
        className="entity-tooltip-content pointer-events-none invisible absolute left-1/2 top-full z-50 mt-3 w-72 -translate-x-1/2 rounded-lg border border-dbd-border bg-[oklch(0.11_0.015_285)] p-4 text-left opacity-0 shadow-2xl transition"
      >
        <div
          aria-hidden
          className="absolute -top-1.5 left-1/2 h-3 w-3 -translate-x-1/2 rotate-45 border-l border-t border-dbd-border bg-[oklch(0.11_0.015_285)]"
        />
        <p className="relative font-[family-name:var(--font-oswald)] text-sm font-semibold text-dbd-text">
          {name}
        </p>
        <p className="relative mt-2 whitespace-pre-line text-xs leading-relaxed text-dbd-muted">
          {description ?? "Description unavailable."}
        </p>
      </div>
    </div>
  )
}
