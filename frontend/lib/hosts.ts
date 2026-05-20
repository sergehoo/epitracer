/**
 * Helpers pour construire les liens cross-domain entre le portail public
 * et le portail admin.
 *
 * Utilisé par les headers/footers pour pointer vers le bon hostname.
 * En dev local, on retombe sur des liens relatifs.
 */

export const PUBLIC_HOST = (process.env.NEXT_PUBLIC_PUBLIC_HOST || '').toLowerCase();
export const ADMIN_HOST = (process.env.NEXT_PUBLIC_ADMIN_HOST || '').toLowerCase();
export const PORTAL_NAME_PUBLIC = process.env.NEXT_PUBLIC_PORTAL_NAME_PUBLIC || 'EpiTravel';
export const PORTAL_NAME_ADMIN = process.env.NEXT_PUBLIC_PORTAL_NAME_ADMIN || 'EpiTravel — Admin INHP';

function makeUrl(host: string, path: string) {
  if (!host) return path;
  const proto = process.env.NODE_ENV === 'production' ? 'https' : 'http';
  const cleaned = path.startsWith('/') ? path : `/${path}`;
  return `${proto}://${host}${cleaned}`;
}

export function publicUrl(path: string) {
  return makeUrl(PUBLIC_HOST, path);
}
export function adminUrl(path: string) {
  return makeUrl(ADMIN_HOST, path);
}
