/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Backend base URL, overridable per environment (local/dev/prod).
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000',
  },
};

module.exports = nextConfig;