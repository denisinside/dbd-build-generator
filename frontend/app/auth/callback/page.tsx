"use client"

import { Suspense, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { LoaderCircle } from "lucide-react"
import { claimAnonymousBuilds } from "@/lib/api"
import { setAuthToken } from "@/lib/session"


/**
 * Where the API drops the browser after a successful OAuth handshake.
 *
 * The session token arrives in the URL fragment rather than the query string:
 * fragments are never sent to a server, so the token stays out of access logs
 * and out of the Referer header on the next navigation. It is read once,
 * stored, and wiped from the address bar.
 */
export default function AuthCallbackRoute() {
  return (
    <Suspense fallback={<Waiting />}>
      <AuthCallback />
    </Suspense>
  )
}


function AuthCallback() {
  const router = useRouter()
  // Failure is carried in the URL rather than in state, so the effect below
  // only ever navigates. A fragment is unreadable until the browser runs.
  const failed = useSearchParams().get("error") !== null

  useEffect(() => {
    if (failed) {
      return
    }

    const fragment = new URLSearchParams(window.location.hash.slice(1))
    const token = fragment.get("token")
    const next = fragment.get("next") ?? "/"

    if (!token) {
      router.replace("/auth/callback?error=sign_in_failed")
      return
    }

    setAuthToken(token)
    // Drop the token from the address bar before anything can copy the URL.
    window.history.replaceState(null, "", window.location.pathname)

    // Anything generated before signing in belongs to this person too.
    claimAnonymousBuilds().finally(() => router.replace(next))
  }, [failed, router])

  if (failed) {
    return (
      <Shell>
        <p className="font-[family-name:var(--font-oswald)] text-xl font-semibold uppercase tracking-wide text-dbd-text">
          Sign-in failed
        </p>
        <p className="mt-2 text-sm text-dbd-muted">
          The provider did not confirm your identity. Nothing was saved.
        </p>
        <button
          type="button"
          onClick={() => router.replace("/")}
          className="mt-6 rounded-lg border border-dbd-border px-4 py-2 text-sm text-dbd-text transition hover:border-dbd-purple/60"
        >
          Back to the generator
        </button>
      </Shell>
    )
  }

  return <Waiting />
}


function Waiting() {
  return (
    <Shell>
      <LoaderCircle className="h-10 w-10 animate-spin text-dbd-purple" aria-hidden />
      <p className="mt-6 text-sm text-dbd-muted">Signing you in...</p>
    </Shell>
  )
}


function Shell({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      {children}
    </main>
  )
}
