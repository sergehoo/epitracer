import type { MetadataRoute } from 'next';
import { fetchPublicDiseases } from '@/lib/portal';

export const revalidate = 3600;

const BASE = process.env.NEXT_PUBLIC_PUBLIC_HOST
  ? `https://${process.env.NEXT_PUBLIC_PUBLIC_HOST}`
  : 'http://localhost:3000';

/** Pages publiques indexables : accueil, informations et fiches maladies publiées. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const diseases = await fetchPublicDiseases();
  const now = new Date();
  return [
    { url: `${BASE}/`, lastModified: now, changeFrequency: 'daily', priority: 1 },
    { url: `${BASE}/maladies`, lastModified: now, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/voyageur`, lastModified: now, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE}/assistance`, lastModified: now, changeFrequency: 'monthly', priority: 0.7 },
    ...diseases.map((d) => ({
      url: `${BASE}/maladies/${d.slug}`,
      lastModified: new Date(d.updated_at),
      changeFrequency: 'weekly' as const,
      priority: 0.8,
    })),
  ];
}
