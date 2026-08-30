/**
 * Browser-local identity. No network, no imports, so both the API client and
 * the UI can read it without a circular dependency.
 *
 * Two separate things live here:
 *
 * - the anonymous token, minted per browser, which decides which builds an
 *   unauthenticated visitor calls "mine";
 * - the session token from signing in, which is what the API actually trusts.
 *
 * Both return "" when storage is unavailable (private mode, blocked site
 * data). Generating a build still works without either; the visitor just does
 * not get a personal list.
 */

const ANONYMOUS_KEY = "dbd-session-id"
const AUTH_KEY = "dbd-auth-token"


function read(key: string): string {
  if (typeof window === "undefined") {
    return ""
  }

  try {
    return window.localStorage.getItem(key) ?? ""
  } catch {
    return ""
  }
}


function write(key: string, value: string) {
  if (typeof window === "undefined") {
    return
  }

  try {
    if (value) {
      window.localStorage.setItem(key, value)
    } else {
      window.localStorage.removeItem(key)
    }
  } catch {
    // Nothing to do: the visitor simply has no persistent identity.
  }
}


/** Anonymous owner token. Not a credential — it only groups a browser's builds. */
export function getSessionId(): string {
  const existing = read(ANONYMOUS_KEY)

  if (existing) {
    return existing
  }

  if (typeof window === "undefined") {
    return ""
  }

  const created = crypto.randomUUID()
  write(ANONYMOUS_KEY, created)

  return created
}


/** Bearer token from signing in. This one the API verifies. */
export function getAuthToken(): string {
  return read(AUTH_KEY)
}


export function setAuthToken(token: string) {
  write(AUTH_KEY, token)
}


export function clearAuthToken() {
  write(AUTH_KEY, "")
}
