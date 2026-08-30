import Link from "next/link"

export default function BuildNotFound() {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,oklch(0.2_0.04_300/0.5),transparent_55%)]"
      />

      <h1 className="font-[family-name:var(--font-oswald)] text-3xl font-bold uppercase tracking-wide text-dbd-text">
        Build not found
      </h1>
      <p className="max-w-md text-sm leading-relaxed text-dbd-muted">
        This build link is invalid or the build no longer exists.
      </p>
      <Link
        href="/"
        className="mt-2 rounded-lg bg-dbd-purple px-5 py-3 font-[family-name:var(--font-oswald)] text-sm font-bold uppercase tracking-wider text-white transition hover:brightness-110"
      >
        Generate a new build
      </Link>
    </main>
  )
}
