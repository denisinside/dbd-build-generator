"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"

interface SmartImageProps {
  src?: string
  alt: string
  className?: string
  /** Native tooltip shown on hover. */
  title?: string
  /** Shown when there is no src or the image fails to load. */
  fallbackLabel?: string
}

/**
 * Image with a graceful fallback. Preserves whatever aspect/shape the
 * container defines (circle, square, etc.). When the image is missing or
 * fails, it renders a muted placeholder with initials.
 */
export function SmartImage({ src, alt, className, title, fallbackLabel }: SmartImageProps) {
  const [failed, setFailed] = useState(false)
  const showFallback = !src || failed

  if (showFallback) {
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
      src={src || "/placeholder.svg"}
      alt={alt}
      title={title}
      onError={() => setFailed(true)}
      className={cn("object-cover", className)}
    />
  )
}
