import { MessageSquareText } from "lucide-react"

interface BuildPromptProps {
  prompt: string
}

/**
 * The request this build came from, hidden behind a click.
 *
 * A plain `<details>`: it needs no client JavaScript, works with a keyboard
 * and a screen reader for free, and a tap opens it on a phone — which a
 * hover tooltip would not.
 */
export function BuildPrompt({ prompt }: BuildPromptProps) {
  return (
    <details className="group relative">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 rounded-lg border border-dbd-border px-3 py-1.5 text-xs font-medium text-dbd-muted transition hover:border-dbd-purple/60 hover:text-dbd-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-dbd-purple [&::-webkit-details-marker]:hidden">
        <MessageSquareText className="h-3.5 w-3.5" aria-hidden />
        Prompt
      </summary>

      <div className="fixed left-3 right-3 z-30 mt-2 rounded-lg border border-dbd-border bg-[oklch(0.11_0.015_285)] p-4 text-left shadow-2xl sm:absolute sm:left-auto sm:right-0 sm:w-[min(22rem,80vw)]">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-dbd-muted/70">
          Asked for
        </p>
        <p className="mt-2 whitespace-pre-line text-xs leading-relaxed text-dbd-text/90">
          {prompt}
        </p>
      </div>
    </details>
  )
}
