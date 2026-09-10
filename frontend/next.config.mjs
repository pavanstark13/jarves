/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Calls to /api/* are handled by the route handler in
  // src/app/api/[...path]/route.ts, which proxies to BACKEND_URL and attaches
  // the API token server-side. A rewrite cannot do that, so there isn't one.
};

export default nextConfig;
