import './globals.css'
import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
    title: 'Maritime Anomaly Detection',
    description: 'Real-time vessel anomaly detection for port security',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body>
                <nav className="navbar">
                    <div className="navbar-content">
                        <div className="logo">🚢 Maritime Anomaly Detection</div>
                        <div className="nav-links">
                            <Link href="/" className="nav-link">Dashboard</Link>
                            <Link href="/manual" className="nav-link">Manual Check</Link>
                        </div>
                    </div>
                </nav>
                {children}
            </body>
        </html>
    )
}
