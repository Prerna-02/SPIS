'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import WebcamCapture from '../components/WebcamCapture'

export default function RegisterPage() {
    const router = useRouter()
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [faceImage, setFaceImage] = useState<string | null>(null)
    const [showFaceCapture, setShowFaceCapture] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError(null)

        // Validation
        if (!username || !password) {
            setError('Username and password are required')
            return
        }
        if (password !== confirmPassword) {
            setError('Passwords do not match')
            return
        }
        if (password.length < 6) {
            setError('Password must be at least 6 characters')
            return
        }

        setLoading(true)

        try {
            // Register user
            const res = await fetch('http://localhost:8004/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })

            if (!res.ok) {
                const data = await res.json()
                throw new Error(data.detail || 'Registration failed')
            }

            // If face was captured, enroll it after login
            if (faceImage) {
                // First login to get session
                const loginRes = await fetch('http://localhost:8004/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ username, password })
                })

                if (loginRes.ok) {
                    // Enroll face
                    await fetch('http://localhost:8004/auth/face/enroll', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({ face_image: faceImage })
                    })
                }
            }

            setSuccess(true)
            setTimeout(() => {
                router.push('/login')
            }, 2000)

        } catch (err) {
            setError(err instanceof Error ? err.message : 'Registration failed')
        } finally {
            setLoading(false)
        }
    }

    const handleFaceCapture = (imageBase64: string) => {
        setFaceImage(imageBase64)
        setShowFaceCapture(false)
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-white mb-2">🚢 SPIS</h1>
                    <p className="text-purple-300">Smart Port Intelligence System</p>
                </div>

                {/* Register Card */}
                <div className="bg-slate-800/50 backdrop-blur-lg border border-slate-700 rounded-2xl p-8">
                    <h2 className="text-2xl font-bold text-white mb-6 text-center">Create Account</h2>

                    {error && (
                        <div className="bg-red-900/50 border border-red-500 rounded-lg p-3 text-red-300 text-sm mb-4">
                            {error}
                        </div>
                    )}

                    {success && (
                        <div className="bg-green-900/50 border border-green-500 rounded-lg p-3 text-green-300 text-sm mb-4">
                            ✅ Account created! Redirecting to login...
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

                        <div>
                            <label className="block text-sm text-gray-400 mb-2">Confirm Password</label>
                            <input
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                                placeholder="Confirm password"
                            />
                        </div>

                        {/* Face Enrollment (Optional) */}
                        <div className="border-t border-slate-700 pt-4 mt-4">
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-sm text-gray-400">Face Login (Optional)</span>
                                {faceImage && (
                                    <span className="text-xs text-green-400">✓ Face captured</span>
                                )}
                            </div>

                            {!showFaceCapture && !faceImage && (
                                <button
                                    type="button"
                                    onClick={() => setShowFaceCapture(true)}
                                    className="w-full py-2 px-4 bg-slate-700 hover:bg-slate-600 text-gray-300 rounded-lg text-sm transition-colors"
                                >
                                    📷 Enable Face Login
                                </button>
                            )}

                            {showFaceCapture && (
                                <WebcamCapture
                                    onCapture={handleFaceCapture}
                                    buttonLabel="Capture Face"
                                />
                            )}

                            {faceImage && (
                                <div className="flex gap-2">
                                    <div className="flex-1 text-center py-2 bg-green-900/30 border border-green-700 rounded-lg text-green-300 text-sm">
                                        Face enrolled ✓
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setFaceImage(null)
                                            setShowFaceCapture(true)
                                        }}
                                        className="py-2 px-3 bg-slate-700 hover:bg-slate-600 text-gray-300 rounded-lg text-sm"
                                    >
                                        Retake
                                    </button>
                                </div>
                            )}
                        </div>

                        <button
                            type="submit"
                            disabled={loading || success}
                            className="w-full py-3 px-4 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
                        >
                            {loading ? 'Creating Account...' : 'Register'}
                        </button>
                    </form>

                    <p className="text-center text-gray-400 mt-6">
                        Already have an account?{' '}
                        <Link href="/login" className="text-purple-400 hover:text-purple-300">
                            Sign In
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
