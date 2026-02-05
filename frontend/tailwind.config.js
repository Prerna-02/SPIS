/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                // SPIS Dark Theme
                'spis-bg': '#0a1628',
                'spis-card': '#0f1f3d',
                'spis-border': '#1e3a5f',
                'spis-accent': '#3b82f6',
                'spis-success': '#10b981',
                'spis-warning': '#f59e0b',
                'spis-danger': '#ef4444',
            },
        },
    },
    plugins: [],
}
