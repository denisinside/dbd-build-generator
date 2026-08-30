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


export async function fetchHistory(): Promise<BuildSummary[]> {
  const response = await fetch(`${API_URL}/api/builds`, { cache: "no-store" })

  if (!response.ok) {
    throw new Error("Could not load build history.")
  }

  return (await response.json()) as BuildSummary[]
}


export async function generateBuild(prompt: string): Promise<GeneratedBuild> {
  const response = await fetch(`${API_URL}/api/builds/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  })
  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail ?? "Build generation failed.")
  }

  return data as GeneratedBuild
}


export function buildPath(buildId: string) {
  return `/build/${buildId}`
}
