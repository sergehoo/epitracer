import type { MetadataRoute } from 'next';

const BASE = process.env.NEXT_PUBLIC_PUBLIC_HOST
  ? `https://${process.env.NEXT_PUBLIC_PUBLIC_HOST}`
  : 'http://localhost:3000';

/** Seul le contenu public d'information est indexable ; pass et suivi restent privés. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: ['/', '/maladies', '/assistance', '/voyageur'],
      disallow: ['/pass/', '/voyageur/suivi', '/voyageur/mes-donnees', '/api/', '/auth/'],
    },
    sitemap: `${BASE}/sitemap.xml`,
  };
}
