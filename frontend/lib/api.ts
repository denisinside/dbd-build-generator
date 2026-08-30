import type { BuildSummary, GeneratedBuild } from "@/types/build"


/**
 * Base URL of the FastAPI backend.
 *
 * `NEXT_PUBLIC_API_URL` is used by both the browser and the server, so the
 * value has to be reachable from both. `API_URL` overrides it server-side for
 * deployments where the API is reachable on an internal hostname.
 */
export const API_URL = (
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000"
).replace(/\/+$/, "")


/** One progress event from the generation stream. */
export interface BuildStep {
  stage: string
  detail: string
}


function sessionHeader(sessionId: string): Record<string, string> {
  return sessionId ? { "X-Session-Id": sessionId } : {}
}


export async function fetchBuild(buildId: string): Promise<GeneratedBuild | null> {
  // Opening a build can backfill missing descriptions and icons server-side,
  // so the response must never be cached.
  const response = await fetch(`${API_URL}/api/builds/${buildId}`, {
    cache: "no-store",
  })

  if (response.status === 404) {
    return null
  }

  if (!response.ok) {
    throw new Error("Could not load this build.")
  }

  return (await response.json()) as GeneratedBuild
}


async function fetchSummaries(params: URLSearchParams): Promise<BuildSummary[]> {
  const response = await fetch(`${API_URL}/api/builds?${params}`, { cache: "no-store" })

  if (!response.ok) {
    throw new Error("Could not load builds.")
  }

  return (await response.json()) as BuildSummary[]
}


/** The shared feed: the newest builds from everyone. */
export function fetchFeed(limit = 30): Promise<BuildSummary[]> {
  return fetchSummaries(new URLSearchParams({ limit: String(limit) }))
}


/** Builds generated from this browser. */
export function fetchMyBuilds(sessionId: string): Promise<BuildSummary[]> {
  if (!sessionId) {
    return Promise.resolve([])
  }

  return fetchSummaries(new URLSearchParams({ session: sessionId, limit: "30" }))
}


function parseFrame(frame: string) {
  let event = "message"
  const data: string[] = []

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim()
    } else if (line.startsWith("data:")) {
      data.push(line.slice("data:".length).trim())
    }
  }

  return { event, data: data.join("\n") }
}


/**
 * Generate a build, reporting every research step as it happens.
 *
 * A build takes minutes. Streaming keeps the connection busy (proxies cut
 * silent ones at 60-100s) and, more importantly, shows the agent working
 * instead of a spinner that cannot be told apart from a hang.
 */
export async function streamBuild(
  prompt: string,
  sessionId: string,
  onStep: (step: BuildStep) => void,
): Promise<GeneratedBuild> {
  const response = await fetch(`${API_URL}/api/builds/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...sessionHeader(sessionId) },
    body: JSON.stringify({ prompt }),
  })

  if (!response.ok || !response.body) {
    const failure = await response.json().catch(() => null)
    throw new Error(failure?.detail ?? "Build generation failed.")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let build: GeneratedBuild | null = null
  let failure: string | null = null

  for (;;) {
    const { done, value } = await reader.read()

    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })

    // Server-sent events are separated by a blank line, and a single read can
    // carry any number of whole or partial frames.
    let boundary = buffer.indexOf("\n\n")

    while (boundary !== -1) {
      const { event, data } = parseFrame(buffer.slice(0, boundary))
      buffer = buffer.slice(boundary + 2)

      if (event === "step") {
        onStep(JSON.parse(data) as BuildStep)
      } else if (event === "build") {
        build = JSON.parse(data) as GeneratedBuild
      } else if (event === "error") {
        failure = (JSON.parse(data) as { detail: string }).detail
      }

      boundary = buffer.indexOf("\n\n")
    }
  }

  if (failure) {
    throw new Error(failure)
  }

  if (build === null) {
    throw new Error("The connection dropped before the build was finished.")
  }

  return build
}


export function buildPath(buildId: string) {
  return `/build/${buildId}`
}
