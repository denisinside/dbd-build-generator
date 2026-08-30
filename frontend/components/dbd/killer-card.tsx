import type { CounterMatchup } from "@/types/build"
import { SmartImage } from "./smart-image"
import { DIFFICULTY_CONFIG } from "@/lib/difficulty"
import { cn } from "@/lib/utils"

interface KillerCardProps {
  counter: CounterMatchup
}

export function KillerCard({ counter }: KillerCardProps) {
  const diff = DIFFICULTY_CONFIG[counter.difficulty]

  return (
    <div className="flex w-36 flex-col items-center text-center">
      <div className="relative">
        <SmartImage
          src={counter.image}
          fallbackSrc={counter.imageFallback}
          alt={counter.name}
          fallbackLabel={counter.name}
          className="h-[74px] w-[74px] rounded-full border border-dbd-border bg-dbd-panel-2 md:h-[92px] md:w-[92px]"
        />
        <span
          className={cn(
            "absolute bottom-1 right-1 h-4 w-4 rounded-full border-2 border-dbd-bg md:h-[18px] md:w-[18px]",
            diff.dotClass,
          )}
          role="img"
          aria-label={`${counter.name}: ${diff.label}`}
        />
      </div>
      <h3 className="mt-3 text-xs font-semibold text-dbd-text">{counter.name}</h3>
      <p className={cn("mt-1 text-[10px] font-semibold", diff.textClass)}>{diff.label}</p>
      <p className="mt-2 text-[10px] leading-relaxed text-dbd-muted">{counter.reason}</p>
    </div>
  )
}
