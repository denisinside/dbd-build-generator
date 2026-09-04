/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true,
  },
  async headers() {
    return [
      {
        // Mirrored wiki icons live in public/, and Next serves those with no
        // cache header at all — so reopening a build page refetches every
        // icon, and any hiccup on the way turns them into placeholders.
        source: "/media/:path*",
        headers: [{ key: "Cache-Control", value: "public, max-age=604800" }],
      },
    ]
  },
}

export default nextConfig
