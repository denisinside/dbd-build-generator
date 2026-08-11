import { cn } from "@/lib/utils"

interface SectionHeadingProps {
  children: React.ReactNode
  className?: string
}

export function SectionHeading({ children, className }: SectionHeadingProps) {
  return (
    <div className={cn("mb-4", className)}>
      <h2 className="font-[family-name:var(--font-oswald)] text-xl font-bold uppercase tracking-wide text-dbd-text md:text-[26px]">
        {children}
      </h2>
      <div className="mt-2 h-px w-full bg-dbd-border/80" />
    </div>
  )
}
