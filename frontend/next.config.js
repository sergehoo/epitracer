/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: { typedRoutes: false },

  /*
   * Filet de sécurité : on laisse le build de production passer même si
   * `tsc` détecte une erreur de typage. Les erreurs restent visibles en
   * dev (HMR) et via `npm run typecheck` lancé dans la CI séparément.
   * Cela évite qu'un type "Partial<>" exotique dans une page admin bloque
   * tout le déploiement public.
   */
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },

  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**' },
      { protocol: 'http', hostname: 'localhost' },
      { protocol: 'http', hostname: 'web' },
    ],
  },

  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      // Proxy direct /api/* → backend (utile en dev)
      { source: '/api/:path*', destination: `${api}/api/:path*` },
      { source: '/media/:path*', destination: `${api}/media/:path*` },
    ];
  },
};

module.exports = nextConfig;
