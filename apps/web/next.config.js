/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/:path*',
      },
      // WebSocket upgrade proxy (dev only)
      {
        source: '/api/v1/ws/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/ws/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
