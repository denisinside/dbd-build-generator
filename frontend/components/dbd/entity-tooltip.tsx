import type { ReactNode } from "react"
import { cn } from "@/lib/utils"


interface EntityTooltipProps {
  name: string
  description?: string
  /** Who teaches this perk. Shown as a label above the wiki text. */
  character?: string
  /** Why the generator picked it for this build, as opposed to what it does. */
  reason?: string
  children: ReactNode
}


export function EntityTooltip({
  name,
  description,
  character,
  reason,
  children,
}: EntityTooltipProps) {
  const spoken = [character, description, reason].filter(Boolean).join(". ")

  return (
    <div
      className="entity-tooltip-trigger relative inline-flex rounded-md outline-none focus-visible:ring-2 focus-visible:ring-dbd-purple"
      tabIndex={0}
      aria-label={`${name}. ${spoken || "Description unavailable."}`}
    >
      {children}

      <div
        role="tooltip"
        className={cn(
          // Hidden with `display: none`, not `visibility`: an invisible
          // absolute box 288px wide still widens the document, which is what
          // let a phone scroll sideways.
          "entity-tooltip-content pointer-events-none hidden rounded-lg border border-dbd-border bg-[oklch(0.11_0.015_285)] p-4 text-left shadow-2xl",
          // Phone: a sheet pinned to the viewport, so a tooltip on the
          // left-most icon cannot fall off the left edge.
          "fixed bottom-3 left-3 right-3 z-50",
          // Wide enough for the anchored tooltip: back under the trigger.
          "sm:absolute sm:bottom-auto sm:left-1/2 sm:right-auto sm:top-full sm:mt-3 sm:w-72 sm:-translate-x-1/2",
        )}
      >
        <div
          aria-hidden
          className="absolute -top-1.5 left-1/2 hidden h-3 w-3 -translate-x-1/2 rotate-45 border-l border-t border-dbd-border bg-[oklch(0.11_0.015_285)] sm:block"
        />
        <p className="relative font-[family-name:var(--font-oswald)] text-sm font-semibold text-dbd-text">
          {name}
        </p>

        {character ? (
          <p className="relative mt-1 text-[10px] font-semibold uppercase tracking-wider text-dbd-purple">
            {character}
          </p>
        ) : null}

        <p className="relative mt-2 whitespace-pre-line text-xs leading-relaxed text-dbd-muted">
          {description ?? "Description unavailable."}
        </p>

        {reason ? (
          // What it does comes from the wiki; why it is here comes from the
          // generator. Keeping them visually apart stops the second from
          // reading like official text.
          <div className="relative mt-3 border-t border-dbd-border/70 pt-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-dbd-muted/70">
              Why it is here
            </p>
            <p className="mt-1 text-xs leading-relaxed text-dbd-text/90">{reason}</p>
          </div>
        ) : null}
      </div>
    </div>
  )
}
