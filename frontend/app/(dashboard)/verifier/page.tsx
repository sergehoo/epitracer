'use client';

/**
 * Vérification de pass — version ADMIN avec mode hors-ligne.
 *
 * Stratégie :
 *   1. À chaque scan, on tente d'abord le serveur (vérif + état révoqué).
 *   2. Si offline ou erreur réseau → fallback sur vérif cryptographique
 *      locale (Ed25519 via @noble/ed25519, clé publique cachée).
 *
 * Visuel : badge En ligne / Hors ligne + bandeau d'avertissement quand
 * la vérification est uniquement locale (pas de check de révocation).
 */

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import {
  Camera, FileSearch, ShieldAlert, ShieldCheck, ShieldX,
  Wifi, WifiOff, RefreshCw,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { api, API_URL, extractApiError } from '@/lib/api';
import {
  loadPublicKey, hasPublicKeyCached, verifyTokenOffline, OfflineVerifyResult,
} from '@/lib/offlinePassVerify';

const Scanner = dynamic(
  () => import('@yudiel/react-qr-scanner').then((m) => m.Scanner),
  { ssr: false },
);

type VerifyResult = {
  is_valid: boolean;
  reason?: string;
  payload?: Record<string, unknown>;
  online_checked?: boolean;
  is_expired?: boolean;
  /** True quand la vérification a été faite localement uniquement */
  offline_only?: boolean;
};

const API_BASE = `${API_URL.replace(/\/$/, '')}/api/v1`;

export default function AdminVerifierPage() {
  const [mode, setMode] = useState<'camera' | 'paste'>('camera');
  const [token, setToken] = useState('');
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [isOnline, setIsOnline] = useState(true);
  const [hasKeyCached, setHasKeyCached] = useState(false);

  // Détection statut réseau + pré-chargement clé publique au mount
  useEffect(() => {
    const updateOnline = () => setIsOnline(navigator.onLine);
    updateOnline();
    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);

    setHasKeyCached(hasPublicKeyCached());

    // Précharge la clé pour permettre la vérif offline sans avoir besoin
    // d'attendre une première vérification "en ligne". Si déjà cachée et
    // pas stale → no-op (lecture localStorage uniquement).
    loadPublicKey(API_BASE).then(() => setHasKeyCached(true)).catch(() => {});

    return () => {
      window.removeEventListener('online', updateOnline);
      window.removeEventListener('offline', updateOnline);
    };
  }, []);

  const verify = async (qr: string) => {
    setBusy(true);
    setError(null);
    setResult(null);
    const trimmed = qr.trim();

    // Tentative serveur si en ligne
    if (isOnline) {
      try {
        const { data } = await api.post<VerifyResult>(
          '/passes/verify/',
          { token: trimmed, online: true },
          { timeout: 8000 },
        );
        setResult({ ...data, offline_only: false, online_checked: true });
        setBusy(false);
        return;
      } catch (err: any) {
        // Si c'est un timeout / erreur réseau → fallback offline
        const isNetworkErr = err?.code === 'ECONNABORTED' || err?.message?.includes('Network') || !err?.response;
        if (!isNetworkErr) {
          // Erreur applicative claire (token invalide côté serveur, etc.)
          setError(extractApiError(err));
          setBusy(false);
          return;
        }
        toast('Serveur injoignable, vérification hors-ligne...', { icon: '📴' });
      }
    }

    // Fallback offline (signature cryptographique uniquement)
    try {
      const off = await verifyTokenOffline(trimmed, API_BASE);
      const finalRes: VerifyResult = {
        is_valid: off.is_valid,
        reason: off.reason,
        payload: off.payload,
        is_expired: off.is_expired,
        offline_only: true,
        online_checked: false,
      };
      setResult(finalRes);
    } catch (e: any) {
      setError(`Vérification hors-ligne impossible : ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  const reloadPublicKey = async () => {
    try {
      await loadPublicKey(API_BASE, true);
      toast.success('Clé publique mise à jour');
      setHasKeyCached(true);
    } catch (e: any) {
      toast.error(`Échec : ${e?.message || e}`);
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs uppercase tracking-widest text-ciOrange font-bold">
            Contrôle sanitaire
          </span>
          {/* Badge statut réseau */}
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-bold ${
              isOnline
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
            }`}
          >
            {isOnline ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
            {isOnline ? 'En ligne' : 'Hors ligne'}
          </span>
          {/* Badge clé publique */}
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-bold ${
              hasKeyCached
                ? 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300'
                : 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300'
            }`}
            title={hasKeyCached ? 'Clé publique pré-chargée — vérification offline possible' : 'Clé non chargée — connexion requise'}
          >
            <ShieldCheck className="h-3 w-3" />
            {hasKeyCached ? 'Clé OK' : 'Clé manquante'}
          </span>
          <button
            onClick={reloadPublicKey}
            className="inline-flex items-center gap-1 text-[10px] text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            title="Rafraîchir la clé publique"
          >
            <RefreshCw className="h-3 w-3" /> Rafraîchir clé
          </button>
        </div>
        <h1 className="font-display text-xl sm:text-2xl md:text-3xl font-black text-ciDark dark:text-emerald-100">
          Vérifier un Pass Sanitaire
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-3xl">
          Scannez le QR code du voyageur ou collez le token reçu. La signature est vérifiée
          cryptographiquement (Ed25519). Si le serveur est injoignable, la vérification se
          fait localement avec la clé publique pré-chargée.
        </p>
      </header>

      <div className="grid lg:grid-cols-2 gap-4 sm:gap-6">
        <div className="card p-4 sm:p-6 space-y-4">
          <div className="inline-flex rounded-xl border border-slate-300 dark:border-slate-700 p-1">
            <button
              onClick={() => setMode('camera')}
              className={`px-3 py-1.5 text-sm rounded-lg font-semibold transition ${mode === 'camera' ? 'bg-emerald-600 text-white' : 'text-slate-600 dark:text-slate-300'}`}
            >
              <Camera className="h-4 w-4 inline mr-1" /> Caméra
            </button>
            <button
              onClick={() => setMode('paste')}
              className={`px-3 py-1.5 text-sm rounded-lg font-semibold transition ${mode === 'paste' ? 'bg-emerald-600 text-white' : 'text-slate-600 dark:text-slate-300'}`}
            >
              <FileSearch className="h-4 w-4 inline mr-1" /> Coller un token
            </button>
          </div>

          {mode === 'camera' ? (
            <div className="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-800 aspect-square bg-black">
              <Scanner
                onScan={(codes) => {
                  const v = codes?.[0]?.rawValue;
                  if (v && !busy) verify(v);
                }}
                onError={(e) => setError(String(e))}
                constraints={{ facingMode: 'environment' }}
                styles={{ container: { width: '100%', height: '100%' } }}
                allowMultiple={false}
              />
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                className="textarea font-mono text-xs"
                placeholder="EPMS1.xxxx.xxxx"
                rows={5}
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
              <button
                disabled={!token.trim() || busy}
                onClick={() => verify(token.trim())}
                className="btn-primary w-full"
              >
                Vérifier la signature
              </button>
            </div>
          )}

          {error && <p className="field-error">{error}</p>}
        </div>

        <div className="space-y-4">
          {!result && !busy && (
            <div className="card p-8 text-center text-slate-500">
              Aucune vérification effectuée. Scannez ou collez un token pour commencer.
            </div>
          )}

          {busy && <div className="card p-10 animate-pulse h-40" />}

          {result && (
            <div
              className={`card p-4 sm:p-6 ${
                result.is_valid
                  ? 'border-emerald-200 dark:border-emerald-900'
                  : 'border-rose-200 dark:border-rose-900'
              }`}
            >
              <div className="flex items-center gap-3">
                {result.is_valid ? (
                  <div className="h-12 w-12 rounded-xl bg-emerald-600 text-white grid place-items-center shrink-0">
                    <ShieldCheck className="h-6 w-6" />
                  </div>
                ) : (
                  <div className="h-12 w-12 rounded-xl bg-rose-600 text-white grid place-items-center shrink-0">
                    <ShieldX className="h-6 w-6" />
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <div className="font-display text-lg sm:text-xl font-bold">
                    {result.is_valid ? 'Pass valide' : (result.is_expired ? 'Pass expiré' : 'Pass invalide')}
                  </div>
                  <div className="text-xs sm:text-sm text-slate-500 break-words">{result.reason || '—'}</div>
                </div>
              </div>

              {/* Bandeau d'avertissement si vérification offline uniquement */}
              {result.offline_only && result.is_valid && (
                <div className="mt-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200/70 dark:border-amber-900 p-3 text-xs sm:text-sm flex items-start gap-2">
                  <WifiOff className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
                  <div>
                    <strong>Vérification hors-ligne.</strong> La signature est valide mais
                    la révocation côté serveur n'a pas pu être vérifiée. Confirmer dès
                    que la connexion est rétablie.
                  </div>
                </div>
              )}

              {result.payload && (
                <div className="mt-5 space-y-2 text-sm">
                  <Row label="Identifiant voyageur" value={result.payload.tid} />
                  <Row label="Pass numéro" value={result.payload.pid} />
                  <Row label="Nom" value={result.payload.name} />
                  <Row label="Maladie" value={result.payload.dis} />
                  <Row label="Point d'entrée" value={result.payload.ep} />
                  <Row label="Émetteur" value={result.payload.iss} />
                  <Row label="Expire le" value={result.payload.exp} />
                </div>
              )}

              {result.is_valid && result.online_checked && (
                <div className="mt-5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200/70 dark:border-emerald-900 p-3 text-xs sm:text-sm flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4 text-emerald-700 shrink-0" />
                  Signature Ed25519 valide + état serveur confirmé.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: unknown }) {
  return (
    <div className="flex justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-1.5 last:border-0">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-right break-all">{value == null ? '—' : String(value)}</span>
    </div>
  );
}
