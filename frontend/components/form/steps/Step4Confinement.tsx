'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { Controller, useForm } from 'react-hook-form';
import { MapPin } from 'lucide-react';
import { confinementSchema, type ConfinementInput } from '@/lib/schema';
import { useRegistrationStore } from '@/lib/store';
import { FieldGroup, FieldRow } from '@/components/form/Field';
import { IntlPhoneInput } from '@/components/form/IntlPhoneInput';

export function Step4Confinement({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const { confinement, set, goTo } = useRegistrationStore();
  const {
    register, handleSubmit, setValue, watch, control,
    formState: { errors },
  } = useForm<ConfinementInput>({
    resolver: zodResolver(confinementSchema),
    defaultValues: confinement,
  });

  const lat = watch('latitude');
  const lng = watch('longitude');

  const fetchLocation = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setValue('latitude', pos.coords.latitude);
        setValue('longitude', pos.coords.longitude);
      },
      () => undefined,
      { enableHighAccuracy: true, timeout: 8000 },
    );
  };

  const submit = (data: ConfinementInput) => {
    set({ confinement: data });
    goTo(4);
    onNext();
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">4. Adresse de résidence en Côte d'Ivoire</h2>
        <p className="text-sm text-slate-500 mt-1">
          Précisez votre lieu de résidence durant votre séjour. Ces informations permettent à
          l'INHP de vous contacter en cas de besoin.
        </p>
      </div>

      <FieldRow>
        <FieldGroup label="Ville" required error={errors.city?.message}>
          <input className="input" placeholder="ex : Abidjan" {...register('city')} />
        </FieldGroup>
        <FieldGroup label="Commune" required error={errors.commune?.message}>
          <input className="input" placeholder="ex : Cocody" {...register('commune')} />
        </FieldGroup>
      </FieldRow>

      <FieldRow>
        <FieldGroup label="Quartier" required error={errors.neighborhood?.message}>
          <input className="input" placeholder="ex : II Plateaux" {...register('neighborhood')} />
        </FieldGroup>
        <FieldGroup label="N° de Rue / N° Lot">
          <div className="grid grid-cols-2 gap-2">
            <input className="input" placeholder="N° rue" {...register('street_number')} />
            <input className="input" placeholder="N° lot" {...register('lot')} />
          </div>
        </FieldGroup>
      </FieldRow>

      <FieldRow>
        <FieldGroup label="Hôtel / Lieu d'hébergement">
          <input className="input" placeholder="ex : Sofitel Ivoire" {...register('hotel')} />
        </FieldGroup>
        <FieldGroup label="N° de Chambre">
          <input className="input" {...register('room_number')} />
        </FieldGroup>
      </FieldRow>

      <FieldRow>
        <Controller
          name="whatsapp_phone"
          control={control}
          defaultValue=""
          render={({ field }) => (
            <FieldGroup
              label="Numéro WhatsApp"
              required
              error={errors.whatsapp_phone?.message}
              help="Canal de contact principal — sélectionnez votre pays puis saisissez votre numéro (sans le 0 initial)."
            >
              <IntlPhoneInput
                value={field.value || ''}
                onChange={field.onChange}
                invalid={Boolean(errors.whatsapp_phone)}
              />
            </FieldGroup>
          )}
        />

        <FieldGroup
          label="Téléphone d'urgence en Côte d'Ivoire (optionnel)"
          error={errors.emergency_phone_ci?.message}
          help="Si vous avez un second numéro joignable durant votre séjour."
        >
          <input className="input" placeholder="+225 ..." {...register('emergency_phone_ci')} />
        </FieldGroup>
      </FieldRow>

      <div className="rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 flex items-center justify-between gap-4">
        <div className="text-sm">
          <div className="font-semibold flex items-center gap-2">
            <MapPin className="h-4 w-4 text-emerald-600" /> Géolocalisation (optionnelle)
          </div>
          {lat && lng ? (
            <div className="text-xs text-slate-500 mt-1">Position enregistrée : {lat.toFixed(5)}, {lng.toFixed(5)}</div>
          ) : (
            <div className="text-xs text-slate-500 mt-1">Aide les agents à vous localiser en cas d'urgence.</div>
          )}
        </div>
        <button type="button" onClick={fetchLocation} className="btn-outline text-sm">
          Utiliser ma position
        </button>
      </div>

      <div className="flex justify-between pt-2">
        <button type="button" onClick={onBack} className="btn-ghost">← Précédent</button>
        <button type="submit" className="btn-primary">Suivant →</button>
      </div>
    </form>
  );
}
