import { getAuthToken, getSessionId } from "@/lib/session"
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


export interface AuthUser {
  id: string
  provider: string
  display_name: string | null
  avatar_url: string | null
}


export interface SignInProvider {
  id: string
  name: string
}


/**
 * Who the caller is, as far as the API is concerned.
 *
 * The session token is what the API verifies. The anonymous id rides along so
 * a visitor who has not signed in still has a personal list, and so the
 * builds they made before signing in can be claimed afterwards.
 */
function identityHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  const token = getAuthToken()
  const sessionId = getSessionId()

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  if (sessionId) {
    headers["X-Session-Id"] = sessionId
  }

  return headers
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
  const response = await fetch(`${API_URL}/api/builds?${params}`, {
    cache: "no-store",
    headers: identityHeaders(),
  })

  if (!response.ok) {
    throw new Error("Could not load builds.")
  }

  return (await response.json()) as BuildSummary[]
}


/** The shared feed: the newest builds from everyone. */
export function fetchFeed(limit = 30): Promise<BuildSummary[]> {
  return fetchSummaries(new URLSearchParams({ limit: String(limit) }))
}


/** The caller's own builds: their account's, or this browser's when signed out. */
export function fetchMyBuilds(): Promise<BuildSummary[]> {
  return fetchSummaries(new URLSearchParams({ mine: "1", limit: "30" }))
}


// --- sign-in ---------------------------------------------------------------


/** Providers the API actually has credentials for. Empty means sign-in is off. */
export async function fetchProviders(): Promise<SignInProvider[]> {
  const response = await fetch(`${API_URL}/auth/providers`, { cache: "no-store" })

  if (!response.ok) {
    return []
  }

  return (await response.json()) as SignInProvider[]
}


/** Where to send the browser to start the OAuth handshake. */
export function signInUrl(provider: string, next = "/") {
  return `${API_URL}/auth/${provider}/login?next=${encodeURIComponent(next)}`
}


/** The signed-in user, or null. A rejected token is treated as signed out. */
export async function fetchMe(): Promise<AuthUser | null> {
  if (!getAuthToken()) {
    return null
  }

  const response = await fetch(`${API_URL}/auth/me`, {
    cache: "no-store",
    headers: identityHeaders(),
  })

  if (!response.ok) {
    return null
  }

  return (await response.json()) as AuthUser
}


/** Move this browser's anonymous builds onto the account that just signed in. */
export async function claimAnonymousBuilds(): Promise<number> {
  const response = await fetch(`${API_URL}/auth/claim`, {
    method: "POST",
    headers: identityHeaders(),
  })

  if (!response.ok) {
    return 0
  }

  return ((await response.json()) as { claimed: number }).claimed
}


// --- generation ------------------------------------------------------------


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
  onStep: (step: BuildStep) => void,
): Promise<GeneratedBuild> {
  const response = await fetch(`${API_URL}/api/builds/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...identityHeaders() },
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
