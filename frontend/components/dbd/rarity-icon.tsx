import { SmartImage } from "./smart-image"
import { getRarityBackgroundUrl } from "@/lib/rarity"
import { cn } from "@/lib/utils"

interface RarityIconProps {
  src?: string
  fallbackSrc?: string
  alt: string
  rarity?: string
  showPlus?: boolean
  className?: string
  fallbackLabel?: string
}


export function RarityIcon({
  src,
  fallbackSrc,
  alt,
  rarity,
  showPlus = false,
  className,
  fallbackLabel,
}: RarityIconProps) {
  const backgroundUrl = getRarityBackgroundUrl(rarity)

  return (
    <div className={cn("relative shrink-0", className)}>
      {backgroundUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={backgroundUrl}
          alt=""
          aria-hidden
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <div className="absolute inset-0 bg-dbd-panel-2" aria-hidden />
      )}

      <SmartImage
        src={src}
        fallbackSrc={fallbackSrc}
        alt={alt}
        fallbackLabel={fallbackLabel ?? alt}
        className="relative h-full w-full object-contain"
      />

      {showPlus ? (
        <span
          aria-hidden
          className="pointer-events-none absolute right-0 top-0 z-10 translate-x-[15%] -translate-y-[10%] font-[family-name:var(--font-oswald)] text-[0.85em] font-bold leading-none text-white drop-shadow-[0_1px_1px_rgba(0,0,0,0.9)]"
        >
          +
        </span>
      ) : null}
    </div>
  )
}
