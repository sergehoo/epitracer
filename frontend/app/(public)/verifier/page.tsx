'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { Camera, FileSearch, ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react';
import { Section } from '@/components/ui/Section';
import { api, extractApiError } from '@/lib/api';

const Scanner = dynamic(
  () => import('@yudiel/react-qr-scanner').then((m) => m.Scanner),
  { ssr: false },
);

interface VerifyResult {
  is_valid: boolean;
  reason?: string;
  payload?: any;
  online_checked?: boolean;
}

export default function VerifierPage() {
  const [mode, setMode] = useState<'camera' | 'paste'>('camera');
  const [token, setToken] = useState('');
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const verify = async (qr: string) => {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const { data } = await api.post<VerifyResult>('/passes/verify/', { token: qr, online: true });
      setResult(data);
    } catch (err) {
      setError(extractApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Section
      eyebrow="Contrôle sanitaire"
      title="Vérifier un Pass Sanitaire"
      description="Scannez le QR code du voyageur ou collez le token reçu. La signature est vérifiée cryptographiquement."
    >
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-6 space-y-4">
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
            <div className={`card p-6 ${result.is_valid ? 'border-emerald-200 dark:border-emerald-900' : 'border-rose-200 dark:border-rose-900'}`}>
              <div className="flex items-center gap-3">
                {result.is_valid ? (
                  <div className="h-12 w-12 rounded-xl bg-emerald-600 text-white grid place-items-center"><ShieldCheck className="h-6 w-6" /></div>
                ) : (
                  <div className="h-12 w-12 rounded-xl bg-rose-600 text-white grid place-items-center"><ShieldX className="h-6 w-6" /></div>
                )}
                <div>
                  <div className="font-display text-xl font-bold">
                    {result.is_valid ? 'Pass valide' : 'Pass invalide'}
                  </div>
                  <div className="text-sm text-slate-500">{result.reason || '—'}</div>
                </div>
              </div>

              {result.payload && (
                <div className="mt-5 space-y-2 text-sm">
                  <Row label="Identifiant voyageur" value={result.payload.tid} />
                  <Row label="Pass numéro" value={result.payload.pid} />
                  <Row label="Nom" value={result.payload.name} />
                  <Row label="Maladie" value={result.payload.dis} />
                  <Row label="Niveau de risque" value={result.payload.rsk} />
                  <Row label="Score" value={`${result.payload.scr ?? '—'} / 100`} />
                  <Row label="Émetteur" value={result.payload.iss} />
                  <Row label="Expire le" value={result.payload.exp} />
                </div>
              )}

              {result.is_valid && (
                <div className="mt-5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200/70 dark:border-emerald-900 p-3 text-sm flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4 text-emerald-700" />
                  Signature Ed25519 valide — Vérification cryptographique réussie.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </Section>
  );
}

function Row({ label, value }: { label: string; value?: any }) {
  return (
    <div className="flex justify-between gap-3 border-b border-slate-100 dark:border-slate-800 pb-1.5 last:border-0">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-right">{value ?? '—'}</span>
    </div>
  );
}
