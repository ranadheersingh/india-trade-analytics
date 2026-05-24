/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  // Proxy /api/v1/* → backend container so the browser never calls :8001
  // directly. Works from any IP/hostname — localhost, LAN, remote server.
  async rewrites() {
    const backendUrl = process.env.BACKEND_INTERNAL_URL || 'http://trade_backend:8000';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
