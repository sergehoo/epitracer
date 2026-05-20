'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { Send, ShieldCheck } from 'lucide-react';
import { useRegistrationStore } from '@/lib/store';
import { declarationSchema } from '@/lib/schema';
import { FieldGroup, FieldRow } from '@/components/form/Field';
import { SignaturePad } from '@/components/form/SignaturePad';
import { api, extractApiError } from '@/lib/api';
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
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!declarantName && store.identite) {
      setDeclarantName(`${store.identite.last_name} ${store.identite.first_name}`.trim());
    }
  }, [declarantName, store.identite]);

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
        },
      };
      const { data } = await api.post<RegistrationResponse>('/ebola/public/register/', payload);
      toast.success('Fiche enregistrée. Pass délivré.');
      store.reset();
      router.replace(`/pass/${data.traveler.public_id}?just_issued=1`);
    } catch (err) {
      const msg = extractApiError(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
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
          {submitting ? 'Soumission…' : (<><Send className="h-4 w-4" /> Soumettre ma fiche</>)}
        </button>
      </div>
    </div>
  );
}
