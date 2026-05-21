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
