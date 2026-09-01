"use client"

import { useRouter } from "next/navigation"
import { Dices } from "lucide-react"
import { setPendingPrompt } from "@/lib/session"

interface AnotherVariantProps {
  prompt: string
}

/**
 * Run the same request again. The research and drafting stages are no longer
 * at temperature 0, so a second pass really does produce a different build.
 *
 * The prompt travels in sessionStorage rather than the URL on purpose: a
 * `?prompt=...&go=1` link would let anyone post a URL that spends money on
 * every viewer who opens it, and there is no global budget cap to stop that.
 * A tab-local handoff cannot be shared, so only a real click can start one.
 */
export function AnotherVariant({ prompt }: AnotherVariantProps) {
  const router = useRouter()

  return (
    <button
      type="button"
      onClick={() => {
        setPendingPrompt(prompt, true)
        router.push("/")
      }}
      className="flex items-center gap-1.5 rounded-lg border border-dbd-purple/40 bg-dbd-purple/10 px-3 py-1.5 text-xs font-medium text-dbd-text transition hover:border-dbd-purple hover:bg-dbd-purple/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-dbd-purple"
    >
      <Dices className="h-3.5 w-3.5" aria-hidden />
      Another variant
    </button>
  )
}
