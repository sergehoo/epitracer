'use client';

/**
 * Maladies — référentiel unique (apps.diseases) : surveillance active,
 * contenu public et publication sur le portail.
 *
 * - « Surveillance active » déclenche questionnaire et suivi des voyageurs.
 * - « Publiée » rend la fiche visible sur le portail public ; seule une
 *   personne habilitée (MSHPCMU / INHP / admin national) peut publier.
 */

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Eye, EyeOff, Pencil, Stethoscope, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { api, extractApiError } from '@/lib/api';
import { ALERT_LEVEL_ORDER, ALERT_LEVEL_STYLE } from '@/lib/portal';
import type { PublicAlertLevel } from '@/types/portal';

interface Disease {
  id: number; uuid: string; code: string; name: string;
  severity: string; color: string; description: string;
  surveillance_days: number; quarantine_days: number;
  is_active: boolean; requires_quarantine: boolean; requires_pass: boolean;
  slug: string; transmission_details: string; prevention: string;
  traveler_recommendations: string; public_alert_level: PublicAlertLevel;
  is_published: boolean; published_at: string | null;
}

type ContentForm = Pick<Disease,
  'slug' | 'description' | 'transmission_details' | 'prevention'
  | 'traveler_recommendations' | 'public_alert_level'>;

