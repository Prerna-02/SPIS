'use client'

import Link from 'next/link'
import dynamic from 'next/dynamic'
import { useState, Suspense } from 'react'

// Dynamic import for 3D component (avoid SSR issues with Three.js)
const Port3D = dynamic(() => import('../components/Port3D'), {
    ssr: false,
    loading: () => (
        <div className="w-full h-full flex items-center justify-center bg-slate-800">
            <div className="text-white text-xl">Loading 3D Port...</div>
        </div>
    )
})

export default function MapPage() {
    const [activeTab, setActiveTab] = useState<'3d' | 'satellite'>('3d')

    // Port of Tallinn coordinates
    const TALLINN_LAT = 59.4370
    const TALLINN_LON = 24.7536

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

            {/* Gradient Overlay */}
            <div className="fixed inset-0 z-0 bg-gradient-to-b from-slate-900/70 via-slate-800/60 to-slate-900/80" />

            {/* Content */}
            <div className="relative z-10 min-h-screen flex flex-col">
                {/* Glassmorphic Header */}
                <header className="backdrop-blur-xl bg-slate-900/60 border-b border-white/20 sticky top-0 z-50">
                    <div className="max-w-7xl mx-auto px-6 py-4">
                        <div className="flex items-center justify-between">
                            {/* Logo */}
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-gradient-to-br from-sky-400 to-blue-600 rounded-xl flex items-center justify-center">
                                    <span className="text-white text-xl">⚓</span>
                                </div>
                                <div>
                                    <h1 className="text-xl font-bold text-white">SPIS</h1>
                                    <p className="text-xs text-sky-200">Smart Port Intelligence</p>
                                </div>
                            </div>

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
                                    className="px-4 py-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition"
                                >
                                    📋 Details
                                </Link>
                                <Link
                                    href="/map"
                                    className="px-4 py-2 bg-white/20 backdrop-blur rounded-lg text-white font-medium hover:bg-white/30 transition border border-white/20"
                                >
                                    🗺️ Map
                                </Link>
                            </nav>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 p-6">
                    {/* Page Title */}
                    <div className="text-center mb-4">
                        <h1 className="text-4xl font-bold text-white mb-2 drop-shadow-2xl">
                            Port of Tallinn - 3D Simulation
                        </h1>
                        <p className="text-sky-100 drop-shadow-lg">
                            Interactive 3D port visualization with vessel simulation
                        </p>
                    </div>

                    {/* Tab Navigation */}
                    <div className="flex justify-center gap-4 mb-4">
                        <button
                            onClick={() => setActiveTab('3d')}
                            className={`px-6 py-3 rounded-lg font-medium transition ${activeTab === '3d'
                                    ? 'bg-sky-500 text-white shadow-lg'
                                    : 'bg-slate-800/60 text-white/70 hover:bg-slate-700/60'
                                }`}
                        >
                            🎮 3D Simulation
                        </button>
                        <button
                            onClick={() => setActiveTab('satellite')}
                            className={`px-6 py-3 rounded-lg font-medium transition ${activeTab === 'satellite'
                                    ? 'bg-sky-500 text-white shadow-lg'
                                    : 'bg-slate-800/60 text-white/70 hover:bg-slate-700/60'
                                }`}
                        >
                            🛰️ Satellite View
                        </button>
                    </div>

                    {/* Map Container */}
                    <div className="backdrop-blur-2xl bg-slate-800/40 border border-white/30 rounded-2xl overflow-hidden shadow-2xl">
                        {activeTab === '3d' ? (
                            <>
                                {/* 3D Simulation Info Bar */}
                                <div className="backdrop-blur bg-slate-900/60 px-6 py-3 border-b border-white/20 flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <span className="text-2xl">🎮</span>
                                        <div>
                                            <p className="font-bold text-white">3D Port Simulation</p>
                                            <p className="text-sm text-sky-200">Click and drag to rotate • Scroll to zoom • Use controls to simulate</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 text-sm text-white/70">
                                        <span className="px-2 py-1 bg-green-500/30 rounded text-green-300">Interactive</span>
                                        <span className="px-2 py-1 bg-sky-500/30 rounded text-sky-300">Real-time</span>
                                    </div>
                                </div>

                                {/* 3D Canvas */}
                                <div style={{ height: 'calc(100vh - 350px)' }}>
                                    <Suspense fallback={
                                        <div className="w-full h-full flex items-center justify-center bg-slate-800">
                                            <div className="text-white text-xl">Loading 3D Port...</div>
                                        </div>
                                    }>
                                        <Port3D />
                                    </Suspense>
                                </div>
                            </>
                        ) : (
                            <>
                                {/* Location Bar for Satellite */}
                                <div className="backdrop-blur bg-slate-900/60 px-6 py-3 border-b border-white/20 flex items-center justify-between">
                                    <div className="flex items-center gap-4">
                                        <span className="text-2xl">📍</span>
                                        <div>
                                            <p className="font-bold text-white">Port of Tallinn, Estonia</p>
                                            <p className="text-sm text-sky-200">Lat: {TALLINN_LAT}° N | Lon: {TALLINN_LON}° E</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <a
                                            href={`https://www.google.com/maps/@${TALLINN_LAT},${TALLINN_LON},15z/data=!3m1!1e3`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="px-4 py-2 bg-blue-500/30 backdrop-blur rounded-lg text-white hover:bg-blue-500/50 transition border border-blue-400/30"
                                        >
                                            Open in Google Maps
                                        </a>
                                    </div>
                                </div>

                                {/* Google Maps Embed */}
                                <div style={{ height: 'calc(100vh - 350px)' }}>
                                    <iframe
                                        src={`https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d16000!2d${TALLINN_LON}!3d${TALLINN_LAT}!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x46929499df5616bf%3A0x6c60c88d6c3d6e4e!2sPort%20of%20Tallinn!5e1!4m2!3e0!4v1700000000000!5m2!1sen!2see`}
                                        width="100%"
                                        height="100%"
                                        style={{ border: 0 }}
                                        allowFullScreen
                                        loading="lazy"
                                        referrerPolicy="no-referrer-when-downgrade"
                                        className="w-full h-full"
                                    />
                                </div>
                            </>
                        )}
                    </div>

                    {/* Terminal Legend */}
                    <div className="backdrop-blur-2xl bg-slate-800/40 border border-white/30 rounded-2xl p-6 mt-6 shadow-2xl">
                        <h2 className="text-xl font-bold text-white mb-4">Port Terminals & Berths</h2>
                        <div className="grid md:grid-cols-4 gap-4">
                            <div className="flex items-center gap-3">
                                <div className="w-4 h-4 rounded-full bg-blue-500"></div>
                                <span className="text-white/90">Old City Terminal (B1-B2)</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="w-4 h-4 rounded-full bg-green-500"></div>
                                <span className="text-white/90">Muuga Container Terminal (B3-B4)</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="w-4 h-4 rounded-full bg-yellow-500"></div>
                                <span className="text-white/90">Container Yard Blocks (Y1-Y3)</span>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="w-4 h-4 rounded-full bg-purple-500"></div>
                                <span className="text-white/90">Gantry Cranes (6 units)</span>
                            </div>
                        </div>
                    </div>
                </main>

                {/* Footer */}
                <footer className="backdrop-blur-xl bg-slate-900/60 border-t border-white/10">
                    <div className="max-w-7xl mx-auto px-6 py-6">
                        <div className="flex justify-between items-center">
                            <p className="text-sky-200">Port of Tallinn © 2026</p>
                            <p className="text-sky-200">SPIS v1.0 - 3D Simulation</p>
                        </div>
                    </div>
                </footer>
            </div>
        </div>
    )
}
