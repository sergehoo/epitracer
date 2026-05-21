'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { FileUp, Send, ShieldCheck, Trash2 } from 'lucide-react';
import { useRegistrationStore } from '@/lib/store';
import { declarationSchema } from '@/lib/schema';
import { FieldGroup, FieldRow } from '@/components/form/Field';
import { SignaturePad } from '@/components/form/SignaturePad';
import { api, apiPostWithRetry, extractApiError } from '@/lib/api';
import type { RegistrationResponse } from '@/types/ebola';

export function Step7Declaration({ onBack }: { onBack: () => void }) {
  const router = useRouter();
  const store = useRegistrationStore();
  const [signedPlace, setSignedPlace] = useState(store.declaration?.signed_place ?? '');
  const [declaredAt, setDeclaredAt] = useState(
    store.declaration?.declared_at?.slice(0, 10) ?? new Date().toISOString().slice(0, 10),
  );
  const [declarantName, setDeclarantName] = useState(
    store.declaration?.declarant_full_name
      ?? `${store.identite?.last_name || ''} ${store.identite?.first_name || ''}`.trim(),
  );
  const [truthful, setTruthful] = useState<boolean>(store.declaration?.truthful_declaration ?? false);
  const [signature, setSignature] = useState<string>(store.declaration?.signature_data_url ?? '');
  const [passportFile, setPassportFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!declarantName && store.identite) {
      setDeclarantName(`${store.identite.last_name} ${store.identite.first_name}`.trim());
    }
  }, [declarantName, store.identite]);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 8 * 1024 * 1024) {
      toast.error('Fichier > 8 Mo. Choisissez un fichier plus léger.');
      e.target.value = '';
      return;
    }
    const ok = ['application/pdf', 'image/jpeg', 'image/png'].includes(f.type);
    if (!ok) {
      toast.error('Format invalide. PDF, JPG ou PNG uniquement.');
      e.target.value = '';
      return;
    }
    setPassportFile(f);
  };

  const submit = async () => {
    setError(null);
    const parsed = declarationSchema.safeParse({
      signed_place: signedPlace,
      declared_at: declaredAt,
      declarant_full_name: declarantName,
      truthful_declaration: truthful,
      signature_data_url: signature,
    });
    if (!parsed.success) {
      setError(parsed.error.errors[0]?.message || 'Veuillez compléter la déclaration.');
      return;
    }

    if (!store.voyage || !store.identite || !store.confinement || !store.exposure || !store.symptoms) {
      setError('Sections précédentes incomplètes. Reprenez depuis le début.');
      return;
    }

    setSubmitting(true);
    setAttempt(0);
    try {
      const payload = {
        voyage: store.voyage,
        identite: store.identite,
        historique: store.historique || [],
        confinement: store.confinement,
        exposure: store.exposure,
        symptoms: store.symptoms,
        declaration: {
          signed_place: signedPlace,
          declared_at: new Date(declaredAt).toISOString(),
          declarant_full_name: declarantName,
          truthful_declaration: truthful,
          signature_data_url: signature,
        },
      };

      // Sauvegarde locale AVANT la requête : si le réseau coupe en cours,
      // on garde la fiche pour la resoumettre plus tard.
      if (typeof window !== 'undefined') {
        try {
          localStorage.setItem('epi_last_unsubmitted', JSON.stringify({
            payload, savedAt: new Date().toISOString(),
          }));
        } catch { /* quota plein, on ignore */ }
      }

      // POST avec retry automatique (2 retries, backoff 1s/2s/4s, timeout 90s)
      const { data } = await apiPostWithRetry<RegistrationResponse>(
        '/ebola/public/register/',
        payload,
        {
          retries: 2,
          timeoutMs: 90_000,
          onAttempt: (n) => setAttempt(n),
        },
      );

      // Succès → on nettoie la sauvegarde locale
      if (typeof window !== 'undefined') {
        try { localStorage.removeItem('epi_last_unsubmitted'); } catch { /* noop */ }
      }

      // Upload passport en best-effort (n'empêche pas la redirection si échoue)
      if (passportFile) {
        try {
          const fd = new FormData();
          fd.append('passport_document', passportFile);
          // IMPORTANT : on NE FIXE PAS Content-Type manuellement.
          // Axios + le navigateur le construisent automatiquement avec le
          // boundary multipart (ex: "multipart/form-data; boundary=----WebKit...").
          // Forcer "multipart/form-data" sans boundary produit un body
          // que le parser DRF refuse → Django retourne un 301/redirect
          // que le navigateur suit en GET, et on tombe sur le 405.
          await api.post(
            `/ebola/public/upload-passport/${data.traveler.public_id}/`,
            fd,
          );
        } catch {
          toast.error('Document de voyage non envoyé — vous pourrez le joindre depuis votre pass.');
        }
      }

      toast.success('Fiche enregistrée. Pass délivré.');
      store.reset();
      router.replace(`/pass/${data.traveler.public_id}?just_issued=1`);
    } catch (err) {
      const msg = extractApiError(err);
      // Sur erreur réseau, on garde la sauvegarde locale pour proposer un retry plus tard
      const isNetwork = /network|timeout|connect|fetch|ECONN/i.test(msg);
      setError(
        isNetwork
          ? 'Connexion interrompue après plusieurs tentatives. Vos réponses ont été sauvegardées '
            + 'localement — revenez sur cette page lorsque votre connexion est stable et cliquez à nouveau '
            + 'sur « Soumettre ma fiche ».'
          : msg,
      );
      toast.error(isNetwork ? 'Connexion réseau instable.' : msg);
    } finally {
      setSubmitting(false);
      setAttempt(0);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">7. Certification & signature</h2>
        <p className="text-sm text-slate-500 mt-1">
          « Je certifie sur l'honneur l'exactitude des renseignements portés sur cette fiche. »
        </p>
      </div>

      <FieldRow>
        <FieldGroup label="Fait à" required>
          <input className="input" value={signedPlace} onChange={(e) => setSignedPlace(e.target.value)} placeholder="ex : Abidjan" />
        </FieldGroup>
        <FieldGroup label="Date" required>
          <input type="date" className="input" value={declaredAt} onChange={(e) => setDeclaredAt(e.target.value)} />
        </FieldGroup>
      </FieldRow>

      <FieldGroup label="Nom complet du déclarant" required>
        <input className="input" value={declarantName} onChange={(e) => setDeclarantName(e.target.value)} />
      </FieldGroup>

      {/* ----- Upload du passeport / document de voyage ----- */}
      <FieldGroup
        label="Copie du passeport ou document de voyage"
        help="Format PDF, JPG ou PNG (8 Mo max). Vous pouvez aussi le joindre plus tard depuis votre pass."
      >
        {!passportFile ? (
          <label className="flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 p-6 cursor-pointer hover:border-ciOrange transition">
            <FileUp className="h-7 w-7 text-ciOrange" />
            <span className="text-sm font-semibold text-ciDark dark:text-emerald-200">
              Cliquez pour sélectionner votre passeport
            </span>
            <span className="text-xs text-slate-500">PDF · JPG · PNG — 8 Mo max</span>
            <input type="file" accept=".pdf,image/jpeg,image/png" className="hidden" onChange={handleFile} />
          </label>
        ) : (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/30 p-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <FileUp className="h-5 w-5 text-emerald-700 shrink-0" />
              <div className="min-w-0">
                <div className="font-semibold truncate">{passportFile.name}</div>
                <div className="text-xs text-slate-500">
                  {(passportFile.size / 1024).toFixed(0)} Ko · {passportFile.type}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setPassportFile(null)}
              className="btn-ghost text-rose-600 text-xs"
            >
              <Trash2 className="h-4 w-4" /> Retirer
            </button>
          </div>
        )}
      </FieldGroup>

      <label className="card p-4 flex items-start gap-3 cursor-pointer">
        <input type="checkbox" className="mt-1 h-4 w-4 accent-emerald-600" checked={truthful} onChange={(e) => setTruthful(e.target.checked)} />
        <div className="text-sm">
          <div className="font-semibold">Certification sur l'honneur</div>
          <div className="text-slate-600 dark:text-slate-300">
            Je certifie sur l'honneur l'exactitude des renseignements portés sur cette fiche, et
            j'accepte le suivi sanitaire de 21 jours conformément aux directives de l'INHP.
          </div>
        </div>
      </label>

      <FieldGroup label="Signature du passager" required>
        <SignaturePad value={signature} onChange={setSignature} />
      </FieldGroup>

      <div className="rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200/70 dark:border-emerald-900 p-4 flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-emerald-700 dark:text-emerald-300 mt-0.5" />
        <div className="text-sm">
          À la validation, un pass sanitaire QR signé cryptographiquement (Ed25519) vous sera
          délivré immédiatement. Vous pourrez le télécharger en PDF et le présenter au contrôle.
        </div>
      </div>

      {error && <p className="field-error">{error}</p>}

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-ghost" disabled={submitting}>← Précédent</button>
        <button type="button" onClick={submit} disabled={submitting} className="btn-primary">
          {submitting
            ? (attempt > 1 ? `Reprise réseau (essai ${attempt}/3)…` : 'Soumission…')
            : (<><Send className="h-4 w-4" /> Soumettre ma fiche</>)}
        </button>
      </div>
    </div>
  );
}
