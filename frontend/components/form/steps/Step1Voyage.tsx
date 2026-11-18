'use client';

import { useEffect, useMemo, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { api } from '@/lib/api';
import { ENTRY_POINTS } from '@/lib/datasets';
import {
  compatibleEntryPoints, keptEntryPoint, noCompatibleEntryPointMessage, type EntryPointOption,
} from '@/lib/entryPoints';
import { voyageSchema, type VoyageInput } from '@/lib/schema';
import { useRegistrationStore } from '@/lib/store';
import { FieldGroup, FieldRow } from '@/components/form/Field';

/** Points d'entrée ouverts (référentiel serveur) ; liste locale si l'API est injoignable. */
function useOpenEntryPoints(): EntryPointOption[] | null {
  const [points, setPoints] = useState<EntryPointOption[] | null>(null);
  useEffect(() => {
    let alive = true;
    api.get<EntryPointOption[]>('/ebola/public/entry-points/')
      .then(({ data }) => { if (alive) setPoints(data); })
      .catch(() => { if (alive) setPoints(ENTRY_POINTS); });
    return () => { alive = false; };
  }, []);
  return points;
}

export function Step1Voyage({ onNext }: { onNext: () => void }) {
  const { voyage, set, goTo } = useRegistrationStore();
  const { register, handleSubmit, watch, getValues, setValue, formState: { errors } } = useForm<VoyageInput>({
    resolver: zodResolver(voyageSchema),
    defaultValues: voyage,
  });
  const [arrival, departure, transport] = watch(['arrival_date', 'planned_departure_date', 'transport_mode']);
  const stayDays = arrival && departure && departure >= arrival
    ? Math.round((Date.parse(departure) - Date.parse(arrival)) / 86_400_000)
    : null;

  const points = useOpenEntryPoints();
  const entryOptions = useMemo(
    () => compatibleEntryPoints(points ?? [], transport || ''),
    [points, transport],
  );
  // Transport modifié (ou point fermé depuis le brouillon) : le point devenu
  // incompatible est vidé ; un point toujours valable est réaffiché.
  useEffect(() => {
    if (points) setValue('entry_point_code', keptEntryPoint(getValues('entry_point_code'), entryOptions));
  }, [points, entryOptions, getValues, setValue]);
  const noCompatible = Boolean(points && transport && entryOptions.length === 0);
  const entryPlaceholder = !points
    ? 'Chargement des points d\'entrée…'
    : !transport
      ? 'Choisissez d\'abord le moyen de transport'
      : noCompatible ? 'Aucun point d\'entrée compatible' : 'Sélectionner —';

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
        <FieldGroup
          label="Date de départ prévue de Côte d'Ivoire (optionnel)"
          error={errors.planned_departure_date?.message}
          help={
            stayDays !== null
              ? `Durée de séjour prévue : ${stayDays} jour${stayDays > 1 ? 's' : ''}.`
              : 'Si vous la connaissez — elle permet d\'adapter votre accompagnement.'
          }
        >
          <input
            type="date"
            className="input"
            min={arrival || undefined}
            {...register('planned_departure_date')}
          />
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
        <FieldGroup
          label="N° de Siège (optionnel)"
          error={errors.seat_number?.message}
          help="Si vous le connaissez — utile pour identifier les passagers à proximité en cas de besoin."
        >
          <input className="input" placeholder="ex : 14A" {...register('seat_number')} />
        </FieldGroup>
        <FieldGroup
          label="Point d'entrée"
          required
          error={errors.entry_point_code?.message}
          help={transport ? undefined : 'La liste dépend du moyen de transport.'}
        >
          <select
            className={`select ${entryOptions.length ? '' : 'opacity-60'}`}
            aria-describedby={noCompatible ? 'entry-point-none' : undefined}
            {...register('entry_point_code')}
          >
            <option value="">{entryPlaceholder}</option>
            {entryOptions.map((ep) => (
              <option key={ep.code} value={ep.code}>{ep.name}</option>
            ))}
          </select>
          {noCompatible && (
            <p
              id="entry-point-none"
              role="status"
              className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:ring-amber-900"
            >
              {noCompatibleEntryPointMessage(transport)}
            </p>
          )}
        </FieldGroup>
      </FieldRow>

      <div className="flex justify-end pt-2">
        <button type="submit" className="btn-primary">Suivant : Identité →</button>
      </div>
    </form>
  );
}
