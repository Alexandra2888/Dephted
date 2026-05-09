import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  typedRoutes: true,
  async redirects() {
    return [{ source: "/", destination: "/dashboard", permanent: false }]
  },
}

export default nextConfig
