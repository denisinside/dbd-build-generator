"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"

interface SmartImageProps {
  src?: string
  /** Tried once if `src` fails — the remote wiki copy of a mirrored icon. */
  fallbackSrc?: string
  alt: string
  className?: string
  /** Native tooltip shown on hover. */
  title?: string
  /** Shown when there is no src or the image fails to load. */
  fallbackLabel?: string
}

/**
 * Image with a graceful fallback chain: local copy, then the remote wiki URL,
 * then a muted placeholder with initials. Preserves whatever aspect/shape the
 * container defines (circle, square, etc.).
 */
export function SmartImage({
  src,
  fallbackSrc,
  alt,
  className,
  title,
  fallbackLabel,
}: SmartImageProps) {
  const [failedSources, setFailedSources] = useState<string[]>([])
  const candidates = [src, fallbackSrc].filter(
    (candidate): candidate is string => Boolean(candidate),
  )
  const currentSrc = candidates.find((candidate) => !failedSources.includes(candidate))

  if (!currentSrc) {
    const label = (fallbackLabel ?? alt ?? "?").trim()
    const initials = label
      .split(/\s+/)
      .slice(0, 2)
      .map((w) => w[0]?.toUpperCase() ?? "")
      .join("")

    return (
      <div
        role="img"
        aria-label={alt}
        title={title}
        className={cn(
          "flex items-center justify-center bg-dbd-panel-2 text-dbd-muted select-none",
          className,
        )}
      >
        <span className="font-[family-name:var(--font-oswald)] text-sm tracking-wide">
          {initials || "?"}
        </span>
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      key={currentSrc}
      src={currentSrc}
      alt={alt}
      title={title}
      onError={() =>
        setFailedSources((current) =>
          current.includes(currentSrc) ? current : [...current, currentSrc],
        )
      }
      className={cn("object-cover", className)}
    />
  )
}
