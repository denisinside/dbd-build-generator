import Link from "next/link"
import type { Build } from "@/types/build"
import { PageTitle } from "./page-title"
import { AnotherVariant } from "./another-variant"
import { BuildPrompt } from "./build-prompt"
import { BuildHeader } from "./build-header"
import { BuildAxes } from "./build-evaluation"
import { BuildSynergies } from "./build-synergies"
import { TargetAudience } from "./target-audience"
import { GameplayStrategy } from "./gameplay-strategy"
import { ProsCons } from "./pros-cons"
import { CounterMatchups } from "./counter-matchups"
import { CounterPerks } from "./counter-perks"
import { Footer } from "./footer"

interface BuildPageProps {
  build: Build
  /** Where the back link goes. Defaults to the generator page. */
  backHref?: string
}

/**
 * The full build-details template. Everything it renders comes from the
 * single `build` prop — swap that object to display a different build.
 */
export function BuildPage({ build, backHref = "/" }: BuildPageProps) {
  return (
    <main className="relative min-h-screen">
      {/* Atmospheric background */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,oklch(0.2_0.04_300/0.5),transparent_55%),radial-gradient(ellipse_at_bottom,oklch(0.16_0.03_320/0.4),transparent_60%)]"
      />

      <div className="mx-auto w-full max-w-4xl px-3 pb-14 sm:px-4 md:px-5">
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <Link
            href={backHref}
            className="text-sm font-medium text-dbd-muted transition hover:text-dbd-text"
          >
            ← Generator / History
          </Link>

          {build.prompt ? (
            <div className="flex items-center gap-2">
              <BuildPrompt prompt={build.prompt} />
              <AnotherVariant prompt={build.prompt} />
            </div>
          ) : null}
        </div>

        <PageTitle title={build.title} />

        <div className="flex flex-col gap-9">
          <BuildHeader build={build} />
          <BuildAxes evaluation={build.evaluation} />
          <BuildSynergies
            synergies={build.synergies}
            perks={build.perks}
            loadouts={build.loadouts}
            power={build.power}
          />
          <TargetAudience items={build.targetAudience} />
          <GameplayStrategy strategy={build.strategy} />
          <ProsCons pros={build.pros} cons={build.cons} />
          <CounterMatchups counters={build.counters} />
          <CounterPerks counterPerks={build.counterPerks} role={build.role} />
        </div>
      </div>

      <Footer />
    </main>
  )
}
