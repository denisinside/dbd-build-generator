"use client"

import { FormEvent, useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { LoaderCircle, Sparkles } from "lucide-react"
import { Footer } from "@/components/dbd/footer"
import { buildPath, fetchHistory, generateBuild } from "@/lib/api"
import type { BuildSummary } from "@/types/build"


export default function Page() {
  const router = useRouter()
  const [prompt, setPrompt] = useState("")
  const [history, setHistory] = useState<BuildSummary[]>([])
  const [generating, setGenerating] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    // Navigating to a build unmounts this page, so late responses are dropped.
    let cancelled = false

    async function loadHistory() {
      setHistoryLoading(true)

      try {
        const builds = await fetchHistory()

        if (!cancelled) {
          setHistory(builds)
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(getErrorMessage(requestError))
        }
      } finally {
        if (!cancelled) {
          setHistoryLoading(false)
        }
      }
    }

    loadHistory()

    return () => {
      cancelled = true
    }
  }, [])

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError("")
    setGenerating(true)

    try {
      const build = await generateBuild(prompt)

      // Every build lives at its own URL, so it can be shared straight away.
      router.push(buildPath(build.id))
    } catch (requestError) {
      setError(getErrorMessage(requestError))
      setGenerating(false)
    }
  }

  if (generating) {
    return <LoadingView />
  }

  return (
    <main className="relative min-h-screen overflow-hidden">
      <AtmosphericBackground />

      <section className="mx-auto flex w-full max-w-5xl flex-col px-4 py-14 md:px-6 md:py-20">
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

        <section className="mt-16" aria-labelledby="history-heading">
          <h2
            id="history-heading"
            className="font-[family-name:var(--font-oswald)] text-2xl font-bold uppercase tracking-wide text-dbd-text"
          >
            Build History
          </h2>
          <div className="mt-3 h-px bg-dbd-border" />

          {historyLoading ? (
            <p className="mt-8 text-sm text-dbd-muted">Loading build history...</p>
          ) : history.length === 0 ? (
            <p className="mt-8 text-sm text-dbd-muted">
              No builds yet. Generate your first build above.
            </p>
          ) : (
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {history.map((build) => (
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
      </section>

      <Footer />
    </main>
  )
}


function LoadingView() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <AtmosphericBackground />
      <div className="flex flex-col items-center text-center">
        <LoaderCircle className="h-12 w-12 animate-spin text-dbd-purple" aria-hidden />
        <p className="mt-6 font-[family-name:var(--font-oswald)] text-xl font-semibold uppercase tracking-wide text-dbd-text">
          Researching meta and generating build via AI...
        </p>
        <p className="mt-2 text-sm text-dbd-muted">This can take a minute.</p>
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
