"use client"

import { useEffect, useState } from "react"
import { LogOut } from "lucide-react"
import { SmartImage } from "@/components/dbd/smart-image"
import { fetchProviders, signInUrl, type AuthUser, type SignInProvider } from "@/lib/api"
import { clearAuthToken } from "@/lib/session"


interface SignInProps {
  user: AuthUser | null
  onSignOut: () => void
}

/**
 * Sign-in controls. Renders nothing when the API reports no configured
 * providers, so a deployment without OAuth credentials shows no dead buttons.
 */
export function SignIn({ user, onSignOut }: SignInProps) {
  const [providers, setProviders] = useState<SignInProvider[]>([])

  useEffect(() => {
    let cancelled = false

    fetchProviders()
      .then((available) => {
        if (!cancelled) {
          setProviders(available)
        }
      })
      .catch(() => {
        // Sign-in is optional; the generator works without it.
      })

    return () => {
      cancelled = true
    }
  }, [])

  if (user) {
    return (
      <div className="flex items-center gap-3">
        <SmartImage
          src={user.avatar_url ?? undefined}
          alt={user.display_name ?? "Your avatar"}
          fallbackLabel={user.display_name ?? "?"}
          className="h-8 w-8 rounded-full"
        />
        <span className="text-sm text-dbd-text">{user.display_name}</span>
        <button
          type="button"
          onClick={() => {
            clearAuthToken()
            onSignOut()
          }}
          className="flex items-center gap-1.5 rounded-lg border border-dbd-border px-3 py-1.5 text-xs uppercase tracking-wider text-dbd-muted transition hover:border-dbd-purple/60 hover:text-dbd-text"
        >
          <LogOut className="h-3.5 w-3.5" aria-hidden />
          Sign out
        </button>
      </div>
    )
  }

  if (providers.length === 0) {
    return null
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs uppercase tracking-wider text-dbd-muted">Sign in with</span>
      {providers.map((provider) => (
        <a
          key={provider.id}
          href={signInUrl(provider.id, "/")}
          className="rounded-lg border border-dbd-border px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-dbd-text transition hover:border-dbd-purple/60 hover:bg-dbd-purple/10"
        >
          {provider.name}
        </a>
      ))}
    </div>
  )
}
