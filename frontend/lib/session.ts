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


const PENDING_PROMPT_KEY = "dbd-pending-prompt"


export interface PendingPrompt {
  prompt: string
  /** true: start generating on arrival. false: just refill the field. */
  autoRun: boolean
}


/**
 * Hand a prompt to the generator page across one navigation.
 *
 * Two callers, two intents: "Another variant" wants the run to start by
 * itself, while the sign-in gate only wants the field refilled once the
 * visitor comes back from the provider.
 *
 * sessionStorage, not the URL: a `?prompt=...` link that auto-starts would
 * let anyone post a link that spends money on every viewer who opens it, and
 * there is no global budget cap to stop that. A tab-local handoff cannot be
 * shared, so only a real click starts a run. It also survives the full page
 * navigation the OAuth handshake makes, which React state would not.
 */
export function setPendingPrompt(prompt: string, autoRun: boolean) {
  try {
    window.sessionStorage.setItem(
      PENDING_PROMPT_KEY,
      JSON.stringify({ prompt, autoRun } satisfies PendingPrompt),
    )
  } catch {
    // Falls back to an empty generator page, which is still usable.
  }
}


/** Read and consume the handed-over prompt. Null when there is none. */
export function takePendingPrompt(): PendingPrompt | null {
  if (typeof window === "undefined") {
    return null
  }

  try {
    const stored = window.sessionStorage.getItem(PENDING_PROMPT_KEY)
    window.sessionStorage.removeItem(PENDING_PROMPT_KEY)

    if (!stored) {
      return null
    }

    const pending = JSON.parse(stored) as PendingPrompt

    return pending.prompt ? pending : null
  } catch {
    return null
  }
}


const PENDING_JOB_KEY = "dbd-pending-job"


/**
 * The generation this browser is waiting on.
 *
 * localStorage rather than sessionStorage or React state: the whole point is
 * to survive a phone locking the tab away or the browser being closed, which
 * is exactly when the progress stream dies while the build keeps running on
 * the server.
 */
export function setPendingJob(jobId: string) {
  write(PENDING_JOB_KEY, jobId)
}


export function getPendingJob(): string {
  return read(PENDING_JOB_KEY)
}


export function clearPendingJob() {
  write(PENDING_JOB_KEY, "")
}
