'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

// ============================================================
// TYPES
// ============================================================
interface WeatherData {
    temp: number
    condition: string
    icon: string
    humidity: number
    wind: number
}

// ============================================================
// QUOTES
// ============================================================
const MARITIME_QUOTES = [
    { quote: "The sea, once it casts its spell, holds one in its net of wonder forever.", author: "Jacques Cousteau" },
    { quote: "A ship in harbor is safe, but that is not what ships are built for.", author: "John A. Shedd" },
    { quote: "The ocean stirs the heart, inspires the imagination and brings eternal joy to the soul.", author: "Wyland" },
    { quote: "To reach a port we must sail, sometimes with the wind, and sometimes against it.", author: "Oliver Wendell Holmes" },
]

// ============================================================
// COMPONENT
// ============================================================
export default function Home() {
    const router = useRouter()
    const [weather, setWeather] = useState<WeatherData | null>(null)
    const [vesselCount, setVesselCount] = useState(27)
    const [currentTime, setCurrentTime] = useState('')
    // Use fixed quote initially, then randomly select on client to avoid hydration mismatch
    const [quote, setQuote] = useState(MARITIME_QUOTES[0])
    const [showLogoutModal, setShowLogoutModal] = useState(false)
    const [loggingOut, setLoggingOut] = useState(false)

    const handleLogout = async () => {
        setLoggingOut(true)
        try {
            await fetch('http://localhost:8004/auth/logout', {
                method: 'POST',
                credentials: 'include',
            })
            // Redirect to login with logout message
            router.push('/login?logout=success')
        } catch (err) {
            console.error('Logout error:', err)
            router.push('/login?logout=success')
        }
    }

    // Select random quote on client-side only to avoid hydration mismatch
    useEffect(() => {
        setQuote(MARITIME_QUOTES[Math.floor(Math.random() * MARITIME_QUOTES.length)])
    }, [])

    // Fetch weather for Tallinn
    useEffect(() => {
        const fetchWeather = async () => {
            try {
                // Using Open-Meteo API (free, no key required)
                // Tallinn coordinates: 59.4370, 24.7536
                const res = await fetch(
                    'https://api.open-meteo.com/v1/forecast?latitude=59.4370&longitude=24.7536&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m'
                )
                if (res.ok) {
                    const data = await res.json()
                    const current = data.current

                    // Map weather code to condition
                    const weatherCode = current.weather_code
                    let condition = 'Clear'
                    let icon = '☀️'

                    if (weatherCode >= 0 && weatherCode <= 3) { condition = 'Clear'; icon = '☀️' }
                    else if (weatherCode >= 45 && weatherCode <= 48) { condition = 'Foggy'; icon = '🌫️' }
                    else if (weatherCode >= 51 && weatherCode <= 67) { condition = 'Rainy'; icon = '🌧️' }
                    else if (weatherCode >= 71 && weatherCode <= 77) { condition = 'Snowy'; icon = '❄️' }
                    else if (weatherCode >= 80 && weatherCode <= 99) { condition = 'Stormy'; icon = '⛈️' }
                    else { condition = 'Cloudy'; icon = '☁️' }

                    setWeather({
                        temp: Math.round(current.temperature_2m),
                        condition,
                        icon,
                        humidity: current.relative_humidity_2m,
                        wind: Math.round(current.wind_speed_10m),
                    })
                }
            } catch (err) {
                console.error('Weather fetch error:', err)
                // Fallback weather
                setWeather({ temp: 2, condition: 'Clear', icon: '☀️', humidity: 75, wind: 12 })
            }
        }

        fetchWeather()

        // Update time
        const updateTime = () => {
            setCurrentTime(new Date().toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'Europe/Tallinn'
            }))
        }
        updateTime()
        const interval = setInterval(updateTime, 1000)

        return () => clearInterval(interval)
    }, [])

    // Fetch vessel count from API
    useEffect(() => {
        const fetchVessels = async () => {
            try {
                const res = await fetch('http://localhost:8000/kg/snapshot')
                if (res.ok) {
                    const data = await res.json()
                    setVesselCount(data.summary?.vessels_approaching + data.summary?.vessels_waiting + data.summary?.vessels_berthed || 27)
                }
            } catch (err) {
                console.error('Vessel count fetch error:', err)
            }
        }
        fetchVessels()
    }, [])

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

            {/* Dark Blue Gradient Overlay for better contrast */}
            <div className="fixed inset-0 z-0 bg-gradient-to-b from-slate-900/70 via-slate-800/60 to-slate-900/80" />

            {/* Content */}
            <div className="relative z-10 min-h-screen">
                {/* Glassmorphic Header - Darker */}
                <header className="backdrop-blur-xl bg-slate-900/60 border-b border-white/10 sticky top-0 z-50">
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
                                    className="px-4 py-2 bg-white/20 backdrop-blur rounded-lg text-white font-medium hover:bg-white/30 transition border border-white/20"
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
                                    className="px-4 py-2 text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition"
                                >
                                    🗺️ Map
                                </Link>
                                <button
                                    onClick={() => setShowLogoutModal(true)}
                                    className="px-4 py-2 text-red-300 hover:text-white hover:bg-red-500/30 rounded-lg transition border border-red-400/30"
                                >
                                    🚪 Logout
                                </button>
                            </nav>

                            {/* Time */}
                            <div className="text-right">
                                <p className="text-2xl font-bold text-white">{currentTime}</p>
                                <p className="text-xs text-sky-200">Tallinn, Estonia</p>
                            </div>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="max-w-7xl mx-auto px-6 py-12">
                    {/* Hero Section */}
                    <div className="text-center mb-12">
                        <h1 className="text-6xl font-bold text-white mb-4 drop-shadow-2xl">
                            Smart Port Intelligence System
                        </h1>
                        <p className="text-xl text-sky-100 drop-shadow-lg">
                            AI-Powered Operations Dashboard for Port of Tallinn
                        </p>
                    </div>

                    {/* Weather & Status Bar - Dark Glassmorphic */}
                    <div className="backdrop-blur-2xl bg-slate-800/70 border border-white/10 rounded-2xl p-6 mb-12 shadow-2xl">
                        <div className="grid grid-cols-3 gap-8">
                            {/* Port Status */}
                            <div className="flex items-center gap-4">
                                <div className="w-16 h-16 bg-gradient-to-br from-sky-400/50 to-blue-500/50 rounded-xl flex items-center justify-center backdrop-blur">
                                    <span className="text-4xl">⚓</span>
                                </div>
                                <div>
                                    <p className="text-sm text-sky-200">Port Status</p>
                                    <p className="text-2xl font-bold text-green-400">Active</p>
                                </div>
                            </div>

                            {/* Current Weather */}
                            <div className="flex items-center justify-center gap-4">
                                <div className="text-center">
                                    <p className="text-sm text-sky-200">Current Weather</p>
                                    <div className="flex items-center justify-center gap-3">
                                        <span className="text-5xl">{weather?.icon || '☀️'}</span>
                                        <div className="text-left">
                                            <p className="text-lg text-white">{weather?.condition || 'Loading...'}</p>
                                            <p className="text-3xl font-bold text-white">{weather?.temp || '--'}°C</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-4 mt-2 text-xs text-sky-200">
                                        <span>💧 {weather?.humidity || '--'}%</span>
                                        <span>💨 {weather?.wind || '--'} km/h</span>
                                    </div>
                                </div>
                            </div>

                            {/* Vessels in Port */}
                            <div className="flex items-center justify-end gap-4">
                                <div className="text-right">
                                    <p className="text-sm text-sky-200">Vessels in Port</p>
                                    <p className="text-3xl font-bold text-white">{vesselCount}</p>
                                    <p className="text-sm text-sky-200">Ships Docked</p>
                                </div>
                                <div className="w-16 h-16 bg-gradient-to-br from-sky-400/50 to-blue-500/50 rounded-xl flex items-center justify-center backdrop-blur">
                                    <span className="text-4xl">🚢</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Feature Cards Grid - Glassmorphic */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
                        {/* Feature 1 - Demand Forecasting */}
                        <Link href="/forecasting" className="group">
                            <div className="backdrop-blur-xl bg-slate-800/60 border border-white/10 rounded-2xl p-6 hover:bg-slate-700/70 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="w-14 h-14 bg-gradient-to-br from-blue-400 to-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                                        <span className="text-3xl">📊</span>
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-bold text-white">Demand Forecasting</h2>
                                        <p className="text-sm text-sky-200">Feature 1</p>
                                    </div>
                                </div>
                                <p className="text-white/80 mb-4">
                                    7-day port throughput predictions using TCN and LightGBM models.
                                </p>
                                <div className="flex gap-3 text-sm">
                                    <span className="px-3 py-1 bg-blue-500/30 backdrop-blur rounded-full text-blue-200 border border-blue-400/30">TCN</span>
                                    <span className="px-3 py-1 bg-blue-500/30 backdrop-blur rounded-full text-blue-200 border border-blue-400/30">LightGBM</span>
                                </div>
                            </div>
                        </Link>

                        {/* Feature 2 - Anomaly Detection */}
                        <Link href="/anomaly" className="group">
                            <div className="backdrop-blur-xl bg-slate-800/60 border border-white/10 rounded-2xl p-6 hover:bg-slate-700/70 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="w-14 h-14 bg-gradient-to-br from-red-400 to-red-600 rounded-xl flex items-center justify-center shadow-lg">
                                        <span className="text-3xl">🚨</span>
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-bold text-white">Anomaly Detection</h2>
                                        <p className="text-sm text-sky-200">Feature 2</p>
                                    </div>
                                </div>
                                <p className="text-white/80 mb-4">
                                    Real-time vessel behavior analysis using Autoencoder models.
                                </p>
                                <div className="flex gap-3 text-sm">
                                    <span className="px-3 py-1 bg-red-500/30 backdrop-blur rounded-full text-red-200 border border-red-400/30">Autoencoder</span>
                                    <span className="px-3 py-1 bg-red-500/30 backdrop-blur rounded-full text-red-200 border border-red-400/30">Redpanda</span>
                                </div>
                            </div>
                        </Link>

                        {/* Feature 3 - Smart Maintenance */}
                        <Link href="/maintenance" className="group">
                            <div className="backdrop-blur-xl bg-slate-800/60 border border-white/10 rounded-2xl p-6 hover:bg-slate-700/70 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="w-14 h-14 bg-gradient-to-br from-yellow-400 to-yellow-600 rounded-xl flex items-center justify-center shadow-lg">
                                        <span className="text-3xl">🔧</span>
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-bold text-white">Smart Maintenance</h2>
                                        <p className="text-sm text-sky-200">Feature 3</p>
                                    </div>
                                </div>
                                <p className="text-white/80 mb-4">
                                    Predictive equipment maintenance with RUL estimation.
                                </p>
                                <div className="flex gap-3 text-sm">
                                    <span className="px-3 py-1 bg-yellow-500/30 backdrop-blur rounded-full text-yellow-200 border border-yellow-400/30">BiLSTM</span>
                                    <span className="px-3 py-1 bg-yellow-500/30 backdrop-blur rounded-full text-yellow-200 border border-yellow-400/30">Multi-Task</span>
                                </div>
                            </div>
                        </Link>

                        {/* Feature 4 - KG + Optimization */}
                        <Link href="/optimization" className="group">
                            <div className="backdrop-blur-xl bg-slate-800/60 border border-white/10 rounded-2xl p-6 hover:bg-slate-700/70 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="w-14 h-14 bg-gradient-to-br from-green-400 to-green-600 rounded-xl flex items-center justify-center shadow-lg">
                                        <span className="text-3xl">🗺️</span>
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-bold text-white">KG + Optimization</h2>
                                        <p className="text-sm text-sky-200">Feature 4</p>
                                    </div>
                                </div>
                                <p className="text-white/80 mb-4">
                                    Real-time berth optimization with cascade impact analysis.
                                </p>
                                <div className="flex gap-3 text-sm">
                                    <span className="px-3 py-1 bg-green-500/30 backdrop-blur rounded-full text-green-200 border border-green-400/30">Neo4j</span>
                                    <span className="px-3 py-1 bg-green-500/30 backdrop-blur rounded-full text-green-200 border border-green-400/30">CP-SAT</span>
                                </div>
                            </div>
                        </Link>
                    </div>

                    {/* Maritime Quote - Dark Glassmorphic */}
                    <div className="backdrop-blur-2xl bg-slate-800/70 border border-white/10 rounded-2xl p-8 text-center">
                        <p className="text-2xl text-white italic mb-4 leading-relaxed">
                            &ldquo;{quote.quote}&rdquo;
                        </p>
                        <p className="text-sky-200">— {quote.author}</p>
                    </div>
                </main>

                {/* Footer */}
                <footer className="backdrop-blur-xl bg-slate-900/60 border-t border-white/10 mt-12">
                    <div className="max-w-7xl mx-auto px-6 py-6">
                        <div className="flex justify-between items-center">
                            <p className="text-sky-200">Port of Tallinn © 2026</p>
                            <p className="text-sky-200">SPIS v1.0</p>
                        </div>
                    </div>
                </footer>

                {/* Logout Confirmation Modal */}
                {showLogoutModal && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center">
                        {/* Backdrop */}
                        <div 
                            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                            onClick={() => setShowLogoutModal(false)}
                        />
                        
                        {/* Modal */}
                        <div className="relative bg-slate-800/95 backdrop-blur-xl border border-white/20 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl">
                            <div className="text-center">
                                <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <span className="text-4xl">👋</span>
                                </div>
                                <h3 className="text-2xl font-bold text-white mb-2">
                                    Leaving So Soon?
                                </h3>
                                <p className="text-gray-300 mb-6">
                                    Are you sure you want to logout from SPIS? We&apos;ll miss you!
                                </p>
                                
                                <div className="flex gap-4 justify-center">
                                    <button
                                        onClick={() => setShowLogoutModal(false)}
                                        className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg font-medium transition"
                                    >
                                        Stay Here
                                    </button>
                                    <button
                                        onClick={handleLogout}
                                        disabled={loggingOut}
                                        className="px-6 py-3 bg-red-600 hover:bg-red-700 disabled:bg-red-800 text-white rounded-lg font-medium transition"
                                    >
                                        {loggingOut ? 'Logging out...' : 'Yes, Logout'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
