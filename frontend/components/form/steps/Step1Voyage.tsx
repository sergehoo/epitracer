'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { ENTRY_POINTS } from '@/lib/datasets';
import { voyageSchema, type VoyageInput } from '@/lib/schema';
import { useRegistrationStore } from '@/lib/store';
import { FieldGroup, FieldRow } from '@/components/form/Field';

export function Step1Voyage({ onNext }: { onNext: () => void }) {
  const { voyage, set, goTo } = useRegistrationStore();
  const { register, handleSubmit, formState: { errors } } = useForm<VoyageInput>({
    resolver: zodResolver(voyageSchema),
    defaultValues: voyage,
  });

  const submit = (data: VoyageInput) => {
    set({ voyage: data });
    goTo(1);
    onNext();
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6">
      <div>
        <h2 className="font-display text-xl font-bold">1. Informations sur le voyage</h2>
        <p className="text-sm text-slate-500 mt-1">
          Indiquez les informations relatives à votre arrivée en Côte d'Ivoire.
        </p>
      </div>

      <FieldRow>
        <FieldGroup label="Date d'arrivée" required error={errors.arrival_date?.message}>
          <input type="date" className="input" {...register('arrival_date')} />
        </FieldGroup>
        <FieldGroup label="Heure d'arrivée">
          <input type="time" className="input" {...register('arrival_time')} />
        </FieldGroup>
      </FieldRow>

      <FieldRow>
        <FieldGroup label="N° de Vol / Moyen de transport" required error={errors.flight_or_voyage_number?.message}>
          <input className="input" placeholder="ex : AF572 ou KQ560" {...register('flight_or_voyage_number')} />
        </FieldGroup>
        <FieldGroup label="Moyen de transport" required error={errors.transport_mode?.message}>
          <select className="select" {...register('transport_mode')}>
            <option value="">Sélectionner —</option>
            <option value="plane">Avion</option>
            <option value="boat">Bateau</option>
            <option value="car">Voiture</option>
            <option value="bus">Bus</option>
            <option value="train">Train</option>
            <option value="foot">À pied</option>
            <option value="other">Autre</option>
          </select>
        </FieldGroup>
      </FieldRow>

      <FieldRow>
        <FieldGroup label="N° de Siège">
          <input className="input" placeholder="ex : 14A" {...register('seat_number')} />
        </FieldGroup>
        <FieldGroup label="Point d'entrée" required error={errors.entry_point_code?.message}>
          <select className="select" {...register('entry_point_code')}>
            <option value="">Sélectionner —</option>
            {ENTRY_POINTS.map((ep) => (
              <option key={ep.code} value={ep.code}>{ep.name}</option>
            ))}
          </select>
        </FieldGroup>
      </FieldRow>

      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary">Suivant : Identité →</button>
      </div>
    </form>
  );
}