export default function GestionMaladiesPage() {
  const [items, setItems] = useState<Disease[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [editing, setEditing] = useState<Disease | null>(null);
  const [form, setForm] = useState<ContentForm | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    api.get('/diseases/?page_size=100')
      .then((r) => setItems(r.data.results || r.data))
      .catch((e) => setErr(extractApiError(e)));
  }, []);
  useEffect(load, [load]);

  const run = async (code: string, fn: () => Promise<unknown>, ok: string) => {
    setBusy(code);
    try {
      await fn();
      toast.success(ok);
      load();
    } catch (e) {
      toast.error(extractApiError(e));
    } finally {
      setBusy(null);
    }
  };

  const openEditor = (d: Disease) => {
    setEditing(d);
    setForm({
      slug: d.slug, description: d.description, transmission_details: d.transmission_details,
      prevention: d.prevention, traveler_recommendations: d.traveler_recommendations,
      public_alert_level: d.public_alert_level,
    });
  };

  const save = (e: FormEvent) => {
    e.preventDefault();
    if (!editing || !form) return;
    run(editing.code, () => api.patch(`/diseases/${editing.code}/`, form), 'Contenu enregistré.')
      .then(() => setEditing(null));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Maladies</h1>
        <p className="text-sm text-slate-500 mt-1">
          Référentiel unique : surveillance des voyageurs et fiches du portail public. Une fiche
          n&apos;est visible du public qu&apos;après publication par une personne habilitée.
        </p>
      </div>
      {err && <div className="card p-6 text-rose-600">{err}</div>}

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((d) => (
          <article key={d.uuid} className="card p-5 relative overflow-hidden flex flex-col">
            <div className="absolute top-0 right-0 w-24 h-24 opacity-10 rounded-full" style={{ backgroundColor: d.color, filter: 'blur(30px)' }} />
            <div className="flex items-start justify-between gap-2">
              <div className="h-10 w-10 rounded-xl grid place-items-center text-white" style={{ backgroundColor: d.color }}>
                <Stethoscope className="h-5 w-5" />
              </div>
              <div className="flex flex-wrap justify-end gap-1">
                <span className={d.is_active ? 'badge-low' : 'badge-high'}>
                  {d.is_active ? 'Surveillance active' : 'Non surveillée'}
                </span>
                <span className={d.is_published ? 'badge-low' : 'badge-moderate'}>
                  {d.is_published ? 'Publiée' : 'Brouillon'}
                </span>
              </div>
            </div>
            <div className="mt-3 font-display text-lg font-bold">{d.name}</div>
            <div className="text-xs text-slate-500">
              {d.code} · gravité {d.severity} · alerte publique {ALERT_LEVEL_STYLE[d.public_alert_level]?.label}
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div><dt className="text-slate-500">Surveillance</dt><dd className="font-semibold">{d.surveillance_days} jours</dd></div>
              <div><dt className="text-slate-500">Quarantaine</dt><dd className="font-semibold">{d.quarantine_days} jours</dd></div>
            </dl>
            <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-wrap gap-2">
              <label className="inline-flex items-center gap-1.5 text-xs font-semibold mr-auto">
                <input
                  type="checkbox"
                  checked={d.is_active}
                  disabled={busy === d.code}
                  onChange={(e) => run(
                    d.code,
                    () => api.patch(`/diseases/${d.code}/`, { is_active: e.target.checked }),
                    e.target.checked ? 'Surveillance activée.' : 'Surveillance désactivée.',
                  )}
                />
                Surveillance active
              </label>
              <button className="btn-ghost text-xs" onClick={() => openEditor(d)}>
                <Pencil className="h-3.5 w-3.5" /> Fiche
              </button>
              {d.is_published ? (
                <button
                  className="btn-outline text-xs" disabled={busy === d.code}
                  onClick={() => run(d.code, () => api.post(`/diseases/${d.code}/unpublish/`), 'Fiche retirée du portail.')}
                >
                  <EyeOff className="h-3.5 w-3.5" /> Retirer
                </button>
              ) : (
                <button
                  className="btn-primary text-xs" disabled={busy === d.code}
                  onClick={() => run(d.code, () => api.post(`/diseases/${d.code}/publish/`), 'Fiche publiée.')}
                >
                  <Eye className="h-3.5 w-3.5" /> Publier
                </button>
              )}
            </div>
          </article>
        ))}
      </div>

      {editing && form && (
        <form onSubmit={save} className="card p-5 space-y-4" aria-label={`Fiche publique ${editing.name}`}>
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-bold">Fiche publique — {editing.name}</h2>
            <button type="button" className="btn-ghost" onClick={() => setEditing(null)} aria-label="Fermer">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            <label className="text-sm">Adresse de la fiche (/maladies/…)
              <input className="input mt-1" value={form.slug} pattern="[a-z0-9-]+" onChange={(e) => setForm({ ...form, slug: e.target.value })} />
            </label>
            <label className="text-sm">Niveau d&apos;alerte public
              <select className="select mt-1" value={form.public_alert_level} onChange={(e) => setForm({ ...form, public_alert_level: e.target.value as PublicAlertLevel })}>
                {ALERT_LEVEL_ORDER.map((l) => <option key={l} value={l}>{ALERT_LEVEL_STYLE[l].label}</option>)}
              </select>
            </label>
          </div>
          <label className="text-sm block">Description
            <textarea className="textarea mt-1" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </label>
          <label className="text-sm block">Transmission
            <textarea className="textarea mt-1" value={form.transmission_details} onChange={(e) => setForm({ ...form, transmission_details: e.target.value })} />
          </label>
          <div className="grid md:grid-cols-2 gap-3">
            <label className="text-sm block">Prévention (un conseil par ligne)
              <textarea className="textarea mt-1" value={form.prevention} onChange={(e) => setForm({ ...form, prevention: e.target.value })} />
            </label>
            <label className="text-sm block">Recommandations aux voyageurs (une par ligne)
              <textarea className="textarea mt-1" value={form.traveler_recommendations} onChange={(e) => setForm({ ...form, traveler_recommendations: e.target.value })} />
            </label>
          </div>
          <p className="text-xs text-slate-500">
            Les symptômes affichés sont ceux du référentiel de la maladie (admin Django → Maladies).
            {editing.is_published && ' Cette fiche est publiée : vos modifications seront visibles immédiatement.'}
          </p>
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-ghost" onClick={() => setEditing(null)}>Annuler</button>
            <button type="submit" className="btn-primary" disabled={busy === editing.code}>Enregistrer</button>
          </div>
        </form>
      )}
    </div>
  );
}
