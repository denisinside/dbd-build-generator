const WIKI_URL = "https://deadbydaylight.wiki.gg"
const LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"

export function Footer() {
  return (
    <footer className="border-t border-dbd-border/60 px-4 py-8 text-center">
      <p className="text-xs uppercase tracking-[0.2em] text-dbd-muted/70">
        DBD Build Generator
      </p>

      <p className="mx-auto mt-4 max-w-2xl text-xs leading-relaxed text-dbd-muted/70">
        Perk, add-on and character data and icons come from the{" "}
        <a
          href={WIKI_URL}
          target="_blank"
          rel="noreferrer noopener"
          className="underline decoration-dotted hover:text-dbd-text"
        >
          Dead by Daylight Wiki
        </a>{" "}
        and are used under{" "}
        <a
          href={LICENSE_URL}
          target="_blank"
          rel="noreferrer noopener"
          className="underline decoration-dotted hover:text-dbd-text"
        >
          CC BY-SA 4.0
        </a>
        .
      </p>

      <p className="mx-auto mt-2 max-w-2xl text-xs leading-relaxed text-dbd-muted/60">
        Dead by Daylight is a trademark of Behaviour Interactive Inc. This is an
        unofficial fan project and is not affiliated with, endorsed by, or
        sponsored by Behaviour Interactive. Generated builds are AI suggestions,
        not official advice.
      </p>
    </footer>
  )
}
