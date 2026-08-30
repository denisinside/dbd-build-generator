"use client"

import { FormEvent, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { LoaderCircle, Sparkles } from "lucide-react"
import { Footer } from "@/components/dbd/footer"
import { buildPath, fetchFeed, fetchMyBuilds, streamBuild } from "@/lib/api"
import type { BuildStep } from "@/lib/api"
import { getSessionId } from "@/lib/session"
import type { BuildSummary } from "@/types/build"


// A build takes a minute to make, so anything faster than this only adds load.
const FEED_REFRESH_MS = 10_000

const STAGE_LABELS: Record<string, string> = {
  classifying: "Request",
  research: "Research",
  drafting: "Drafting",
  validating: "Validation",
  enriching: "Finishing",
}


export default function Page() {
  const router = useRouter()
  const [prompt, setPrompt] = useState("")
  const [feed, setFeed] = useState<BuildSummary[]>([])
  const [mine, setMine] = useState<BuildSummary[]>([])
  const [steps, setSteps] = useState<BuildStep[]>([])
  const [generating, setGenerating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    // Navigating to a build unmounts this page, so late responses are dropped.
    let cancelled = false

    async function refresh() {
      try {
        const sessionId = getSessionId()
        const [everyone, own] = await Promise.all([
          fetchFeed(),
          fetchMyBuilds(sessionId),
        ])

        if (!cancelled) {
          setFeed(everyone)
          setMine(own)
        }
      } catch {
        // A failed poll keeps whatever was already on screen; the next tick
        // retries on its own.
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    refresh()
    const timer = setInterval(refresh, FEED_REFRESH_MS)

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError("")
    setSteps([])
    setGenerating(true)

    try {
      const build = await streamBuild(prompt, getSessionId(), (step) =>
        setSteps((current) => [...current, step]),
      )

      // Every build lives at its own URL, so it can be shared straight away.
      router.push(buildPath(build.id))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
      setGenerating(false)
    }
  }

  if (generating) {
    return <GeneratingView steps={steps} />
  }

  return (
    <main className="relative min-h-screen overflow-hidden">
      <AtmosphericBackground />

      <section className="mx-auto flex w-full max-w-6xl flex-col px-4 py-14 md:px-6 md:py-20">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-dbd-purple">
            Dead by Daylight
          </p>
          <h1 className="mt-4 font-[family-name:var(--font-oswald)] text-4xl font-bold uppercase tracking-wide text-dbd-text md:text-6xl">
            AI Build Generator
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-dbd-muted md:text-base">
            Describe your role, playstyle, character, or goal. The RAG agent will research
            the data and create a complete build.
          </p>
        </div>

        <form
          onSubmit={handleGenerate}
          className="mx-auto mt-10 flex w-full max-w-3xl flex-col gap-4 rounded-xl border border-dbd-border bg-dbd-panel p-4 shadow-[0_0_60px_-30px_var(--dbd-purple)] md:p-6"
        >
          <label
            htmlFor="build-prompt"
            className="font-[family-name:var(--font-oswald)] text-sm font-semibold uppercase tracking-wider text-dbd-text"
          >
            Describe your build
          </label>
          <textarea
            id="build-prompt"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            minLength={3}
            maxLength={1000}
            required
            rows={5}
            placeholder="Example: Create a Survivor build for fast generator repairs and safe escapes."
            className="resize-y rounded-lg border border-dbd-border bg-black/20 px-4 py-3 text-sm leading-relaxed text-dbd-text outline-none transition placeholder:text-dbd-muted/60 focus:border-dbd-purple focus:ring-2 focus:ring-dbd-purple/20"
          />
          <button
            type="submit"
            className="flex items-center justify-center gap-2 rounded-lg bg-dbd-purple px-5 py-3 font-[family-name:var(--font-oswald)] text-sm font-bold uppercase tracking-wider text-white transition hover:brightness-110 focus:outline-none focus:ring-2 focus:ring-dbd-purple focus:ring-offset-2 focus:ring-offset-dbd-bg"
          >
            <Sparkles className="h-4 w-4" aria-hidden />
            Generate Build
          </button>
        </form>

        {error ? (
          <p
            role="alert"
            className="mx-auto mt-5 w-full max-w-3xl rounded-lg border border-dbd-con/30 bg-dbd-con/10 px-4 py-3 text-sm text-dbd-text"
          >
            {error}
          </p>
        ) : null}

        <div className="mt-16 grid gap-10 lg:grid-cols-[1.6fr_1fr]">
          <BuildColumn
            id="feed-heading"
            title="Live Feed"
            live
            builds={feed}
            loading={loading}
            emptyText="No builds yet. Generate the first one above."
            columns="sm:grid-cols-2"
          />
          <BuildColumn
            id="mine-heading"
            title="Your Builds"
            builds={mine}
            loading={loading}
            emptyText="Builds you generate in this browser show up here."
            columns=""
          />
        </div>
      </section>

      <Footer />
    </main>
  )
}


interface BuildColumnProps {
  id: string
  title: string
  builds: BuildSummary[]
  loading: boolean
  emptyText: string
  columns: string
  live?: boolean
}

function BuildColumn({
  id,
  title,
  builds,
  loading,
  emptyText,
  columns,
  live,
}: BuildColumnProps) {
  return (
    <section aria-labelledby={id}>
      <div className="flex items-center gap-3">
        <h2
          id={id}
          className="font-[family-name:var(--font-oswald)] text-2xl font-bold uppercase tracking-wide text-dbd-text"
        >
          {title}
        </h2>
        {live ? (
          <span className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-dbd-purple">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-dbd-purple opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-dbd-purple" />
            </span>
            Live
          </span>
        ) : null}
      </div>
      <div className="mt-3 h-px bg-dbd-border" />

      {loading ? (
        <p className="mt-8 text-sm text-dbd-muted">Loading...</p>
      ) : builds.length === 0 ? (
        <p className="mt-8 text-sm text-dbd-muted">{emptyText}</p>
      ) : (
        <div className={`mt-6 grid gap-4 ${columns}`}>
          {builds.map((build) => (
            <Link
              key={build.id}
              href={buildPath(build.id)}
              className="group rounded-lg border border-dbd-border bg-dbd-panel p-5 text-left transition hover:-translate-y-1 hover:border-dbd-purple/60 hover:shadow-[0_12px_35px_-22px_var(--dbd-purple)]"
            >
              <span className="text-xs font-semibold uppercase tracking-wider text-dbd-purple">
                {build.role}
              </span>
              <h3 className="mt-2 font-[family-name:var(--font-oswald)] text-xl font-semibold uppercase text-dbd-text">
                {build.build_title}
              </h3>
              <p className="mt-2 text-sm text-dbd-muted">{build.character_name}</p>
              <div className="mt-5 flex items-center justify-between text-xs text-dbd-muted">
                <span>Score {build.build_score}/10</span>
                <time dateTime={build.created_at}>{formatDate(build.created_at)}</time>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}


function GeneratingView({ steps }: { steps: BuildStep[] }) {
  const endOfLog = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endOfLog.current?.scrollIntoView({ block: "nearest" })
  }, [steps.length])

  const current = steps[steps.length - 1]

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-14">
      <AtmosphericBackground />
      <div className="flex w-full max-w-2xl flex-col items-center text-center">
        <LoaderCircle className="h-12 w-12 animate-spin text-dbd-purple" aria-hidden />
        <p className="mt-6 font-[family-name:var(--font-oswald)] text-xl font-semibold uppercase tracking-wide text-dbd-text">
          {current ? STAGE_LABELS[current.stage] ?? current.stage : "Starting up"}
        </p>
        <p className="mt-2 text-sm text-dbd-muted">This usually takes a minute.</p>

        <div
          aria-live="polite"
          className="mt-8 max-h-72 w-full overflow-y-auto rounded-xl border border-dbd-border bg-dbd-panel/70 p-4 text-left"
        >
          {steps.length === 0 ? (
            <p className="text-sm text-dbd-muted">Waking the research agent...</p>
          ) : (
            <ol className="flex flex-col gap-2">
              {steps.map((step, index) => (
                <li
                  key={index}
                  className={`flex gap-3 text-sm transition ${
                    index === steps.length - 1 ? "text-dbd-text" : "text-dbd-muted/70"
                  }`}
                >
                  <span className="shrink-0 pt-0.5 text-[10px] font-semibold uppercase tracking-[0.15em] text-dbd-purple">
                    {STAGE_LABELS[step.stage] ?? step.stage}
                  </span>
                  <span className="break-words">{step.detail}</span>
                </li>
              ))}
            </ol>
          )}
          <div ref={endOfLog} />
        </div>
      </div>
    </main>
  )
}


function AtmosphericBackground() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,oklch(0.2_0.04_300/0.55),transparent_55%),radial-gradient(ellipse_at_bottom,oklch(0.16_0.03_320/0.4),transparent_60%)]"
    />
  )
}


function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value))
}


function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message
  }

  return "An unexpected error occurred."
}
