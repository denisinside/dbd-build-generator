import { ImageResponse } from "next/og"
import { fetchBuild } from "@/lib/api"

export const size = { width: 1200, height: 630 }
export const contentType = "image/png"
export const alt = "Dead by Daylight build"

interface OpengraphImageProps {
  params: Promise<{ id: string }>
}

const BACKGROUND = "#100e18"
const PANEL = "#171423"
const BORDER = "#2b2440"
const PURPLE = "#a78bfa"
const TEXT = "#ece9f5"
const MUTED = "#9c94b3"

/**
 * Link preview card. Text only on purpose: embedding the wiki icons here would
 * make every preview render depend on an external host.
 */
export default async function OpengraphImage({ params }: OpengraphImageProps) {
  const { id } = await params

  let build = null

  try {
    build = await fetchBuild(id)
  } catch {
    build = null
  }

  const title = build?.build_title ?? "DBD Build Generator"
  const character = build?.character_name ?? "AI-generated Dead by Daylight builds"
  const role = build?.role ?? ""
  const score = build ? `${build.build_score}/10` : ""
  const perks = build?.perks.map((perk) => perk.name) ?? []

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: BACKGROUND,
          padding: 64,
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div
            style={{
              display: "flex",
              gap: 16,
              fontSize: 22,
              letterSpacing: 6,
              textTransform: "uppercase",
              color: PURPLE,
            }}
          >
            <span>Dead by Daylight</span>
            {role ? <span style={{ color: MUTED }}>· {role}</span> : null}
          </div>

          <div
            style={{
              fontSize: title.length > 48 ? 60 : 76,
              fontWeight: 700,
              lineHeight: 1.05,
              color: TEXT,
              textTransform: "uppercase",
            }}
          >
            {title}
          </div>

          <div style={{ fontSize: 34, color: MUTED }}>{character}</div>
        </div>

        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, maxWidth: 820 }}>
            {perks.map((perk) => (
              <div
                key={perk}
                style={{
                  display: "flex",
                  padding: "12px 20px",
                  borderRadius: 10,
                  border: `1px solid ${BORDER}`,
                  background: PANEL,
                  color: TEXT,
                  fontSize: 24,
                }}
              >
                {perk}
              </div>
            ))}
          </div>

          {score ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
              <span style={{ fontSize: 20, letterSpacing: 3, color: MUTED }}>SCORE</span>
              <span style={{ fontSize: 64, fontWeight: 700, color: PURPLE }}>{score}</span>
            </div>
          ) : null}
        </div>
      </div>
    ),
    size,
  )
}
