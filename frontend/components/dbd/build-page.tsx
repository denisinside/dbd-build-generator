import type { Build } from "@/types/build"
import { PageTitle } from "./page-title"
import { BuildHeader } from "./build-header"
import { TargetAudience } from "./target-audience"
import { GameplayStrategy } from "./gameplay-strategy"
import { ProsCons } from "./pros-cons"
import { CounterMatchups } from "./counter-matchups"
import { Footer } from "./footer"

interface BuildPageProps {
  build: Build
  onBack: () => void
}

/**
 * The full build-details template. Everything it renders comes from the
 * single `build` prop — swap that object to display a different build.
 */
export function BuildPage({ build, onBack }: BuildPageProps) {
  return (
    <main className="relative min-h-screen">
      {/* Atmospheric background */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,oklch(0.2_0.04_300/0.5),transparent_55%),radial-gradient(ellipse_at_bottom,oklch(0.16_0.03_320/0.4),transparent_60%)]"
      />

      <div className="mx-auto w-full max-w-4xl px-4 pb-14 md:px-5">
        <button
          type="button"
          onClick={onBack}
          className="mt-6 text-sm font-medium text-dbd-muted transition hover:text-dbd-text"
        >
          ← Back to Generator / History
        </button>

        <PageTitle title={build.title} />

        <div className="flex flex-col gap-9">
          <BuildHeader build={build} />
          <TargetAudience items={build.targetAudience} />
          <GameplayStrategy strategy={build.strategy} />
          <ProsCons pros={build.pros} cons={build.cons} />
          <CounterMatchups counters={build.counters} />
        </div>
      </div>

      <Footer />
    </main>
  )
}
