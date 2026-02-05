'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import WebcamCapture from '../components/WebcamCapture'

export default function LoginPage() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [faceImage, setFaceImage] = useState<string | null>(null)
    const [showFaceVerify, setShowFaceVerify] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [showWelcomeBack, setShowWelcomeBack] = useState(false)

    // Check if user just logged out
    useEffect(() => {
        if (searchParams.get('logout') === 'success') {
            setShowWelcomeBack(true)
            // Remove the query param from URL without reload
            window.history.replaceState({}, '', '/login')
        }
    }, [searchParams])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)

        if (!username || !password) {
            setError('Username and password are required')
            return
        }

        setLoading(true)

        try {
            const res = await fetch('http://localhost:8004/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    username,
                    password,
                    face_image: faceImage
                })
            })

            if (!res.ok) {
                const data = await res.json()
                throw new Error(data.detail || 'Login failed')
            }

            const data = await res.json()
            console.log('Login successful:', data)

            // Redirect to dashboard
            router.push('/')
            router.refresh()

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed')
        } finally {
            setLoading(false)
        }
    }

    const handleFaceCapture = (imageBase64: string) => {
        setFaceImage(imageBase64)
        setShowFaceVerify(false)
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-white mb-2">🚢 SPIS</h1>
                    <p className="text-purple-300">Smart Port Intelligence System</p>
                </div>

                {/* Welcome Back Message */}
                {showWelcomeBack && (
                    <div className="bg-gradient-to-r from-purple-900/60 to-blue-900/60 backdrop-blur-lg border border-purple-500/30 rounded-2xl p-6 mb-6 text-center relative overflow-hidden">
                        <div className="absolute inset-0 bg-gradient-to-r from-purple-500/10 to-blue-500/10 animate-pulse" />
                        <div className="relative">
                            <span className="text-4xl mb-2 block">👋</span>
                            <h3 className="text-xl font-bold text-white mb-2">Hope You Enjoyed Your Session!</h3>
                            <p className="text-purple-200 text-sm">
                                Thank you for using SPIS. We look forward to seeing you again soon!
                            </p>
                            <p className="text-purple-300 text-xs mt-2">
                                🚢 Safe voyages ahead!
                            </p>
                        </div>
                        <button 
                            onClick={() => setShowWelcomeBack(false)}
                            className="absolute top-2 right-2 text-purple-300 hover:text-white"
                        >
                            ✕
                        </button>
                    </div>
                )}

                {/* Login Card */}
                <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700 rounded-2xl p-8">
                    <h2 className="text-2xl font-bold text-white mb-6 text-center">Sign In</h2>

                    {error && (
                        <div className="bg-red-900/50 border border-red-500 rounded-lg p-3 text-red-300 text-sm mb-4">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm text-gray-400 mb-2">Username</label>
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="w-full px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                                placeholder="Enter username"
                            />
                        </div>

                        <div>
                            <label className="block text-sm text-gray-400 mb-2">Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                                placeholder="Enter password"
                            />
                        </div>

                        {/* Face Verification (Optional) */}
                        <div className="border-t border-slate-700 pt-4 mt-4">
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-sm text-gray-400">Face Verification (Optional)</span>
                                {faceImage && (
                                    <span className="text-xs text-green-400">✓ Ready</span>
                                )}
                            </div>

                            {!showFaceVerify && !faceImage && (
                                <button
                                    type="button"
                                    onClick={() => setShowFaceVerify(true)}
                                    className="w-full py-2 px-4 bg-slate-700 hover:bg-slate-600 text-gray-300 rounded-lg text-sm transition-colors"
                                >
                                    📷 Add Face Verification
                                </button>
                            )}

                            {showFaceVerify && (
                                <WebcamCapture
                                    onCapture={handleFaceCapture}
                                    buttonLabel="Capture for Verification"
                                />
                            )}

                            {faceImage && (
                                <div className="flex gap-2">
                                    <div className="flex-1 text-center py-2 bg-purple-900/30 border border-purple-700 rounded-lg text-purple-300 text-sm">
                                        Face captured for verification
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => setFaceImage(null)}
                                        className="py-2 px-3 bg-slate-700 hover:bg-slate-600 text-gray-300 rounded-lg text-sm"
                                    >
                                        ✕
                                    </button>
                                </div>
                            )}

                            <p className="text-xs text-gray-500 mt-2">
                                Face verification adds an extra layer of security if you enrolled your face during registration.
                            </p>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-3 px-4 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                        >
                            {loading ? 'Signing In...' : 'Sign In'}
                        </button>
                    </form>

                    <p className="text-center text-gray-400 mt-6">
                        Don't have an account?{' '}
                        <Link href="/register" className="text-purple-400 hover:text-purple-300">
                            Register
                        </Link>
                    </p>
                </div>

                {/* Demo Info */}
                <div className="mt-6 p-4 bg-slate-800/30 border border-slate-700 rounded-lg">
                    <p className="text-sm text-gray-400 text-center">
                        <strong className="text-purple-300">Demo:</strong> Register a new user or use existing credentials.
                        Face verification is optional.
                    </p>
                </div>
            </div>
        </div>
    )
}
