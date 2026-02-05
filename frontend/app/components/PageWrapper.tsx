'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface PageWrapperProps {
    children: React.ReactNode
    title: string
    subtitle?: string
}

const navItems = [
    { href: '/', label: 'Home', icon: '🏠' },
    { href: '/details', label: 'Details', icon: '📋' },
    { href: '/map', label: 'Map', icon: '🗺️' },
]

const featureNavItems = [
    { href: '/forecasting', label: 'Forecasting', icon: '📊' },
    { href: '/anomaly', label: 'Anomaly', icon: '🚨' },
    { href: '/maintenance', label: 'Maintenance', icon: '🔧' },
    { href: '/optimization', label: 'Optimization', icon: '🗺️' },
]

export default function PageWrapper({ children, title, subtitle }: PageWrapperProps) {
    const pathname = usePathname()

    return (
        <div className="min-h-screen relative overflow-hidden">
            {/* Background Image */}
            <div
                className="fixed inset-0 z-0"
                style={{
                    backgroundImage: 'url("/port-background.jpg")',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat',
                }}
            />

            {/* Dark Gradient Overlay for better contrast */}
            <div className="fixed inset-0 z-0 bg-gradient-to-b from-slate-900/70 via-slate-800/60 to-slate-900/80" />

            {/* Content */}
            <div className="relative z-10 min-h-screen flex flex-col">
                {/* Glassmorphic Header - Dark */}
                <header className="backdrop-blur-xl bg-slate-900/60 border-b border-white/10 sticky top-0 z-50">
                    <div className="max-w-7xl mx-auto px-6 py-4">
                        <div className="flex items-center justify-between">
                            {/* Logo */}
                            <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition">
                                <div className="w-10 h-10 bg-gradient-to-br from-sky-400 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                                    <span className="text-white text-xl">⚓</span>
                                </div>
                                <div>
                                    <h1 className="text-xl font-bold text-white drop-shadow">SPIS</h1>
                                    <p className="text-xs text-sky-100">Smart Port Intelligence</p>
                                </div>
                            </Link>

                            {/* Main Navigation */}
                            <nav className="flex items-center gap-2">
                                {navItems.map((item) => {
                                    const isActive = pathname === item.href
                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${isActive
                                                ? 'bg-white/25 backdrop-blur text-white font-medium border border-white/30 shadow-lg'
                                                : 'text-white/80 hover:text-white hover:bg-white/10'
                                                }`}
                                        >
                                            <span>{item.icon}</span>
                                            {item.label}
                                        </Link>
                                    )
                                })}

                                {/* Separator */}
                                <div className="w-px h-6 bg-white/20 mx-2" />

                                {/* Feature Navigation */}
                                {featureNavItems.map((item) => {
                                    const isActive = pathname === item.href
                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={`px-3 py-2 rounded-lg transition flex items-center gap-2 text-sm ${isActive
                                                ? 'bg-sky-500/30 backdrop-blur text-white font-medium border border-sky-400/40 shadow'
                                                : 'text-white/70 hover:text-white hover:bg-white/10'
                                                }`}
                                        >
                                            <span>{item.icon}</span>
                                            {item.label}
                                        </Link>
                                    )
                                })}
                            </nav>

                            {/* Status indicator */}
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-400/50" />
                                <span className="text-sm text-white/80">Live</span>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Page Title */}
                <div className="text-center py-8">
                    <h1 className="text-4xl font-bold text-white drop-shadow-2xl mb-2">
                        {title}
                    </h1>
                    {subtitle && (
                        <p className="text-lg text-sky-100 drop-shadow-lg">
                            {subtitle}
                        </p>
                    )}
                </div>

                {/* Main content */}
                <main className="flex-1 max-w-7xl mx-auto px-6 pb-8 w-full">
                    {children}
                </main>

                {/* Footer */}
                <footer className="backdrop-blur-xl bg-slate-900/60 border-t border-white/10 mt-auto">
                    <div className="max-w-7xl mx-auto px-6 py-4">
                        <div className="flex justify-between items-center">
                            <p className="text-sky-100">Port of Tallinn © 2026</p>
                            <p className="text-sky-100">SPIS v1.0</p>
                        </div>
                    </div>
                </footer>
            </div>
        </div>
    )
}
