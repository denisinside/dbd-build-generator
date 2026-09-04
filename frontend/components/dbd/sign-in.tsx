"use client"

import { LogOut } from "lucide-react"
import { SmartImage } from "@/components/dbd/smart-image"
import { signInUrl, signOut, type AuthUser, type SignInProvider } from "@/lib/api"
import { clearAuthToken } from "@/lib/session"


interface ProviderButtonsProps {
  providers: SignInProvider[]
  /** Runs before the browser leaves for the provider, to stash any draft. */
  onBeforeSignIn?: () => void
}

/**
 * The provider links themselves.
 *
 * Plain anchors, because the OAuth handshake is a full page navigation to the
 * API and back — a client-side route change cannot start it. `onClick` still
 * fires first, which is what makes stashing a draft possible.
 */
export function ProviderButtons({ providers, onBeforeSignIn }: ProviderButtonsProps) {
  return (
    <>
      {providers.map((provider) => (
        <a
          key={provider.id}
          href={signInUrl(provider.id, "/")}
          onClick={onBeforeSignIn}
          className="rounded-lg border border-dbd-purple/40 bg-dbd-purple/10 px-4 py-2 text-sm font-semibold uppercase tracking-wider text-dbd-text transition hover:border-dbd-purple hover:bg-dbd-purple/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-dbd-purple"
        >
          {provider.name}
        </a>
      ))}
    </>
  )
}


interface SignInProps {
  user: AuthUser | null
  providers: SignInProvider[]
  onSignOut: () => void
  onBeforeSignIn?: () => void
}

/** Sign-in controls for the page header. */
export function SignIn({ user, providers, onSignOut, onBeforeSignIn }: SignInProps) {
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
            // Revoke the token server-side first: it still knows who it is
            // for this one request, and clearing it locally first would lose
            // that.
            void signOut().finally(() => {
              clearAuthToken()
              onSignOut()
            })
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
    // Said out loud rather than rendering nothing: an empty corner is
    // indistinguishable from a broken button, and the usual cause is simply
    // that AUTH_SECRET or a provider's credentials are missing.
    return (
      <p className="text-xs text-dbd-muted/70">
        Sign-in is not configured on this server.
      </p>
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs uppercase tracking-wider text-dbd-muted">Sign in with</span>
      <ProviderButtons providers={providers} onBeforeSignIn={onBeforeSignIn} />
    </div>
  )
}
