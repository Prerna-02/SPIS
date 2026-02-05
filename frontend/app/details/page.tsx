'use client'

import Link from 'next/link'

export default function DetailsPage() {
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

            {/* Sky Blue Gradient Overlay - Slightly darker for better contrast */}
            <div className="fixed inset-0 z-0 bg-gradient-to-b from-sky-500/50 via-sky-600/40 to-sky-800/70" />

            {/* Content */}
            <div className="relative z-10 min-h-screen">
                {/* Glassmorphic Header */}
                <header className="backdrop-blur-xl bg-white/15 border-b border-white/20 sticky top-0 z-50">
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

                            {/* Navigation */}
                            <nav className="flex items-center gap-6">
                                <Link
                                    href="/"
                                    className="px-4 py-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition"
                                >
                                    🏠 Home
                                </Link>
                                <Link
                                    href="/details"
                                    className="px-4 py-2 bg-white/20 backdrop-blur rounded-lg text-white font-medium hover:bg-white/30 transition border border-white/20"
                                >
                                    📋 Details
                                </Link>
                                <Link
                                    href="/map"
                                    className="px-4 py-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition"
                                >
                                    🗺️ Map
                                </Link>
                            </nav>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="max-w-7xl mx-auto px-6 py-12">
                    {/* Page Title */}
                    <div className="text-center mb-12">
                        <h1 className="text-5xl font-bold text-white mb-4 drop-shadow-2xl">
                            About Port of Tallinn
                        </h1>
                        <p className="text-xl text-white drop-shadow-lg">
                            Estonia&apos;s Gateway to the Baltic Sea
                        </p>
                    </div>

                    {/* Company Overview - More opaque background for better readability */}
                    <div className="backdrop-blur-2xl bg-slate-800/70 border border-white/20 rounded-2xl p-8 mb-8 shadow-2xl">
                        <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
                            <span className="text-3xl">🏢</span> Company Overview
                        </h2>
                        <div className="grid md:grid-cols-2 gap-8">
                            <div>
                                <p className="text-white leading-relaxed mb-4">
                                    Port of Tallinn is the largest port complex in Estonia and one of the busiest
                                    in the Baltic Sea region. As a major hub for both cargo and passenger traffic,
                                    we connect Estonia to over 40 countries worldwide.
                                </p>
                                <p className="text-white leading-relaxed">
                                    Our Smart Port Intelligence System (SPIS) represents our commitment to
                                    innovation, using cutting-edge AI and machine learning to optimize operations
                                    and deliver world-class service.
                                </p>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="backdrop-blur bg-sky-600/30 rounded-xl p-4 text-center border border-sky-400/30">
                                    <p className="text-3xl font-bold text-white">1991</p>
                                    <p className="text-sm text-sky-100">Established</p>
                                </div>
                                <div className="backdrop-blur bg-sky-600/30 rounded-xl p-4 text-center border border-sky-400/30">
                                    <p className="text-3xl font-bold text-white">4</p>
                                    <p className="text-sm text-sky-100">Terminals</p>
                                </div>
                                <div className="backdrop-blur bg-sky-600/30 rounded-xl p-4 text-center border border-sky-400/30">
                                    <p className="text-3xl font-bold text-white">10M+</p>
                                    <p className="text-sm text-sky-100">Passengers/Year</p>
                                </div>
                                <div className="backdrop-blur bg-sky-600/30 rounded-xl p-4 text-center border border-sky-400/30">
                                    <p className="text-3xl font-bold text-white">25M</p>
                                    <p className="text-sm text-sky-100">Tons Cargo/Year</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Terminals - More opaque background */}
                    <div className="backdrop-blur-2xl bg-slate-800/70 border border-white/20 rounded-2xl p-8 mb-8 shadow-2xl">
                        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                            <span className="text-3xl">🚢</span> Our Terminals
                        </h2>
                        <div className="grid md:grid-cols-2 gap-6">
                            <div className="backdrop-blur bg-slate-700/60 rounded-xl p-6 border border-white/10">
                                <h3 className="text-xl font-bold text-white mb-2">Old City Harbor</h3>
                                <p className="text-sky-200 text-sm mb-3">Passenger Terminal</p>
                                <p className="text-white">
                                    The heart of Tallinn&apos;s cruise and ferry operations, located in the
                                    historic Old Town. Handles over 9 million passengers annually.
                                </p>
                            </div>
                            <div className="backdrop-blur bg-slate-700/60 rounded-xl p-6 border border-white/10">
                                <h3 className="text-xl font-bold text-white mb-2">Muuga Harbor</h3>
                                <p className="text-sky-200 text-sm mb-3">Container & Cargo Terminal</p>
                                <p className="text-white">
                                    Estonia&apos;s largest cargo terminal with modern container handling
                                    facilities and direct rail connections to Russia and Central Asia.
                                </p>
                            </div>
                            <div className="backdrop-blur bg-slate-700/60 rounded-xl p-6 border border-white/10">
                                <h3 className="text-xl font-bold text-white mb-2">Paldiski South Harbor</h3>
                                <p className="text-sky-200 text-sm mb-3">Ro-Ro Terminal</p>
                                <p className="text-white">
                                    Specialized in roll-on/roll-off cargo with regular ferry connections
                                    to Sweden and Finland.
                                </p>
                            </div>
                            <div className="backdrop-blur bg-slate-700/60 rounded-xl p-6 border border-white/10">
                                <h3 className="text-xl font-bold text-white mb-2">Saaremaa Harbor</h3>
                                <p className="text-sky-200 text-sm mb-3">Island Connection</p>
                                <p className="text-white">
                                    Essential ferry link to Estonia&apos;s largest island, serving both
                                    local residents and tourists.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* SPIS Features - More opaque background */}
                    <div className="backdrop-blur-2xl bg-slate-800/70 border border-white/20 rounded-2xl p-8 shadow-2xl">
                        <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                            <span className="text-3xl">🤖</span> SPIS Technology Stack
                        </h2>
                        <div className="grid md:grid-cols-4 gap-4">
                            <div className="backdrop-blur bg-blue-600/40 rounded-xl p-4 text-center border border-blue-400/40">
                                <p className="text-4xl mb-2">📊</p>
                                <p className="font-bold text-white">Forecasting</p>
                                <p className="text-sm text-blue-100">TCN + LightGBM</p>
                            </div>
                            <div className="backdrop-blur bg-red-600/40 rounded-xl p-4 text-center border border-red-400/40">
                                <p className="text-4xl mb-2">🚨</p>
                                <p className="font-bold text-white">Anomaly</p>
                                <p className="text-sm text-red-100">Autoencoder</p>
                            </div>
                            <div className="backdrop-blur bg-yellow-600/40 rounded-xl p-4 text-center border border-yellow-400/40">
                                <p className="text-4xl mb-2">🔧</p>
                                <p className="font-bold text-white">Maintenance</p>
                                <p className="text-sm text-yellow-100">BiLSTM</p>
                            </div>
                            <div className="backdrop-blur bg-green-600/40 rounded-xl p-4 text-center border border-green-400/40">
                                <p className="text-4xl mb-2">🗺️</p>
                                <p className="font-bold text-white">Optimization</p>
                                <p className="text-sm text-green-100">Neo4j + CP-SAT</p>
                            </div>
                        </div>
                    </div>
                </main>

                {/* Footer */}
                <footer className="backdrop-blur-xl bg-slate-900/50 border-t border-white/10 mt-12">
                    <div className="max-w-7xl mx-auto px-6 py-6">
                        <div className="flex justify-between items-center">
                            <p className="text-white">Port of Tallinn © 2026</p>
                            <p className="text-white">SPIS v1.0</p>
                        </div>
                    </div>
                </footer>
            </div>
        </div>
    )
}
