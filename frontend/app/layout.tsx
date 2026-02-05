import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
    title: 'SPIS - Smart Port Intelligence System',
    description: 'Port of Tallinn - AI-Powered Operations Dashboard',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body className="min-h-screen">
                {children}
            </body>
        </html>
    )
}
