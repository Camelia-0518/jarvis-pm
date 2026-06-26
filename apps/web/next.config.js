/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'dist',
  images: {
    unoptimized: true,
  },
  async rewrites() {
    // 开发环境：通过 rewrite 代理 API 请求到本地后端（避免 CORS）
    // 生产环境（Vercel）：前端直接通过 NEXT_PUBLIC_API_URL 访问后端，不使用 rewrite
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/v1/:path*',
          destination: 'http://127.0.0.1:8000/api/v1/:path*',
        },
        {
          source: '/api/v1/ws/:path*',
          destination: 'http://127.0.0.1:8000/api/v1/ws/:path*',
        },
      ];
    }
    return [];
  },
  trailingSlash: true,
};

module.exports = nextConfig;
