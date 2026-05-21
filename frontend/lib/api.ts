/**
 * Client API EpidemiTracker (axios) — intercepteurs JWT, timeouts, gestion erreurs.
 */
import axios, { AxiosError, AxiosInstance } from 'axios';

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,
});

const ACCESS_KEY = 'epi_access';
const REFRESH_KEY = 'epi_refresh';

export function setTokens(access: string, refresh: string) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}
export function clearTokens() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}
export function getAccess() {
  return typeof window === 'undefined' ? null : localStorage.getItem(ACCESS_KEY);
}
export function getRefresh() {
  return typeof window === 'undefined' ? null : localStorage.getItem(REFRESH_KEY);
}

api.interceptors.request.use((cfg) => {
  const token = getAccess();
  if (token) cfg.headers.Authorization = `Bearer ${token}`;

  // Si le body est un FormData, on supprime le Content-Type par défaut
  // ("application/json") pour laisser le navigateur ajouter automatiquement
  // "multipart/form-data; boundary=...". Sans cela, le parser DRF ne sait
  // pas découper le body, Django renvoie une redirection que le navigateur
  // suit en GET → 405 sur l'endpoint POST-only.
  if (typeof FormData !== 'undefined' && cfg.data instanceof FormData) {
    if (cfg.headers && 'Content-Type' in cfg.headers) {
      delete (cfg.headers as Record<string, unknown>)['Content-Type'];
    }
  }

  return cfg;
});

let refreshing: Promise<string | null> | null = null;
async function refreshAccess(): Promise<string | null> {
  const refresh = getRefresh();
  if (!refresh) return null;
  try {
    const { data } = await axios.post(`${API_URL}/api/v1/auth/refresh/`, { refresh });
    setTokens(data.access, refresh);
    return data.access as string;
  } catch {
    clearTokens();
    return null;
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original: any = error.config;
    if (error.response?.status === 401 && !original?._retry) {
      original._retry = true;
      refreshing = refreshing || refreshAccess();
      const newToken = await refreshing;
      refreshing = null;
      if (newToken) {
        original.headers = original.headers || {};
        original.headers.Authorization = `Bearer ${newToken}`;
        return api.request(original);
      }
    }
    return Promise.reject(error);
  },
);

/**
 * POST avec retry automatique sur erreur réseau / timeout / 5xx transient.
 *
 * Utile pour les endpoints lourds (génération PDF, signature crypto) en
 * réseau mobile instable où la première tentative peut être coupée.
 *
 * - Retry uniquement sur : pas de réponse (ECONNABORTED, ERR_NETWORK)
 *   OU statut 502/503/504 OU timeout
 * - PAS de retry sur : 4xx (validation), 5xx applicatif (sauf gateway)
 * - Backoff exponentiel : 1s, 2s, 4s
 */
export async function apiPostWithRetry<T = unknown>(
  url: string,
  data: unknown,
  options: {
    retries?: number;
    timeoutMs?: number;
    onAttempt?: (n: number) => void;
  } = {},
): Promise<{ data: T }> {
  const retries = options.retries ?? 2;          // 1 essai + 2 retries
  const timeoutMs = options.timeoutMs ?? 90_000; // 90 s par défaut
  let lastError: unknown;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      options.onAttempt?.(attempt + 1);
      const r = await api.post<T>(url, data, { timeout: timeoutMs });
      return { data: r.data };
    } catch (err) {
      lastError = err;
      if (!axios.isAxiosError(err)) throw err;

      const status = err.response?.status;
      const code = err.code;
      const isNetworkErr = !err.response && (
        code === 'ECONNABORTED' || code === 'ERR_NETWORK' || code === 'ETIMEDOUT'
      );
      const isGatewayErr = status === 502 || status === 503 || status === 504;

      // Retry uniquement sur ces conditions, et tant qu'on a des essais
      if ((isNetworkErr || isGatewayErr) && attempt < retries) {
        const wait = 1000 * Math.pow(2, attempt); // 1s → 2s → 4s
        await new Promise((res) => setTimeout(res, wait));
        continue;
      }
      throw err;
    }
  }
  throw lastError;
}

/** Helper pour formater proprement les erreurs DRF. */
export function extractApiError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data: any = err.response?.data;
    if (typeof data === 'string') return data;
    if (data?.error?.message) return data.error.message;
    if (data?.detail) return String(data.detail);
    if (data?.error?.details) {
      const det = data.error.details;
      const first = Object.entries(det).find(([k]) => k !== 'detail');
      if (first) {
        const [k, v] = first;
        return Array.isArray(v) ? `${k}: ${v.join(' ')}` : `${k}: ${String(v)}`;
      }
    }
    return err.message;
  }
  return (err as Error)?.message || 'Erreur inconnue.';
}
