const STORAGE_KEY = "dbd-session-id"

/**
 * Anonymous owner token, minted once per browser.
 *
 * Not a credential and not a login: it only decides which builds this browser
 * calls "mine" in the sidebar, until real accounts exist. Returns "" when
 * storage is unavailable (private mode, blocked site data) — generation still
 * works, the browser just does not get a personal list.
 */
export function getSessionId(): string {
  if (typeof window === "undefined") {
    return ""
  }

  try {
    const existing = window.localStorage.getItem(STORAGE_KEY)

    if (existing) {
      return existing
    }

    const created = crypto.randomUUID()
    window.localStorage.setItem(STORAGE_KEY, created)

    return created
  } catch {
    return ""
  }
}
