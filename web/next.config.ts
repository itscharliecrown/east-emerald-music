import type { NextConfig } from "next";

// Static export: deploys to Vercel as plain files and can also be served by the Modal API.
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
