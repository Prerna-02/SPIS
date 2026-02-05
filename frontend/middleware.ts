import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Routes that don't require authentication
const PUBLIC_ROUTES = ['/login', '/register']

// Cookie name must match backend
const AUTH_COOKIE = 'spis_auth_token'

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl

    // Allow public routes
    if (PUBLIC_ROUTES.some(route => pathname.startsWith(route))) {
        return NextResponse.next()
    }

    // Allow static assets and API routes
    if (
        pathname.startsWith('/_next') ||
        pathname.startsWith('/api') ||
        pathname.includes('.') // files with extensions (images, etc.)
    ) {
        return NextResponse.next()
    }

    // Check for auth cookie
    const token = request.cookies.get(AUTH_COOKIE)?.value

    if (!token) {
        // Redirect to login if not authenticated
        const loginUrl = new URL('/login', request.url)
        loginUrl.searchParams.set('redirect', pathname)
        return NextResponse.redirect(loginUrl)
    }

    // Token exists - allow request
    // Note: Full token validation happens on backend API calls
    return NextResponse.next()
}

export const config = {
    matcher: [
        /*
         * Match all request paths except:
         * - _next/static (static files)
         * - _next/image (image optimization)
         * - favicon.ico (favicon)
         */
        '/((?!_next/static|_next/image|favicon.ico).*)',
    ],
}
