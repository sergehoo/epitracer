/**
 * Middleware Next.js — séparation stricte des deux portails par hostname.
 *
 *   destinationci.com  → portail PUBLIC voyageurs (groupe (public))
 *                        + assets statiques + /api/* (proxy)
 *                        ⇒ toute autre route est redirigée vers l'hôte admin.
 *
 *   inhpadmin.ci       → portail ADMINISTRATIF (groupe (dashboard) + /auth)
 *                        ⇒ toute route publique est redirigée vers l'hôte public.
 *
 * Configuration via env :
 *   NEXT_PUBLIC_PUBLIC_HOST=destinationci.com
 *   NEXT_PUBLIC_ADMIN_HOST=inhpadmin.ci
 *
 * En dev local (localhost), aucune restriction n'est appliquée.
 */
import { NextRequest, NextResponse } from 'next/server';

const PUBLIC_PATHS = [
  '/',
  '/voyageur',
  '/pass',
  '/verifier',
  '/assistance',
];

const ADMIN_PATHS = [
  '/dashboard',
  '/surveillance',
  '/points-entree',
  '/districts',
  '/alertes',
  '/cartographie',
  '/maladies',
  '/formulaires',
  '/utilisateurs',
  '/auth',
];

const PASSTHROUGH = [
  '/_next', '/api', '/media', '/favicon', '/robots.txt', '/sitemap.xml',
  '/manifest.webmanifest', '/icons',
];

function isPublicPath(pathname: string) {
  return PUBLIC_PATHS.some((p) => p === pathname || pathname.startsWith(p + '/'));
}
function isAdminPath(pathname: string) {
  return ADMIN_PATHS.some((p) => p === pathname || pathname.startsWith(p + '/'));
}
function isPassthrough(pathname: string) {
  return PASSTHROUGH.some((p) => pathname.startsWith(p));
}

export function middleware(req: NextRequest) {
  const url = req.nextUrl.clone();
  const host = req.headers.get('host')?.split(':')[0]?.toLowerCase() || '';
  const path = url.pathname;

  // Dev / IPs internes : ne rien filtrer
  if (
    host === 'localhost' ||
    host.startsWith('127.') ||
    host.startsWith('10.') ||
    host.startsWith('192.168.') ||
    host === 'web' ||
    host === 'frontend' ||
    isPassthrough(path)
  ) {
    return NextResponse.next();
  }

  const publicHost = (process.env.NEXT_PUBLIC_PUBLIC_HOST || '').toLowerCase();
  const adminHost = (process.env.NEXT_PUBLIC_ADMIN_HOST || '').toLowerCase();
  if (!publicHost || !adminHost) {
    return NextResponse.next();
  }

  const protocol = req.headers.get('x-forwarded-proto') || 'https';

  // ===== Domaine public =====
  if (host === publicHost || host === `www.${publicHost}`) {
    if (isAdminPath(path)) {
      return NextResponse.redirect(`${protocol}://${adminHost}${path}${url.search}`, 308);
    }
    // /pass est public mais sa sous-route /pass/[id] aussi
    return NextResponse.next();
  }

  // ===== Domaine admin =====
  if (host === adminHost || host === `www.${adminHost}`) {
    // Racine admin → /dashboard
    if (path === '/') {
      url.pathname = '/dashboard';
      return NextResponse.redirect(url, 308);
    }
    if (isPublicPath(path) && !isAdminPath(path) && path !== '/') {
      return NextResponse.redirect(`${protocol}://${publicHost}${path}${url.search}`, 308);
    }
    return NextResponse.next();
  }

  // Host inconnu : laisser passer (peut être un check-up santé)
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api).*)'],
};
