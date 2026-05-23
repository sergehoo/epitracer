'use client';

/**
 * Hook React qui se connecte au WebSocket `/ws/alerts/` (Django Channels)
 * et affiche un toast à chaque nouvelle alerte sanitaire reçue.
 *
 * Stratégie :
 * - URL : NEXT_PUBLIC_WS_URL (ex: wss://api.veillesanitaire.com) + /ws/alerts/
 * - Reconnexion automatique avec backoff exponentiel (1s → 30s max).
 * - Auth JWT envoyé en query string `?token=...` (lu depuis localStorage).
 * - Arrêt des reconnexions après MAX_ATTEMPTS échecs consécutifs pour
 *   éviter le spam de la console et la charge réseau.
 * - Code 4401 (auth refusée) : arrêt immédiat sans backoff.
 * - Graceful fallback : si le WS échoue, l'app fonctionne normalement.
 */

import { useEffect, useRef } from 'react';
import toast from 'react-hot-toast';
import { getAccess } from '@/lib/api';

interface AlertPayload {
  id: string;
  code: string;
  title: string;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | string;
  status: string;
  created_at: string;
}

interface AlertMessage {
  type: 'alert' | 'ready' | 'pong';
  data?: AlertPayload | unknown;
}

const SEV_ICON: Record<string, string> = {
  CRITICAL: '🚨',
  HIGH: '⚠️',
  MEDIUM: '🔔',
  LOW: 'ℹ️',
  INFO: 'ℹ️',
};

// Arrêt définitif des reconnexions après ce nombre d'échecs consécutifs.
// Évite le spam si Daphne est down ou Traefik mal configuré.
const MAX_ATTEMPTS = 6;

export function useRealtimeAlerts(options: { onAlert?: (a: AlertPayload) => void } = {}) {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const closedManuallyRef = useRef(false);
  const givenUpRef = useRef(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const wsBase = process.env.NEXT_PUBLIC_WS_URL || (
      window.location.protocol === 'https:'
        ? `wss://${window.location.host.replace(/^admin\./, 'api.')}`
        : `ws://${window.location.host.replace(/^admin\./, 'api.')}`
    );

    const connect = () => {
      if (givenUpRef.current || closedManuallyRef.current) return;
      if (attemptRef.current >= MAX_ATTEMPTS) {
        givenUpRef.current = true;
        // Log unique pour informer le dev sans bruit
        // eslint-disable-next-line no-console
        console.info(
          `[useRealtimeAlerts] Notifications temps réel désactivées après ${MAX_ATTEMPTS} tentatives. ` +
          'Rechargez la page pour réessayer.',
        );
        return;
      }

      const token = getAccess();
      if (!token) return; // pas d'auth → on n'essaie pas

      const url = `${wsBase}/ws/alerts/?token=${encodeURIComponent(token)}`;
      let ws: WebSocket;
      try {
        ws = new WebSocket(url);
      } catch {
        scheduleReconnect();
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => {
        attemptRef.current = 0;
        givenUpRef.current = false;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string) as AlertMessage;
          if (msg.type === 'alert' && msg.data) {
            const a = msg.data as AlertPayload;
            const icon = SEV_ICON[a.severity] || '🔔';
            toast(
              (t) => (
                // eslint-disable-next-line @next/next/no-html-link-for-pages
                <a
                  href="/alertes"
                  onClick={() => toast.dismiss(t.id)}
                  className="block min-w-[280px]"
                >
                  <div className="font-semibold">{icon} {a.title}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {a.severity} · cliquez pour ouvrir le centre d'alertes
                  </div>
                </a>
              ),
              { duration: a.severity === 'CRITICAL' ? 12_000 : 6_000 },
            );
            options.onAlert?.(a);
          }
        } catch {
          // payload invalide — ignore
        }
      };

      ws.onclose = (event) => {
        if (closedManuallyRef.current) return;
        // Code 4401 = auth refusée par JwtAuthMiddleware → inutile de réessayer
        if (event.code === 4401) {
          givenUpRef.current = true;
          // eslint-disable-next-line no-console
          console.info('[useRealtimeAlerts] Auth WebSocket refusée (token expiré ?). Notifications désactivées.');
          return;
        }
        scheduleReconnect();
      };

      ws.onerror = () => {
        // Pas de console.error ici — onclose se charge du backoff
        try { ws.close(); } catch {}
      };
    };

    const scheduleReconnect = () => {
      if (closedManuallyRef.current || givenUpRef.current) return;
      attemptRef.current += 1;
      // Backoff : 1s, 2s, 4s, 8s, 16s, 30s puis arrêt
      const delay = Math.min(30_000, 1000 * 2 ** Math.min(attemptRef.current, 5));
      reconnectTimerRef.current = window.setTimeout(connect, delay);
    };

    connect();

    return () => {
      closedManuallyRef.current = true;
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      try { wsRef.current?.close(); } catch {}
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
