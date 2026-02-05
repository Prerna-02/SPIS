/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone',
    env: {
        FEATURE1_API: process.env.NEXT_PUBLIC_FEATURE1_API || 'http://localhost:8001',
        FEATURE2_API: process.env.NEXT_PUBLIC_FEATURE2_API || 'http://localhost:8002',
        FEATURE3_API: process.env.NEXT_PUBLIC_FEATURE3_API || 'http://localhost:8003',
        FEATURE4_API: process.env.NEXT_PUBLIC_FEATURE4_API || 'http://localhost:8000',
    },
}

module.exports = nextConfig
