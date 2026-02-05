'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'

export default function LogoutButton({ className = '' }: { className?: string }) {
    const router = useRouter()
    const [loading, setLoading] = useState(false)

    const handleLogout = async () => {
        setLoading(true)
        try {
            await fetch('http://localhost:8004/auth/logout', {
                method: 'POST',
                credentials: 'include'
            })
        } catch (err) {
            console.error('Logout error:', err)
        } finally {
            router.push('/login')
            router.refresh()
        }
    }

    return (
        <button
            onClick={handleLogout}
            disabled={loading}
            className={`px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${className}`}
        >
            {loading ? 'Logging out...' : '🚪 Logout'}
        </button>
    )
}
