interface PageTitleProps {
  /** The generated build title (data-driven). */
  title: string
}

export function PageTitle({ title }: PageTitleProps) {
  return (
    <header className="relative overflow-hidden pt-8 pb-6 text-center md:pt-10 md:pb-7">
      {/* Subtle purple decorative glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-0 h-40 w-[min(90vw,640px)] -translate-x-1/2 rounded-full bg-dbd-purple/20 blur-[90px]"
      />

      <h1 className="relative mx-auto max-w-4xl px-4 font-[family-name:var(--font-oswald)] text-[26px] font-bold uppercase leading-none tracking-[0.02em] text-dbd-text text-balance [text-shadow:0_0_24px_rgba(255,255,255,0.25)] md:text-4xl">
        {title}
      </h1>
    </header>
  )
}
