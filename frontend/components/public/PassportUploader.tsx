'use client';

import { useState } from 'react';
import toast from 'react-hot-toast';
import { Check, FileUp, Loader2 } from 'lucide-react';
import { api, extractApiError } from '@/lib/api';

export function PassportUploader({
  publicId,
  hasPassport,
  onUploaded,
}: {
  publicId: string;
  hasPassport: boolean;
  onUploaded?: () => void;
}) {
  const [busy, setBusy] = useState(false);

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 8 * 1024 * 1024) {
      toast.error('Fichier > 8 Mo.');
      return;
    }
    if (!['application/pdf', 'image/jpeg', 'image/png'].includes(f.type)) {
      toast.error('PDF, JPG ou PNG uniquement.');
      return;
    }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('passport_document', f);
      // Pas de Content-Type manuel : axios/navigateur ajoutent automatiquement
      // le boundary multipart (sinon le parser DRF refuse le body).
      await api.post(`/ebola/public/upload-passport/${publicId}/`, fd);
      toast.success('Document de voyage enregistré.');
      onUploaded?.();
    } catch (err) {
      toast.error(extractApiError(err));
    } finally {
      setBusy(false);
      e.target.value = '';
    }
  };

  return (
    <article className="card p-5">
      <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold">
        Document de voyage
      </div>
      <h3 className="font-display text-base font-black mt-1">
        {hasPassport ? 'Document joint ✓' : 'Joindre une copie'}
      </h3>
      <p className="mt-2 text-xs text-slate-500 leading-5">
        {hasPassport
          ? 'Votre passeport est bien enregistré. Vous pouvez le remplacer si besoin.'
          : 'PDF, JPG ou PNG (8 Mo max). Recommandé pour faciliter les contrôles à l\'arrivée.'}
      </p>
      <label className="mt-3 inline-flex items-center gap-2 cursor-pointer rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-950 px-4 py-3 hover:border-ciOrange transition w-full justify-center">
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin text-ciOrange" />
        ) : hasPassport ? (
          <Check className="h-4 w-4 text-ciGreen" />
        ) : (
          <FileUp className="h-4 w-4 text-ciOrange" />
        )}
        <span className="text-sm font-semibold text-ciDark dark:text-emerald-200">
          {busy ? 'Envoi…' : hasPassport ? 'Remplacer le document' : 'Sélectionner un fichier'}
        </span>
        <input
          type="file"
          accept=".pdf,image/jpeg,image/png"
          className="hidden"
          onChange={upload}
          disabled={busy}
        />
      </label>
    </article>
  );
}
