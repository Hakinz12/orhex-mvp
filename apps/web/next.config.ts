import type { NextConfig } from "next";

const apiBaseUrl = process.env.ORHEX_API_BASE_URL?.replace(/\/+$/, "");

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    if (!apiBaseUrl) return [];
    const apiUrl = new URL(apiBaseUrl);
    if (apiUrl.username || apiUrl.password || apiUrl.search || apiUrl.hash) {
      throw new Error("ORHEX_API_BASE_URL must not contain credentials, query, or fragment.");
    }
    if (process.env.NODE_ENV === "production" && apiUrl.protocol !== "https:") {
      throw new Error("ORHEX_API_BASE_URL must use HTTPS in production.");
    }
    return [{ source: "/api/:path*", destination: `${apiUrl.origin}/:path*` }];
  },
};

export default nextConfig;
