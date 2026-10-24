/** @type {import('next').NextConfig} */
const config = {
  devIndicators: false,
  // Local development only. Vercel Services owns public routing after deployment.
  async rewrites() {
    if (process.env.VERCEL) return [];
    const origin = process.env.XI_BACKEND_ORIGIN ?? "http://127.0.0.1:8000";
    return [{ source: "/api/v1/:path*", destination: `${origin}/api/v1/:path*` }];
  },
};
export default config;
