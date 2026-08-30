import type { Metadata } from "next"
import { notFound } from "next/navigation"
import { BuildPage } from "@/components/dbd/build-page"
import { fetchBuild } from "@/lib/api"
import { adaptGeneratedBuild } from "@/lib/build-adapter"

interface BuildRouteProps {
  params: Promise<{ id: string }>
}

/**
 * Every generated build gets its own URL so it can be shared in chat, on
 * stream or on social media. The page is rendered on demand from the API.
 */
export default async function BuildRoute({ params }: BuildRouteProps) {
  const { id } = await params
  const build = await fetchBuild(id)

  if (build === null) {
    notFound()
  }

  return <BuildPage build={adaptGeneratedBuild(build)} backHref="/" />
}

export async function generateMetadata({ params }: BuildRouteProps): Promise<Metadata> {
  const { id } = await params

  let build = null

  try {
    build = await fetchBuild(id)
  } catch {
    // A metadata failure must not take the page down with it.
  }

  if (build === null) {
    return { title: "Build not found — DBD Build Generator" }
  }

  const title = `${build.build_title} — ${build.character_name}`
  const description =
    `${build.role} build for ${build.character_name}: ` +
    `${build.perks.map((perk) => perk.name).join(", ")}. ` +
    `Score ${build.build_score}/10.`

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "article",
      url: `/build/${id}`,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  }
}
