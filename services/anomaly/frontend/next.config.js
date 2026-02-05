/** @type {import('next').NextConfig} */
const nextConfig = {
    // Enable API calls to FastAPI backend
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://localhost:8002/:path*',
            },
        ];
    },
};

module.exports = nextConfig;
