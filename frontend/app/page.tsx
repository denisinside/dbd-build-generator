"use client"

import { FormEvent, useEffect, useState } from "react"
import { LoaderCircle, Sparkles } from "lucide-react"
import { BuildPage } from "@/components/dbd/build-page"
import { adaptGeneratedBuild } from "@/lib/build-adapter"
import type { BuildSummary, GeneratedBuild } from "@/types/build"


const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"


export default function Page() {
  const [prompt, setPrompt] = useState("")
  const [history, setHistory] = useState<BuildSummary[]>([])
  const [selectedBuild, setSelectedBuild] = useState<GeneratedBuild | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState(
    "Researching meta and generating build via AI...",
  )
  const [historyLoading, setHistoryLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    loadHistory()
  }, [])

  async function loadHistory() {
    setHistoryLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/builds`)
      if (!response.ok) {
        throw new Error("Could not load build history.")
      }

      const builds: BuildSummary[] = await response.json()
      setHistory(builds)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setHistoryLoading(false)
    }
  }

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError("")
    setLoadingMessage("Researching meta and generating build via AI...")
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/builds/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt }),
      })
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail ?? "Build generation failed.")
      }

      const build = data as GeneratedBuild
      setSelectedBuild(build)
      setHistory((current) => [
        {
          id: build.id,
          build_title: build.build_title,
          character_name: build.character_name,
          role: build.role,
          build_score: build.build_score,
          created_at: build.created_at,
        },
        ...current,
      ])
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  async function openBuild(buildId: string) {
    setError("")
    setLoadingMessage("Loading saved build...")
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/builds/${buildId}`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail ?? "Could not load this build.")
      }

      setSelectedBuild(data as GeneratedBuild)
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <LoadingView message={loadingMessage} />
  }

  if (selectedBuild) {
    return (
      <BuildPage
        build={adaptGeneratedBuild(selectedBuild)}
        onBack={() => setSelectedBuild(null)}
      />
    )
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
                <button
                  key={build.id}
                  type="button"
                  onClick={() => openBuild(build.id)}
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
                </button>
              ))}
            </div>
          )}
        </section>
      </section>
    </main>
  )
}


function LoadingView({ message }: { message: string }) {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <AtmosphericBackground />
      <div className="flex flex-col items-center text-center">
        <LoaderCircle className="h-12 w-12 animate-spin text-dbd-purple" aria-hidden />
        <p className="mt-6 font-[family-name:var(--font-oswald)] text-xl font-semibold uppercase tracking-wide text-dbd-text">
          {message}
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
