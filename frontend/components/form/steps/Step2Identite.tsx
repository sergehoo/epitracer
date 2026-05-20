'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { COUNTRIES } from '@/lib/datasets';
import { identiteSchema, type IdentiteInput } from '@/lib/schema';
import { useRegistrationStore } from '@/lib/store';
import { FieldGroup, FieldRow } from '@/components/form/Field';

export function Step2Identite({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { identite, set, goTo } = useRegistrationStore();
  const { register, handleSubmit, formState: { errors } } = useForm<IdentiteInput>({
    resolver: zodResolver(identiteSchema),
    defaultValues: identite ?? { age_unit: 'years', id_document_type: 'passport' },
  });

  const submit = (data: IdentiteInput) => {
    set({ identite: data });
    goTo(2);
    onNext();
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">2. Identité et contacts du passager</h2>
        <p className="text-sm text-slate-500 mt-1">Renseignez vos informations personnelles.</p>
      </div>

      <FieldRow>
        <FieldGroup label="Nom de famille" required error={errors.last_name?.message}>
          <input className="input" {...register('last_name')} />
        </FieldGroup>
        <FieldGroup label="Prénoms" required error={errors.first_name?.message}>
          <input className="input" {...register('first_name')} />
        </FieldGroup>
      </FieldRow>

      <FieldRow>
        <FieldGroup label="Âge" required error={errors.age?.message}>
          <div className="grid grid-cols-3 gap-2">
            <input type="number" min={0} max={130} className="input col-span-1" {...register('age')} />
            <select className="select col-span-2" {...register('age_unit')}>
              <option value="years">Ans</option>
              <option value="months">Mois</option>
            </select>
          </div>
        </FieldGroup>
        <FieldGroup label="Sexe" required error={errors.gender?.message}>
          <div className="flex gap-3 mt-1">
            <label className="inline-flex items-center gap-2 rounded-xl border border-slate-300 dark:border-slate-700 px-3 py-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900">
              <input type="radio" value="M" {...register('gender')} /> Masculin
            </label>
            <label className="inline-flex items-center gap-2 rounded-xl border border-slate-300 dark:border-slate-700 px-3 py-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900">
              <input type="radio" value="F" {...register('gender')} /> Féminin
            </label>
          </div>
        </FieldGroup>
      </FieldRow>

      <FieldRow>
        <FieldGroup label="Profession" required error={errors.profession?.message}>
          <input className="input" {...register('profession')} />
        </FieldGroup>
        <FieldGroup label="N° Passeport" required error={errors.id_document_number?.message}>
          <input className="input" {...register('id_document_number')} />
        </FieldGroup>
      </FieldRow>

      <FieldRow>
        <FieldGroup label="Nationalité">
          <select className="select" {...register('nationality_code')}>
            <option value="">Sélectionner —</option>
            {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
          </select>
        </FieldGroup>
        <FieldGroup label="Date de naissance">
          <input type="date" className="input" {...register('date_of_birth')} />
        </FieldGroup>
      </FieldRow>

      <FieldRow>
        <FieldGroup label="Téléphone Portable" required error={errors.phone_mobile?.message}>
          <input className="input" placeholder="+225 0X XX XX XX XX" {...register('phone_mobile')} />
        </FieldGroup>
        <FieldGroup label="Adresse E-mail" error={errors.email?.message}>
          <input type="email" className="input" placeholder="exemple@email.com" {...register('email')} />
        </FieldGroup>
      </FieldRow>

      <FieldGroup label="Adresse Postale">
        <textarea className="textarea" rows={2} {...register('postal_address')} />
      </FieldGroup>

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-ghost">← Précédent</button>
        <button type="submit" className="btn-primary">Suivant : Historique →</button>
      </div>
    </form>
  );
}
