const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000';

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      // The browser calls /api/... and Next proxies to the agent's API, which
      // serves its routes at the root (/agent, /market, /trades, /backtest).
      { source: '/api/:path*', destination: `${BACKEND_URL}/:path*` },
    ];
  },
};

export default nextConfig;
