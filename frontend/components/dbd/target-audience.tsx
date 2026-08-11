import type { AudienceItem } from "@/types/build"
import { SectionHeading } from "./section-heading"
import { getIcon } from "@/lib/icon-registry"

interface TargetAudienceProps {
  items: AudienceItem[]
}

export function TargetAudience({ items }: TargetAudienceProps) {
  return (
    <section aria-label="Target audience">
      <SectionHeading>Target Audience</SectionHeading>
      <ul className="flex flex-col gap-4">
        {items.map((item, i) => {
          const Icon = getIcon(item.icon)
          return (
            <li key={i} className="flex items-start gap-4">
              <Icon className="mt-0.5 h-6 w-6 shrink-0 text-dbd-text/80" aria-hidden />
              <div>
                <h3 className="text-sm font-semibold text-dbd-text">{item.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-dbd-muted">{item.description}</p>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
